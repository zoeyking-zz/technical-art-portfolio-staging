"""Run with Blender --background --factory-startup --python-exit-code 1 --python ..."""
import hashlib
import json
import os
from pathlib import Path
import struct
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import gen3d_factory as addon
from gen3d_factory.core import Policy, inspect_ply, report_document, write_report
from gen3d_factory.demo import create_demo, box_mesh, material
from gen3d_factory.mesh_checks import inspect_objects

OUT = ROOT / 'Gen3D_build'
OUT.mkdir(exist_ok=True)
checks = []


def check(condition,name):
    if not condition:
        raise AssertionError(name)
    checks.append(name)
    print('PASS:',name,flush=True)


addon.register()
original_scene = bpy.context.scene
original_objects = set(original_scene.objects)
scene,clean,bad = create_demo(bpy.context)
check(original_scene in bpy.data.scenes[:] and set(original_scene.objects)==original_objects,'Demo preserves existing scene')
initial = {o.name:[tuple(v.co) for v in o.data.vertices] for o in scene.objects if o.type=='MESH'}
results = inspect_objects(clean+bad,Policy())
by_name = {r['name']:r for r in results}
check(all(by_name[o.name]['status']=='PASS' for o in clean),'Constant PBR materials without UV pass')
for obj,rule in zip(bad,['UV_MISSING','TEXTURE_MISSING','TOPOLOGY_DEGENERATE']):
    check(rule in {i['rule'] for i in by_name[obj.name]['issues']},f'Deliberate fault detected: {rule}')
check(initial=={o.name:[tuple(v.co) for v in o.data.vertices] for o in scene.objects if o.type=='MESH'},'Scan preserves base vertices')

# A legal open plane with tiled UV is accepted by one policy and flagged by another.
mesh = bpy.data.meshes.new('OpenFixture')
mesh.from_pydata([(0,0,0),(1,0,0),(1,1,0),(0,1,0)],[],[(0,1,2,3)])
mesh.materials.append(clean[0].data.materials[0])
layer = mesh.uv_layers.new(name='UVMap')
for loop,uv in zip(layer.data,[(0,0),(2,0),(2,2),(0,2)]):
    loop.uv = uv
plane = bpy.data.objects.new('SM_OpenPlane',mesh)
scene.collection.objects.link(plane)
check(inspect_objects([plane],Policy())[0]['status']=='PASS','Allowed boundaries and tiled UV pass')
strict = inspect_objects([plane],Policy(allow_boundaries=False,allow_tiled_uv=False))[0]
check({'TOPOLOGY_BOUNDARY','UV_RANGE'} <= {i['rule'] for i in strict['issues']},'Strict policy flags boundary and UV range')
bpy.data.objects.remove(plane,do_unlink=True)

# Unsupported and malformed input paths do not masquerade as valid meshes.
truncated = OUT / 'truncated_test.ply'
truncated.write_bytes(b'ply\nformat binary_little_endian 1.0\nelement vertex 1\n')
check(inspect_ply(truncated,Policy())['status']=='ERROR','Truncated PLY rejected')
mesh_ply = OUT / 'mesh_schema_test.ply'
mesh_ply.write_bytes(b'ply\nformat ascii 1.0\nelement vertex 0\nend_header\n')
check(inspect_ply(mesh_ply,Policy())['status']=='UNSUPPORTED','Other PLY schema explicit unsupported')
check(inspect_ply(OUT/'nonexistent.ply',Policy())['status']=='ERROR','Missing PLY rejected')

def gs_fixture(filename,count,nonfinite=False,zero_rotation=False):
    names=['x','y','z','opacity']+[f'f_dc_{i}' for i in range(3)]+[f'scale_{i}' for i in range(3)]+[f'rot_{i}' for i in range(4)]
    header=('ply\nformat binary_little_endian 1.0\nelement vertex '+str(count)+'\n'
            +''.join('property float '+n+'\n' for n in names)+'end_header\n')
    row=[0.,0.,0.,-3.,0.,0.,0.,-4.,-4.,-4.,1.,0.,0.,0.]
    if nonfinite:
        row[0]=float('nan')
    if zero_rotation:
        row[10]=0.
    path=OUT/filename
    path.write_bytes(header.encode('ascii')+struct.pack('<14f',*row)*count)
    return path

valid_gs=gs_fixture('synthetic_valid_gs.ply',128)
tiny_gs=gs_fixture('synthetic_tiny_gs.ply',3)
check(inspect_ply(valid_gs,Policy())['status']=='PASS','Synthetic GS negative stored opacity/scale accepted')
check(inspect_ply(tiny_gs,Policy())['status']=='WARNING','Synthetic three-point GS review warning')
check(inspect_ply(gs_fixture('synthetic_nan_gs.ply',128,nonfinite=True),Policy())['status']=='ERROR','Non-finite GS rejected')
check(inspect_ply(gs_fixture('synthetic_zeroq_gs.ply',128,zero_rotation=True),Policy())['status']=='ERROR','Zero rotation GS rejected')
check(inspect_ply(gs_fixture('synthetic_empty_gs.ply',0),Policy())['status']=='ERROR','Empty GS rejected')

scene.gen3d.output_dir = str(OUT/'reports')
for obj in scene.objects:
    obj.select_set(obj.type=='MESH')
