"""Behavior tests for the copy/export/re-import transaction in Blender 5.2."""
import json
from pathlib import Path
import re
import sys
import bpy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import gen3d_factory as addon
from gen3d_factory import delivery
from gen3d_factory.core import Policy
from gen3d_factory.demo import create_demo,box_mesh,material

OUT=ROOT/'Gen3D_build'/'delivery_tests'
OUT.mkdir(parents=True,exist_ok=True)
checks=[]


def check(condition,name):
    if not condition:
        raise AssertionError(name)
    checks.append(name)
    print('PASS:',name,flush=True)


def snapshot():
    return dict(scene=bpy.context.scene.name,
                selected=sorted(o.name for o in bpy.context.selected_objects),
                active=bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
                ids={bucket:sorted(d.name for d in getattr(bpy.data,bucket)) for bucket in delivery.BUCKETS},
                meshes={o.name:[tuple(v.co) for v in o.data.vertices] for o in bpy.data.objects if o.type=='MESH'},
                matrices={o.name:[tuple(row) for row in o.matrix_world] for o in bpy.data.objects},
                custom_props={o.name:dict(o.items()) for o in bpy.data.objects})


addon.register()
scene,clean,bad=create_demo(bpy.context)
clean[0].name='side panel.001'
clean[0]['user_note']='This property must not be exported'
scene.gen3d.output_dir=str(OUT)
for obj in scene.objects:
    obj.select_set(obj in clean)
bpy.context.view_layer.objects.active=clean[0]
bpy.context.view_layer.update()

before=snapshot()
plan=delivery.naming_plan(clean)
check(plan==delivery.naming_plan(clean),'Naming plan deterministic for same Blender state')
check(len({p['export_name'] for p in plan})==len(clean),'Export names unique')
check(all(re.fullmatch('SM_[A-Za-z0-9_]+',p['export_name']) for p in plan),'Export names conform to rule')
check(bpy.ops.gen3d.preview_names()=={'FINISHED'},'Preview operator executes')
check(snapshot()==before,'Naming preview preserves original data and selection')
check(bpy.ops.gen3d.deliver()=={'FINISHED'},'Delivery operator executes')
success=json.loads(scene.gen3d.report_json)
result=success['delivery']
check(result['status']=='VERIFIED','Clean static selection verified')
check(Path(result['glb']).exists(),'Verified GLB exists')
check(all(c['passed'] for c in result['checks']),'All recorded round-trip invariants pass')
check(snapshot()==before,'Delivery preserves source data, selection, active object and ID inventory')
check(all(a['status']=='PASS' for a in result['copy_assets']),'Copied names remove naming warnings')
# Inspect actual embedded JSON, rather than trusting the report projection.
import struct
raw=Path(result['glb']).read_bytes()
length=struct.unpack_from('<I',raw,12)[0]
gltf=json.loads(raw[20:20+length])
check(all('user_note' not in n.get('extras',{}) for n in gltf['nodes']),'User custom properties are omitted from GLB nodes')

blocked=delivery.deliver(bpy.context,[bad[0]],Policy(),OUT)
check(blocked['document']['delivery']['status']=='BLOCKED','Missing UV prevents delivery')
check(not list(Path(blocked['directory']).glob('*.glb')),'Blocked run creates no GLB')
check(snapshot()==before,'Blocked run preserves scene state')

# Node-side export exception must restore state and never publish asset.glb.
original_export=delivery._export
def fail_export(path):
    raise RuntimeError('Injected export failure')
delivery._export=fail_export
failed=delivery.deliver(bpy.context,clean,Policy(),OUT)
delivery._export=original_export
check(failed['document']['delivery']['status']=='FAILED','Exporter failure recorded')
check(not (Path(failed['directory'])/'asset.glb').exists(),'Export failure does not publish verified artifact')
check(snapshot()==before,'Exporter failure rolls back temporary Blender data')

original_import=delivery._import
def changed_import(path):
    status=original_import(path)
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH':
            obj.data.vertices[0].co.x += 100
            break
    return status
delivery._import=changed_import
mismatch=delivery.deliver(bpy.context,clean,Policy(),OUT)
delivery._import=original_import
check(mismatch['document']['delivery']['status']=='FAILED','Re-import geometry mismatch fails verification')
check((Path(mismatch['directory'])/'candidate.glb').exists() and not (Path(mismatch['directory'])/'asset.glb').exists(),
      'Unverified candidate retained without delivery filename')
