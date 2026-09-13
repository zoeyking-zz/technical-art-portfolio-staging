# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only base-mesh checks. Modifier evaluation and artistic intent are explicit limits."""
import math
from pathlib import Path
import re
import bmesh
import bpy
from .core import issue, asset_result


def upstream(start):
    nodes, seen = [], set()
    def walk(node):
        if node in seen:
            return
        seen.add(node)
        nodes.append(node)
        for socket in node.inputs:
            for link in socket.links:
                walk(link.from_node)
    walk(start)
    return nodes


def check_material(mat, obj, policy):
    issues = []
    def add(rule, severity, message, hint=''):
        issues.append(issue(rule, severity, f'{mat.name}: {message}', obj.name, hint=hint))
    if not mat.use_nodes or not mat.node_tree:
        add('MATERIAL_REVIEW', 'WARNING', 'Non-node material needs export review')
        return issues
    outputs = [n for n in mat.node_tree.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output]
    if not outputs or not outputs[0].inputs['Surface'].is_linked:
        add('MATERIAL_SURFACE', 'ERROR', 'No active connected surface output')
        return issues
    nodes = upstream(outputs[0])
    if any(n.type == 'GROUP' for n in nodes):
        add('MATERIAL_GROUP', 'WARNING', 'Node group internals not checked', 'Review group contents manually.')
    if not any(n.type == 'BSDF_PRINCIPLED' for n in nodes):
        add('MATERIAL_PBR', 'WARNING', 'No direct Principled shader found', 'Review glTF material compatibility.')
    for node in nodes:
        if node.type != 'TEX_IMAGE':
            continue
        image = node.image
        if image is None:
            add('TEXTURE_MISSING', 'ERROR', f'{node.name} has no image')
        else:
            packed = bool(image.packed_file or image.packed_files)
            if image.source == 'FILE' and not packed:
                path = bpy.path.abspath(image.filepath, library=image.library)
                if not path or not Path(path).is_file():
                    add('TEXTURE_MISSING', 'ERROR', f'Image file unavailable: {image.filepath}', 'Restore the referenced source image.')
            elif image.source not in {'FILE', 'GENERATED'}:
                add('TEXTURE_SOURCE', 'WARNING', f'{image.source} source not verified', 'UDIM, movies and sequences need explicit conversion.')
            if max(image.size, default=0) > policy.max_texture_size:
                add('TEXTURE_BUDGET', 'WARNING', f'Resolution {tuple(image.size)} exceeds {policy.max_texture_size}')
            data_use = False
            for socket in node.outputs:
                for link in socket.links:
                    if link.from_socket.name != 'Color':
                        continue
                    if link.to_node.type == 'NORMAL_MAP' or (link.to_node.type == 'BSDF_PRINCIPLED' and link.to_socket.name in {'Roughness', 'Metallic'}):
                        data_use = True
            if data_use and not image.colorspace_settings.is_data:
                add('TEXTURE_COLORSPACE', 'WARNING', 'Direct data-texture connection uses a color space', 'Review role before changing shared image color space.')
        vector = node.inputs.get('Vector')
        uv_names = []
        uses_default_uv = not vector.is_linked
        if vector.is_linked:
            for link in vector.links:
                for source in upstream(link.from_node):
                    if source.type == 'UVMAP':
                        uv_names.append(source.uv_map)
                    if source.type == 'TEX_COORD':
                        uses_default_uv |= any(l.from_socket.name == 'UV' for l in source.outputs['UV'].links)
        if uses_default_uv or '' in uv_names:
            if not obj.data.uv_layers:
                add('UV_MISSING', 'ERROR', 'Image texture requires UV coordinates but mesh has none', 'Create or restore UVs before textured export.')
        for name in set(uv_names) - {''}:
            if name not in obj.data.uv_layers:
                add('UV_MISSING', 'ERROR', f'Referenced UV layer {name} is absent')
    return issues


