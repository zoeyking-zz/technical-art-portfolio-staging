# SPDX-License-Identifier: GPL-3.0-or-later
"""Gen3D Asset Factory: inspection, copy naming, and verified static GLB delivery."""
import json
from pathlib import Path
import platform
import sys
import bpy
from bpy.props import BoolProperty, CollectionProperty, IntProperty, PointerProperty, StringProperty
from .core import Policy, VERSION, RULE_HELP, asset_result, issue, inspect_ply, report_document, write_report
from .mesh_checks import inspect_objects
from .demo import create_demo
from .delivery import deliver, naming_plan

bl_info = dict(name='Gen3D Asset Factory', author='Zoey King', version=(0,2,0),
               blender=(5,2,0), location='View3D > Sidebar > Gen3D', category='Object',
               description='Inspect mesh and Gaussian assets and save quality reports')


def policy(settings):
    return Policy(settings.max_triangles,settings.max_texture_size,settings.allow_boundaries,
                  settings.allow_tiled_uv,settings.min_gaussians)


def store_results(context, assets, source):
    settings = context.scene.gen3d
    document = report_document(assets,policy(settings),
        dict(blender=bpy.app.version_string,python=sys.version.split()[0],system=platform.system()),source)
    store_document(settings,document)


def store_document(settings,document):
    settings.report_json = json.dumps(document,ensure_ascii=False,allow_nan=False)
    settings.issues.clear()
    for asset in document['assets']:
        for entry in asset['issues']:
            row = settings.issues.add()
            row.severity = entry['severity']
            row.rule = entry['rule']
            row.message = entry['message']
            row.target = entry['target']
    assets = document['assets']
    settings.summary = f"{len(assets)} assets | {sum(a['status']=='ERROR' for a in assets)} errors | {sum(a['status']=='WARNING' for a in assets)} warnings"
    settings.active_issue = 0


class GEN3D_Issue(bpy.types.PropertyGroup):
    severity: StringProperty()
    rule: StringProperty()
    message: StringProperty()
    target: StringProperty()


class GEN3D_Settings(bpy.types.PropertyGroup):
    max_triangles: IntProperty(name='Triangle budget',default=100000,min=1)
    max_texture_size: IntProperty(name='Max texture size',default=4096,min=1)
    min_gaussians: IntProperty(name='GS count review threshold',default=100,min=0)
    allow_boundaries: BoolProperty(name='Allow open boundaries',default=True)
    allow_tiled_uv: BoolProperty(name='Allow tiled UVs',default=True)
    ply_path: StringProperty(name='PLY file or folder',subtype='FILE_PATH')
    output_dir: StringProperty(name='Report folder',subtype='DIR_PATH')
    summary: StringProperty(default='No scan yet')
    report_json: StringProperty(options={'HIDDEN'})
    last_html: StringProperty(subtype='FILE_PATH')
    name_plan: StringProperty(options={'HIDDEN'})
    delivery_status: StringProperty(default='No delivery yet')
    last_glb: StringProperty(subtype='FILE_PATH')
    allow_delivery_warnings: BoolProperty(name='Allow review warnings / 允许警告交付',default=False,
        description='Errors and unsupported features still block delivery; visual review is always required')
    issues: CollectionProperty(type=GEN3D_Issue)
    active_issue: IntProperty()


class GEN3D_OT_scan_mesh(bpy.types.Operator):
    bl_idname = 'gen3d.scan_mesh'
    bl_label = 'Scan Selected Meshes'
    bl_description = 'Read-only scan of selected base meshes; modifiers are not evaluated'
    @classmethod
    def poll(cls,context):
        return context.mode == 'OBJECT' and any(o.type == 'MESH' for o in context.selected_objects)
    def execute(self,context):
        store_results(context,inspect_objects(context.selected_objects,policy(context.scene.gen3d)), 'Selected Blender objects (snapshot)')
        self.report({'INFO'},context.scene.gen3d.summary)
        return {'FINISHED'}


