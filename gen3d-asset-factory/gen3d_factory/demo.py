# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate original, deterministic mesh fixtures in a separate scene."""
import bpy


def box_mesh(name, location, dimensions, material, scene):
    x, y, z = (v/2 for v in dimensions)
    verts = [(-x,-y,-z), (x,-y,-z), (x,y,-z), (-x,y,-z),
             (-x,-y,z), (x,-y,z), (x,y,z), (-x,y,z)]
    faces = [(0,3,2,1), (4,5,6,7), (0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    scene.collection.objects.link(obj)
    return obj


def material(name, color, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = .36
    return mat


def create_demo(context):
    scene = bpy.data.scenes.new('Gen3D_Demo')
    context.window.scene = scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    teal = material('M_Gen3D_Teal', (.04,.24,.28), .3)
    dark = material('M_Gen3D_Charcoal', (.025,.035,.045), .15)
    brass = material('M_Gen3D_Brass', (.65,.36,.08), .7)
    clean = []
    for side, xpos in [('Left',-.58), ('Right',.58)]:
        clean.append(box_mesh('SM_Cabinet_'+side, (xpos,0,.85), (.08,.65,1.5),teal,scene))
    for name, zpos in [('Base',.14), ('Top',1.58), ('Shelf',.8)]:
        clean.append(box_mesh('SM_Cabinet_'+name,(0,0,zpos),(1.24,.65,.08),teal,scene))
    clean.append(box_mesh('SM_Cabinet_Back',(0,.285,.85),(1.1,.08,1.38),dark,scene))
    for number, zpos in enumerate((.49,1.18),1):
        clean.append(box_mesh(f'SM_Drawer_{number}',(0,-.33,zpos),(1.06,.08,.58),teal,scene))
        clean.append(box_mesh(f'SM_Handle_{number}',(0,-.41,zpos),(.36,.06,.045),brass,scene))
    for x in (-.47,.47):
        for y in (-.21,.21):
            clean.append(box_mesh(f'SM_Foot_{len(clean)}',(x,y,.055),(.09,.09,.11),dark,scene))
    # Constant materials without UVs are valid clean examples.
    uv_mat = material('M_MissingUV',(.4,.4,.4))
    tex = uv_mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.new('Gen3D_GeneratedTexture',64,64)
    uv_mat.node_tree.links.new(tex.outputs['Color'],uv_mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    missing_uv = box_mesh('SM_Bad_MissingUV',(2,0,.5),(.7,.7,1),uv_mat,scene)
    missing_mat = material('M_MissingImage',(.4,.4,.4))
    tex = missing_mat.node_tree.nodes.new('ShaderNodeTexImage')
    missing_mat.node_tree.links.new(tex.outputs['Color'],missing_mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    missing_image = box_mesh('SM_Bad_MissingImage',(3.1,0,.5),(.7,.7,1),missing_mat,scene)
    missing_image.data.uv_layers.new(name='UVMap')
    degenerate = box_mesh('SM_Bad_Degenerate',(4.2,0,.5),(.7,.7,1),dark,scene)
    verts = [tuple(v.co) for v in degenerate.data.vertices] + [(0,0,0),(.1,0,0),(.2,0,0)]
    faces = [tuple(p.vertices) for p in degenerate.data.polygons] + [(8,9,10)]
    degenerate.data.clear_geometry()
    degenerate.data.from_pydata(verts,[],faces)
    degenerate.data.update()
    for obj in scene.objects:
        obj.select_set(True)
    context.view_layer.objects.active = clean[0]
    return scene, clean, [missing_uv,missing_image,degenerate]