bpy.context.view_layer.objects.active=clean[0]
check(bpy.ops.gen3d.scan_mesh()=={'FINISHED'},'Scan operator executes')
check(len(scene.gen3d.issues)>=3,'Issues populate UI collection')
check(bpy.ops.gen3d.locate()=={'FINISHED'},'Locate operator selects problem object')
check(bpy.ops.gen3d.save_report()=={'FINISHED'},'Report operator writes HTML and JSON')
mesh_report = scene.gen3d.last_html
doc = json.loads(scene.gen3d.report_json)
check(len(doc['assets'])==len(clean+bad),'Report covers all selected meshes')
escaped = report_document([dict(name='<script>alert(1)</script>',kind='TEST',status='PASS',metrics={},issues=[],not_checked=[])],Policy(),{},'test')
_,escaped_path = write_report(escaped,OUT/'test_reports')
check('<script>' not in Path(escaped_path).read_text(encoding='utf-8'),'Report escapes untrusted asset names')

# Export clean self-authored reference mesh; round trip uses a separate scene.
for obj in scene.objects:
    obj.select_set(obj in clean)
glb = OUT/'Gen3D_Cabinet.glb'
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,use_active_scene=True)
check(glb.read_bytes()[:4]==b'glTF','Original cabinet exported to GLB')
tri_before=sum(len(o.data.loop_triangles) for o in clean)
verification=bpy.data.scenes.new('RoundTrip_Verification')
bpy.context.window.scene=verification
bpy.ops.import_scene.gltf(filepath=str(glb))
roundtrip=inspect_objects(list(verification.objects),Policy())
check(sum(r['metrics']['triangles'] for r in roundtrip)==tri_before,'Cabinet GLB round trip preserves triangle count')
check(all(r['status']!='ERROR' for r in roundtrip),'Cabinet round trip has no structural errors (name collisions may warn)')
bpy.context.window.scene=scene

ply_input = os.environ.get('GEN3D_TEST_PLY_DIR')
ply_folder = Path(ply_input) if ply_input else None
gs_report = None
real_ply_state='SKIPPED: optional external PLY directory not configured'
if ply_folder is not None:
    if not ply_folder.is_dir():
        raise AssertionError('GEN3D_TEST_PLY_DIR must point to an existing directory')
    ply_files=list(sorted(ply_folder.glob('*.ply')))
    if not ply_files:
        raise AssertionError('GEN3D_TEST_PLY_DIR contains no .ply files')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ply_files}
    scene.gen3d.ply_path=str(ply_folder)
    check(bpy.ops.gen3d.scan_ply()=={'FINISHED'},'Real PLY folder operator executes')
    gs=json.loads(scene.gen3d.report_json)
    by_ply={r['name']:r for r in gs['assets']}
    check(len(by_ply)==len(ply_files),'External PLY report covers each input file')
    check(all(not any(i['rule'].startswith('UV_') for i in a['issues']) for a in gs['assets']),'No mesh UV rules applied to Gaussian data')
    check(hashes=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ply_files},'Real PLY originals unchanged by scan')
    bpy.ops.gen3d.save_report()
    gs_report=scene.gen3d.last_html
    real_ply_state=f'TESTED: {len(ply_files)} external PLY files (report coverage and original preservation, not dataset quality)'
else:
    scene.gen3d.ply_path=str(tiny_gs)
    check(bpy.ops.gen3d.scan_ply()=={'FINISHED'},'Synthetic PLY operator executes')
    bpy.ops.gen3d.save_report()
    gs_report=scene.gen3d.last_html
    print(real_ply_state,flush=True)

# Restore the demo scan as the default visible project state.
for obj in scene.objects:
    obj.select_set(obj.type=='MESH')
bpy.context.view_layer.objects.active=clean[0]
bpy.ops.gen3d.scan_mesh()
scene.gen3d.last_html=mesh_report

# Workbench preview is a studio diagnostic, not a PBR renderer comparison.
for obj in bad:
    obj.hide_render=True
camera_data=bpy.data.cameras.new('DemoCamera')
camera=bpy.data.objects.new('DemoCamera',camera_data)
scene.collection.objects.link(camera)
camera.location=(3,-4,2.8)
camera.rotation_euler=(Vector((0,0,.83))-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.type='ORTHO'
camera_data.ortho_scale=2.8
scene.camera=camera
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO'
scene.display.shading.color_type='MATERIAL'
for mat in bpy.data.materials:
    if mat.use_nodes and mat.node_tree.nodes.get('Principled BSDF'):
        mat.diffuse_color=mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value
scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True
scene.render.resolution_x=1000
scene.render.resolution_y=1000
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.use_stamp_filename=False  # Do not embed a local project path in PNG metadata.
scene.render.filepath=str(OUT/'cabinet_preview.png')
# A render failure should not hide earlier check results; attempt after saving evidence.
summary=dict(blender=bpy.app.version_string,python=sys.version.split()[0],passed=len(checks),
             checks=checks,mesh_report=mesh_report,gs_report=gs_report,glb=str(glb),real_ply=real_ply_state)
(OUT/'test_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Gen3D_Demo.blend'))
addon.unregister()
addon.register()
check(hasattr(bpy.context.scene,'gen3d'),'Disable / enable registration cycle succeeds')
summary['passed']=len(checks)
(OUT/'test_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print('GEN3D_TESTS_COMPLETE',len(checks),flush=True)
bpy.ops.render.render(write_still=True)