class GEN3D_OT_scan_ply(bpy.types.Operator):
    bl_idname = 'gen3d.scan_ply'
    bl_label = 'Inspect PLY Input'
    bl_description = 'Read GS parameters from one PLY or the immediate PLY files of a directory'
    def execute(self,context):
        settings = context.scene.gen3d
        if not settings.ply_path.strip():
            self.report({'ERROR'},'Choose a PLY file or folder')
            return {'CANCELLED'}
        path = Path(bpy.path.abspath(settings.ply_path))
        try:
            files = sorted(path.glob('*.ply')) if path.is_dir() else [path]
            if not files:
                assets = [asset_result(path.name,'INPUT',{},[issue('INPUT_EMPTY','ERROR','Folder contains no PLY files')])]
            else:
                assets = [inspect_ply(p,policy(settings)) for p in files]
            store_results(context,assets,str(path))
        except Exception as error:
            store_results(context,[asset_result(path.name,'INPUT',{},[issue('INPUT_READ','ERROR',str(error))])],str(path))
        self.report({'INFO'},settings.summary)
        return {'FINISHED'}


class GEN3D_OT_report(bpy.types.Operator):
    bl_idname = 'gen3d.save_report'
    bl_label = 'Save HTML + JSON Report'
    @classmethod
    def poll(cls,context):
        return bool(context.scene.gen3d.report_json)
    def execute(self,context):
        settings = context.scene.gen3d
        if not settings.output_dir.strip():
            self.report({'ERROR'},'Set a report folder first')
            return {'CANCELLED'}
        try:
            _,settings.last_html = write_report(json.loads(settings.report_json),bpy.path.abspath(settings.output_dir))
        except Exception as error:
            self.report({'ERROR'},str(error))
            return {'CANCELLED'}
        self.report({'INFO'},'Saved report: '+settings.last_html)
        return {'FINISHED'}


class GEN3D_OT_open_report(bpy.types.Operator):
    bl_idname = 'gen3d.open_report'
    bl_label = 'Open Last Report'
    def execute(self,context):
        path = Path(context.scene.gen3d.last_html)
        if not path.is_file():
            self.report({'ERROR'},'Save a report first')
            return {'CANCELLED'}
        bpy.ops.wm.url_open(url=path.resolve().as_uri())
        return {'FINISHED'}


class GEN3D_OT_locate(bpy.types.Operator):
    bl_idname = 'gen3d.locate'
    bl_label = 'Select Problem Object'
    bl_description = 'Select the object referenced by this snapshot; element-level highlighting is not implemented'
    def execute(self,context):
        settings = context.scene.gen3d
        if context.mode != 'OBJECT' or not 0 <= settings.active_issue < len(settings.issues):
            return {'CANCELLED'}
        obj = context.view_layer.objects.get(settings.issues[settings.active_issue].target)
        if obj is None:
            self.report({'WARNING'},'No matching object in this view layer; rescan if renamed')
            return {'CANCELLED'}
        for selected in context.selected_objects:
            selected.select_set(False)
        obj.hide_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        return {'FINISHED'}


class GEN3D_OT_demo(bpy.types.Operator):
    bl_idname = 'gen3d.create_demo'
    bl_label = 'Create Demo Scene'
    bl_description = 'Create an original cabinet and three deliberate fault fixtures in a new scene'
    def execute(self,context):
        old_output = context.scene.gen3d.output_dir
        old_ply = context.scene.gen3d.ply_path
        scene,_,_ = create_demo(context)
        scene.gen3d.output_dir = old_output
        scene.gen3d.ply_path = old_ply
        bpy.ops.gen3d.scan_mesh()
        return {'FINISHED'}


class GEN3D_OT_preview_names(bpy.types.Operator):
    bl_idname = 'gen3d.preview_names'
    bl_label = 'Preview Names / 预览副本命名'
    @classmethod
    def poll(cls,context):
        return context.mode=='OBJECT' and any(o.type=='MESH' for o in context.selected_objects)
    def execute(self,context):
        context.scene.gen3d.name_plan=json.dumps(naming_plan([o for o in context.selected_objects if o.type=='MESH']),ensure_ascii=False)
        self.report({'INFO'},'Naming preview only; source objects unchanged')
        return {'FINISHED'}


