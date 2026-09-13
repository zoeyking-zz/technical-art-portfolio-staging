# SPDX-License-Identifier: GPL-3.0-or-later
"""Static-mesh copy/name/export/re-import transaction. Originals are not renamed.

The verified result covers explicitly measured invariants, not visual acceptance.
Every attempt gets its own folder; unverified candidates are never named asset.glb.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import struct
import sys
import uuid

import bpy
from .core import issue, asset_result, report_document, write_report
from .mesh_checks import inspect_objects, upstream

ID_KEY = 'gen3d_validation_id'
BLOCKED_RULES = {'MATERIAL_GROUP', 'MATERIAL_REVIEW', 'MATERIAL_PBR', 'TEXTURE_SOURCE',
                 'MATERIAL_SLOT', 'CHECK_EXCEPTION'}
BUCKETS = ('objects', 'scenes', 'meshes', 'materials', 'images', 'collections',
           'actions', 'cameras', 'lights', 'textures')


def naming_plan(objects):
    """Reserve Blender-global names so copies never rename an existing ID."""
    reserved = set(bpy.data.objects.keys())
    plan = []
    for index, obj in enumerate(sorted(objects, key=lambda o: o.name)):
        base = re.sub(r'[^A-Za-z0-9_]+', '_', obj.name).strip('_')
        if not base:
            base = 'Asset_' + hashlib.sha256(obj.name.encode()).hexdigest()[:8]
        if not base.startswith('SM_'):
            base = 'SM_' + base
        base = base[:45]
        name = base
        if name in reserved:
            name = base + '_Export'
        suffix = 2
        while name in reserved:
            name = base + f'_Export_{suffix:03d}'
            suffix += 1
        reserved.add(name)
        plan.append(dict(source=obj.name, export_name=name, validation_id=f'asset_{index:04d}'))
    return plan


def signature(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    positions = [obj.matrix_world @ v.co for v in mesh.vertices]
    return dict(triangles=len(mesh.loop_triangles),
                bounds_min=[min(p[a] for p in positions) for a in range(3)],
                bounds_max=[max(p[a] for p in positions) for a in range(3)],
                used_materials=len({p.material_index for p in mesh.polygons}))


def compare_signatures(expected, actual):
    """Per-object world-space comparison; vertex counts may change at seams."""
    checks = []
    checks.append(dict(check='object_ids', passed=set(expected) == set(actual),
                       expected=sorted(expected), actual=sorted(actual)))
    for key in sorted(expected.keys() & actual.keys()):
        before, after = expected[key], actual[key]
        for field in ('triangles', 'used_materials'):
            checks.append(dict(check=field, asset=key, passed=before[field] == after[field],
                               expected=before[field], actual=after[field]))
        extent = max(b-a for a,b in zip(before['bounds_min'],before['bounds_max']))
        tolerance = max(1e-5,extent*1e-5)
        for field in ('bounds_min','bounds_max'):
            good = all(math.isfinite(b) and abs(a-b) <= tolerance for a,b in zip(before[field],after[field]))
            checks.append(dict(check=field,asset=key,passed=good,expected=before[field],
                               actual=after[field],tolerance=tolerance))
    return checks


def inspect_glb_container(path):
    """Check embedded-resource bounds, not the complete glTF specification."""
    raw = Path(path).read_bytes()
    if len(raw) < 20:
        raise ValueError('GLB shorter than header')
    magic, version, length = struct.unpack_from('<4sII',raw)
    if magic != b'glTF' or version != 2 or length != len(raw):
        raise ValueError('Invalid GLB header or length')
    offset = 12
    chunks = []
    while offset < length:
        size, kind = struct.unpack_from('<II',raw,offset)
        if size % 4 or offset+8+size > length:
            raise ValueError('Invalid GLB chunk size')
        chunks.append((kind,raw[offset+8:offset+8+size]))
        offset += 8+size
    if offset != length or chunks[0][0] != 0x4E4F534A:
        raise ValueError('Missing JSON chunk')
    doc = json.loads(chunks[0][1])
    bins = [block for kind,block in chunks if kind == 0x004E4942]
    buffers = doc.get('buffers',[])
    if len(buffers) != 1 or len(bins) != 1 or buffers[0].get('uri'):
        raise ValueError('Delivery must use one embedded buffer')
    byte_count = buffers[0]['byteLength']
    if byte_count > len(bins[0]) or byte_count < 0:
        raise ValueError('Embedded buffer too short')
    views = doc.get('bufferViews',[])
    for view in views:
        start, count = view.get('byteOffset',0), view['byteLength']
        if view.get('buffer',0) != 0 or start < 0 or count < 0 or start+count > byte_count:
            raise ValueError('Buffer view exceeds embedded buffer')
    for img in doc.get('images',[]):
        idx = img.get('bufferView',-1)
        if 'uri' in img or not 0 <= idx < len(views):
            raise ValueError('Image is not embedded in GLB')
    nodes = [n for n in doc.get('nodes',[]) if 'mesh' in n]
    ids = [n.get('extras',{}).get(ID_KEY) for n in nodes]
    if not nodes or None in ids or len(set(ids)) != len(ids):
        raise ValueError('Missing or duplicate validation IDs')
    return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
                mesh_nodes=len(nodes),node_names=[n.get('name','') for n in nodes],
                validation_ids=ids,images=len(doc.get('images',[])),
                materials=len(doc.get('materials',[])),embedded_resources_valid=True)


def preflight(objects, scene):
    problems = []
    if not objects:
        return ['Select at least one mesh']
    if scene.unit_settings.scale_length != 1:
        problems.append('Only scene unit scale 1 is supported; confirm units before delivery')
    for obj in objects:
        if obj.type != 'MESH':
            problems.append(f'{obj.name}: non-mesh selection is not supported')
            continue
        if obj.modifiers or obj.data.shape_keys or obj.data.animation_data or obj.rigid_body or obj.instance_type != 'NONE':
            problems.append(f'{obj.name}: modifiers, shape keys, mesh animation, rigid bodies or instancing require another export path')
        if any(slot.link == 'OBJECT' for slot in obj.material_slots):
            problems.append(f'{obj.name}: object-level material overrides need a separate material validation path')
        for mat in (m for m in obj.data.materials if m):
            if mat.animation_data or (mat.node_tree and mat.node_tree.animation_data):
                problems.append(f'{obj.name}: animated materials are unsupported')
            if not mat.node_tree:
                continue
            output=next((n for n in mat.node_tree.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output),None)
            if output is None:
                continue
            allowed={'OUTPUT_MATERIAL','BSDF_PRINCIPLED','TEX_IMAGE','NORMAL_MAP','UVMAP','TEX_COORD'}
            for node in upstream(output):
                if node.type not in allowed:
                    problems.append(f'{obj.name}: {node.type} shader node needs a separate material validation path')
                if node.type=='NORMAL_MAP' and node.space!='TANGENT':
                    problems.append(f'{obj.name}: non-tangent normal maps are unsupported')
                if node.type=='TEX_COORD' and any(socket.is_linked for socket in node.outputs if socket.name!='UV'):
                    problems.append(f'{obj.name}: non-UV texture coordinates are unsupported')
        current = obj
        while current:
            if current.constraints or current.animation_data:
                problems.append(f'{obj.name}: animated/constrained hierarchy is not supported')
                break
            current = current.parent
        # A parent can induce shear which cannot be represented by Blender TRS copying.
        from mathutils import Matrix
        loc, rot, scale = obj.matrix_world.decompose()
        reconstructed = Matrix.LocRotScale(loc,rot,scale)
        if any(abs(a-b) > 1e-5 for ra,rb in zip(obj.matrix_world,reconstructed) for a,b in zip(ra,rb)):
            problems.append(f'{obj.name}: sheared world transform requires manual handling')
    return problems


def _export(path):
    return bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',
        use_selection=True,use_active_scene=True,export_extras=True,
        export_animations=False,export_apply=False)


def _import(path):
    return bpy.ops.import_scene.gltf(filepath=str(path))


def deliver(context, objects, policy, directory, allow_warnings=False):
    """Run synchronously with a fresh scan; preserve source scene and selection.

    BLOCKED: unsuitable input; FAILED: export/verification error; VERIFIED:
    measured invariants passed. Unexpected failure also retains its own report.
    """
    if context.mode != 'OBJECT' or context.window is None:
        raise ValueError('Use Object Mode in a Blender window context')
    if not str(directory).strip():
        raise ValueError('Choose a delivery directory')
    folder = Path(directory)
    folder.mkdir(parents=True,exist_ok=True)
    run = folder / ('delivery_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:8])
    run.mkdir()
    objects = sorted(objects,key=lambda o:o.name)
    original_scene = context.window.scene
    original_layer = context.view_layer
    original_active = original_layer.objects.active
    original_selection = list(context.selected_objects)
    context.view_layer.update()
    source_results = inspect_objects(objects,policy)
    document = report_document(source_results,policy,
        dict(blender=bpy.app.version_string,python=sys.version.split()[0],system=platform.system()),
        'Selected source objects (unchanged); copy/export evidence appears separately')
    delivery = dict(status='BLOCKED',plan=naming_plan([o for o in objects if o.type=='MESH']),
        problems=[],allow_warnings=allow_warnings,copy_assets=[],checks=[],glb=None,
        limits=['No PBR render comparison, material-value/texture-pixel equivalence, or complete glTF validation',
                'Static meshes only; only object/data names are repaired; hierarchy flattened in copies',
                'Object/mesh custom properties omitted except validation IDs; material/image metadata not audited'])
    document['delivery'] = delivery
    problems = preflight(objects,original_scene)
    for asset in source_results:
        for finding in asset['issues']:
            if finding['severity'] == 'ERROR' or finding['rule'] in BLOCKED_RULES:
                problems.append(f"{asset['name']}: {finding['rule']} — {finding['message']}")
            elif finding['severity'] == 'WARNING' and finding['rule'] != 'NAMING' and not allow_warnings:
                problems.append(f"{asset['name']}: review warning {finding['rule']} before export")
    delivery['problems'] = problems
    if not problems:
        before = {bucket:set(getattr(bpy.data,bucket)) for bucket in BUCKETS}
        try:
            staging = bpy.data.scenes.new('Gen3D_Delivery_Temporary')
            staging.unit_settings.system = 'METRIC'
            staging.unit_settings.scale_length = 1
            context.window.scene = staging
            copies = []
            expected = {}
            for obj, row in zip(objects,delivery['plan']):
                copy = obj.copy()
                copy.data = obj.data.copy()
                world = obj.matrix_world.copy()
                copy.parent = None
                copy.matrix_world = world
                for key in list(copy.keys()):
                    del copy[key]
                for key in list(copy.data.keys()):
                    del copy.data[key]
                copy[ID_KEY] = row['validation_id']
                copy.name = row['export_name']
                copy.data.name = row['export_name']+'_Mesh'
                copy.hide_viewport = copy.hide_render = False
                copy.hide_select = False
                staging.collection.objects.link(copy)
                copy.select_set(True)
                copies.append(copy)
                expected[row['validation_id']] = signature(obj)
            context.view_layer.objects.active = copies[0]
            context.view_layer.update()
            delivery['copy_assets'] = inspect_objects(copies,policy)
            if any(a['status']=='ERROR' for a in delivery['copy_assets']):
                raise ValueError('Copy scan failed')
            candidate = run/'candidate.glb'
            if _export(candidate) != {'FINISHED'}:
                raise RuntimeError('glTF export did not finish')
            container = inspect_glb_container(candidate)
            if set(container['node_names']) != {p['export_name'] for p in delivery['plan']}:
                raise ValueError('Exported names differ from naming plan')
            # Release copies before import so canonical names cannot collide with them.
            for copy in copies:
                mesh = copy.data
                bpy.data.objects.remove(copy,do_unlink=True)
                bpy.data.meshes.remove(mesh)
            if _import(candidate) != {'FINISHED'}:
                raise RuntimeError('glTF re-import did not finish')
            imported = [o for o in staging.objects if o.type=='MESH']
            actual = {}
            for obj in imported:
                key = obj.get(ID_KEY)
                if not key or key in actual:
                    raise ValueError('Re-import lost or duplicated asset IDs')
                actual[key] = signature(obj)
            delivery['checks'] = compare_signatures(expected,actual)
            delivery['roundtrip_assets'] = inspect_objects(imported,policy)
            delivery['container'] = container
            if not all(c['passed'] for c in delivery['checks']):
                raise ValueError('Round-trip geometry/material-count validation failed')
            if any(a['status']=='ERROR' for a in delivery['roundtrip_assets']):
                raise ValueError('Re-imported asset fails implemented checks')
            destination = run/'asset.glb'
            candidate.rename(destination)
            delivery['glb'] = str(destination)
            warnings = any(a['status']=='WARNING' for a in delivery['copy_assets']+delivery['roundtrip_assets'])
            delivery['status'] = 'VERIFIED_WITH_WARNINGS' if warnings else 'VERIFIED'
        except Exception as error:
            delivery['status'] = 'FAILED'
            delivery['problems'].append(f'{type(error).__name__}: {error}')
        finally:
            context.window.scene = original_scene
            context.window.view_layer = original_layer
            # Only IDs created during this synchronous transaction are eligible.
            for bucket in BUCKETS:
                collection = getattr(bpy.data,bucket)
                for item in list(collection):
                    if item not in before[bucket]:
                        collection.remove(item,do_unlink=True)
            for obj in original_layer.objects:
                obj.select_set(obj in original_selection)
            original_layer.objects.active = original_active
    json_path,html_path = write_report(document,run)
    return dict(document=document,json=json_path,html=html_path,directory=str(run))