check(snapshot()==before,'Verification failure restores originals and active selection')

scene.unit_settings.scale_length=.01
units=delivery.deliver(bpy.context,clean,Policy(),OUT)
check(units['document']['delivery']['status']=='BLOCKED','Non-unit scene scale requires manual review')
scene.unit_settings.scale_length=1
mod=clean[0].modifiers.new('TestSubdivision','SUBSURF')
modified=delivery.deliver(bpy.context,[clean[0]],Policy(),OUT,allow_warnings=True)
check(modified['document']['delivery']['status']=='BLOCKED','Unsupported modifier blocks even when warnings allowed')
clean[0].modifiers.remove(mod)

# Explicitly exercise resource embedding and constant material non-UV exception.
mat=material('M_TextureFixture',(.5,.5,.5))
tex=mat.node_tree.nodes.new('ShaderNodeTexImage')
tex.image=bpy.data.images.new('DeliveryGeneratedImage',16,16)
tex.image.generated_color=(.1,.6,.3,1)
mat.node_tree.links.new(tex.outputs['Color'],mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
textured=box_mesh('textured panel',(2,2,.5),(1,1,1),mat,scene)
uv=textured.data.uv_layers.new(name='UVMap')
for index,loop in enumerate(uv.data):
    loop.uv=[(0,0),(1,0),(1,1),(0,1)][index%4]
bpy.context.view_layer.update()
texture_before=snapshot()
texture_result=delivery.deliver(bpy.context,[textured],Policy(),OUT)
texture_delivery=texture_result['document']['delivery']
check(texture_delivery['status']=='VERIFIED','Textured static fixture verified')
check(texture_delivery['container']['images']>=1 and texture_delivery['container']['embedded_resources_valid'],
      'Texture embedded and resource bounds checked')
check(snapshot()==texture_before,'Texture delivery cleans imported material and image IDs')

noise=mat.node_tree.nodes.new('ShaderNodeTexNoise')
mat.node_tree.links.new(noise.outputs['Color'],mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
procedural=delivery.deliver(bpy.context,[textured],Policy(),OUT,allow_warnings=True)
check(procedural['document']['delivery']['status']=='BLOCKED','Procedural shader cannot silently lose appearance on export')
mat.node_tree.nodes.remove(noise)
mat.node_tree.links.new(tex.outputs['Color'],mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])

mixed=delivery.deliver(bpy.context,[clean[0],bpy.data.objects.get('Camera')],Policy(),OUT)
check(mixed['document']['delivery']['status']=='BLOCKED','Mixed non-mesh selection is rejected explicitly')

parent=bpy.data.objects.new('StaticParent',None)
scene.collection.objects.link(parent)
parent.location=(1,2,3)
textured.parent=parent
textured.scale=(-1,2,1)
bpy.context.view_layer.update()
scaled=delivery.deliver(bpy.context,[textured],Policy(),OUT,allow_warnings=True)
check(scaled['document']['delivery']['status']=='VERIFIED_WITH_WARNINGS','Static parent and mirrored scale retain explicit review warning')
check(all(c['passed'] for c in scaled['document']['delivery']['checks']),'Flattened copy preserves source world bounds')

signature=dict(triangles=12,used_materials=1,bounds_min=[0,0,0],bounds_max=[1,1,1])
check(not all(c['passed'] for c in delivery.compare_signatures({'a':signature},{})),
      'Comparison detects missing exported object')
bad_signature=dict(signature,triangles=11)
check(not all(c['passed'] for c in delivery.compare_signatures({'a':signature},{'a':bad_signature})),
      'Comparison detects changed triangle count')

(OUT/'test_summary.json').write_text(json.dumps(dict(passed=len(checks),checks=checks,
    delivery_report=scene.gen3d.last_html,verified_glb=result['glb'],
    sample_reports=dict(blocked=blocked['html'],export_failure=failed['html'],mismatch=mismatch['html'],
                        textured=texture_result['html'],scaled=scaled['html'])),ensure_ascii=False,indent=2),encoding='utf-8')
print('GEN3D_DELIVERY_TESTS_COMPLETE',len(checks),flush=True)