class GEN3D_OT_deliver(bpy.types.Operator):
    bl_idname = 'gen3d.deliver'
    bl_label = 'Export Verified GLB / 副本交付'
    bl_description = 'Fresh scan, name copies, export and re-import for measured validation; source objects unchanged'
    @classmethod
    def poll(cls,context):
        return context.mode=='OBJECT' and any(o.type=='MESH' for o in context.selected_objects)
    def execute(self,context):
        settings=context.scene.gen3d
        settings.last_glb=''
        settings.delivery_status='Running'
        if not settings.output_dir.strip():
            settings.delivery_status='BLOCKED: choose a report/delivery folder'
            self.report({'ERROR'},settings.delivery_status)
            return {'CANCELLED'}
        try:
            result=deliver(context,list(context.selected_objects),policy(settings),
                           bpy.path.abspath(settings.output_dir),settings.allow_delivery_warnings)
            store_document(settings,result['document'])
            outcome=result['document']['delivery']
            settings.last_html=result['html']
            settings.name_plan=json.dumps(outcome['plan'],ensure_ascii=False)
            settings.delivery_status=outcome['status']
            settings.last_glb=outcome['glb'] or ''
        except Exception as error:
            settings.delivery_status='FAILED: '+str(error)
            self.report({'ERROR'},settings.delivery_status)
            return {'CANCELLED'}
        self.report({'INFO'} if outcome['glb'] else {'WARNING'},
                    outcome['status']+' — see report for details')
        return {'FINISHED'}


class GEN3D_UL_issues(bpy.types.UIList):
    def draw_item(self,context,layout,data,item,icon,active_data,active_propname,index):
        row = layout.row()
        row.label(text=item.severity,icon='ERROR' if item.severity=='ERROR' else 'INFO')
        row.label(text=item.rule)
        row.label(text=item.target)


class GEN3D_PT_panel(bpy.types.Panel):
    bl_label = 'Gen3D Asset Factory'
    bl_idname = 'GEN3D_PT_panel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Gen3D'
    def draw(self,context):
        layout = self.layout
        settings = context.scene.gen3d
        layout.label(text='v'+VERSION+' | Inspect + Deliver')
        box = layout.box()
        box.label(text='Delivery policy')
        for name in ('max_triangles','max_texture_size','allow_boundaries','allow_tiled_uv'):
            box.prop(settings,name)
        layout.operator('gen3d.scan_mesh',icon='VIEWZOOM')
        box = layout.box()
        box.label(text='Gaussian PLY (read only)')
        box.prop(settings,'ply_path')
        box.prop(settings,'min_gaussians')
        box.operator('gen3d.scan_ply')
        layout.separator()
        layout.label(text=settings.summary)
        layout.template_list('GEN3D_UL_issues','',settings,'issues',settings,'active_issue',rows=5)
        if 0 <= settings.active_issue < len(settings.issues):
            entry = settings.issues[settings.active_issue]
            layout.label(text=entry.message[:100])
            explanation=RULE_HELP.get(entry.rule,'')
            for start in range(0,len(explanation),24):
                layout.label(text=explanation[start:start+24])
            if entry.target:
                layout.operator('gen3d.locate',icon='RESTRICT_SELECT_OFF')
        layout.label(text='Snapshot only; rescan after edits.',icon='INFO')
        layout.prop(settings,'output_dir')
        layout.operator('gen3d.save_report',icon='FILE_TICK')
        if settings.last_html:
            layout.operator('gen3d.open_report')
        box=layout.box()
        box.label(text='Static GLB / 静态网格交付')
        box.operator('gen3d.preview_names')
        if settings.name_plan:
            plan=json.loads(settings.name_plan)
            for row in plan[:4]:
                box.label(text=row['source']+' → '+row['export_name'])
            if len(plan)>4:
                box.label(text=f'{len(plan)} objects total; full mapping in report')
        box.prop(settings,'allow_delivery_warnings')
        box.operator('gen3d.deliver',icon='EXPORT')
        box.label(text=settings.delivery_status)
        box.label(text='原件保留；仅修正副本命名。')
        layout.separator()
        layout.operator('gen3d.create_demo',icon='SCENE_DATA')


CLASSES = (GEN3D_Issue,GEN3D_Settings,GEN3D_OT_scan_mesh,GEN3D_OT_scan_ply,
           GEN3D_OT_report,GEN3D_OT_open_report,GEN3D_OT_locate,GEN3D_OT_demo,
           GEN3D_OT_preview_names,GEN3D_OT_deliver,GEN3D_UL_issues,GEN3D_PT_panel)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.gen3d = PointerProperty(type=GEN3D_Settings)


def unregister():
    del bpy.types.Scene.gen3d
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