def inspect_mesh(obj, policy):
    mesh = obj.data
    issues = []
    metrics = dict(vertices=len(mesh.vertices), polygons=len(mesh.polygons),
                   materials=len(mesh.materials), uv_layers=len(mesh.uv_layers),
                   dimensions=[float(v) for v in obj.dimensions])
    limits = ['Base mesh only; modifier result not evaluated',
              'UV overlap, self-intersection, normal intent and render appearance: not checked',
              'Material node groups and indirect channel packing: manual review']
    def add(rule, severity, message, count=None, hint=''):
        issues.append(issue(rule, severity, message, obj.name, count, hint))
    if not re.fullmatch(r'SM_[A-Za-z0-9_]+', obj.name):
        add('NAMING', 'WARNING', 'Expected SM_ followed by ASCII letters, digits or underscores', hint='Rename according to delivery convention.')
    bad_vertices = sum(not all(math.isfinite(v) for v in vert.co) for vert in mesh.vertices)
    if bad_vertices:
        add('MESH_FINITE', 'ERROR', 'Non-finite vertex positions', bad_vertices)
    if not mesh.vertices or not mesh.polygons:
        add('MESH_EMPTY', 'ERROR', 'Mesh has no surface faces')
    if not all(math.isfinite(v) for row in obj.matrix_world for v in row):
        add('TRANSFORM_FINITE', 'ERROR', 'Non-finite world transform')
    if any(abs(v-1) > 1e-5 for v in obj.scale):
        add('TRANSFORM_SCALE', 'WARNING', 'Unapplied scale', hint='Review hierarchy and units before applying.')
    if obj.modifiers:
        add('MODIFIERS', 'WARNING', 'Modifier output not included in this scan', len(obj.modifiers))
    if not bad_vertices:
        mesh.calc_loop_triangles()
        metrics['triangles'] = len(mesh.loop_triangles)
        if len(mesh.loop_triangles) > policy.max_triangles:
            add('TRIANGLE_BUDGET', 'WARNING', f'Triangle count exceeds {policy.max_triangles}', len(mesh.loop_triangles))
        bm = bmesh.new()
        try:
            bm.from_mesh(mesh)
            counts = dict(boundary_edges=sum(e.is_boundary for e in bm.edges),
                          multi_face_edges=sum(len(e.link_faces) > 2 for e in bm.edges),
                          wire_edges=sum(e.is_wire for e in bm.edges),
                          isolated_vertices=sum(not v.link_edges for v in bm.verts),
                          degenerate_faces=sum(f.calc_area() <= 1e-12 for f in bm.faces))
            metrics.update(counts)
            for key, rule in [('multi_face_edges', 'TOPOLOGY_MULTI_FACE'), ('degenerate_faces', 'TOPOLOGY_DEGENERATE')]:
                if counts[key]:
                    add(rule, 'ERROR', key.replace('_', ' '), counts[key])
            for key in ('wire_edges', 'isolated_vertices'):
                if counts[key]:
                    add('TOPOLOGY_LOOSE', 'WARNING', key.replace('_', ' '), counts[key])
            if counts['boundary_edges'] and not policy.allow_boundaries:
                add('TOPOLOGY_BOUNDARY', 'WARNING', 'Boundary edges require review under closed-surface policy', counts['boundary_edges'])
        finally:
            bm.free()
    for layer in mesh.uv_layers:
        bad_uv = sum(not all(math.isfinite(v) for v in item.uv) for item in layer.data)
        outside = sum(any(v < -1e-5 or v > 1.00001 for v in item.uv) for item in layer.data)
        if bad_uv:
            add('UV_FINITE', 'ERROR', f'{layer.name}: non-finite UV coordinates', bad_uv)
        if outside and not policy.allow_tiled_uv:
            add('UV_RANGE', 'WARNING', f'{layer.name}: coordinates outside 0-1', outside,
                'Tiled coordinates can be intentional; check target sampler and baking policy.')
    for index in sorted({face.material_index for face in mesh.polygons}):
        mat = mesh.materials[index] if index < len(mesh.materials) else None
        if mat is None:
            add('MATERIAL_SLOT', 'WARNING', f'Faces use missing material slot {index}')
        else:
            issues.extend(check_material(mat, obj, policy))
    # Non-finite bounds cannot be encoded in standards-compliant JSON.
    metrics['dimensions'] = [v if math.isfinite(v) else None for v in metrics['dimensions']]
    return asset_result(obj.name, 'MESH', metrics, issues, limits)


def inspect_objects(objects, policy):
    results = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        try:
            results.append(inspect_mesh(obj, policy))
        except Exception as error:
            results.append(asset_result(obj.name, 'MESH', {},
                [issue('CHECK_EXCEPTION', 'ERROR', f'{type(error).__name__}: {error}', obj.name)],
                ['Scan interrupted; remaining checks not completed']))
    return results
