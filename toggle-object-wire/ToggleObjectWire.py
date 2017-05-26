#-------------------------------------------------------------------------------
#                      Toggle Object Wire - Addon for Blender
# Version: 0.1
# Revised: 29.03.2017
# Author: Miki (Meshlogic)
#-------------------------------------------------------------------------------
bl_info = {
    "name": "Toggle Object Wire",
    "author": "Meshlogic",
    "category": "3D View",
    "description": "Toggle object's wire display or subsurf modifiers for all objects or for the selection only. Shortcuts: wire (\), subsurf (shift+\).",
    "location": "3D View > Info Panel > Shading",
    "version": (0, 1),
    "blender": (2, 78, 0)
}

import bpy
from bpy.props import *
from bpy.types import Menu, Operator, Panel, UIList


#-------------------------------------------------------------------------------
# ToggleObjectWire_OT
#------------------------------------------------------------------------------- 
class ToggleObjectWire_OT(Operator):
    bl_idname = "object.toggle_wire"
    bl_label = "Toggle Object Wire"
    bl_description = "Toggle object(s) wire display"
    
    def execute(self, context):
        cs = context.scene
        cs_props = cs.toggle_object_wire

        #--- Toggle all objects or the selected objects only
        if cs_props.all_objects:
            obj_list = bpy.data.objects
        else:
            obj_list = context.selected_objects

        #--- Only one object selected - toggle according the object's state
        if len(obj_list) == 1:
            obj = obj_list[0]
            if obj and obj.type in {'MESH', 'CURVE', 'FONT', 'META', 'SURFACE'}:
                cs_props.toggle_wire = not obj.show_wire
            
        #--- Multiple objects selected - toggle according the previous operator state
        elif len(obj_list) > 1:
            cs_props.toggle_wire = not cs_props.toggle_wire
            
        #--- Execute toggling!
        for obj in obj_list:
            if obj and obj.type in {'MESH', 'CURVE', 'FONT', 'META', 'SURFACE'}:
                obj.show_all_edges = True
                obj.show_wire = cs_props.toggle_wire
                
                # Optimal display for subsurf mod
                for mod in obj.modifiers:
                    if mod and mod.type == 'SUBSURF':
                        mod.show_only_control_edges = cs_props.optimal_display
 
        return{'FINISHED'}    


#-------------------------------------------------------------------------------
# ToggleSubsurf_OT
#------------------------------------------------------------------------------- 
class ToggleSubsurf_OT(Operator):
    bl_idname = "object.toggle_subsurf"
    bl_label = "Toggle Object Subsurf"
    bl_description = "Toggle object(s) subsurf modifiers"

    def execute(self, context):
        cs = context.scene
        cs_props = cs.toggle_object_wire
 
        #--- Toggle all objects or the selected objects only
        if cs_props.all_objects:
            obj_list = bpy.data.objects
        else:
            obj_list = context.selected_objects

        #--- Only one object selected - toggle according the object's modifier state
        if len(obj_list) == 1:
            obj = obj_list[0]
            
            # Find state of an existing subsurf mod
            if obj and obj.type in {'MESH', 'CURVE', 'FONT', 'META', 'SURFACE'}:
                for mod in obj.modifiers:
                    if mod and mod.type == 'SUBSURF':
                        cs_props.toggle_subsurf = not mod.show_viewport
                        break
                    
        #--- Multiple objects selected - toggle according the previous operator state
        elif len(obj_list) > 1:
            cs_props.toggle_subsurf = not cs_props.toggle_subsurf
    
        #--- Execute toggling!
        for obj in obj_list:
            if obj and obj.type in {'MESH', 'CURVE', 'FONT', 'META', 'SURFACE'}:
                
                for mod in obj.modifiers:
                    if mod and mod.type == 'SUBSURF':
                        mod.show_only_control_edges = cs_props.optimal_display
                        mod.show_viewport = cs_props.toggle_subsurf
    
        return{'FINISHED'}
    
    
#-------------------------------------------------------------------------------
# update_optimal_display
# - Optimal Display on/off for all subsurf modifiers
#-------------------------------------------------------------------------------   
def update_optimal_display(self, context):
    
    cs = context.scene
    cs_props = cs.toggle_object_wire
    obj_list = bpy.data.objects
    
    for obj in obj_list:
        if obj and obj.type in {'MESH', 'CURVE', 'FONT', 'META', 'SURFACE'}:
            for mod in obj.modifiers:
                if mod and mod.type == 'SUBSURF':
                    mod.show_only_control_edges = cs_props.optimal_display
    
    
#-------------------------------------------------------------------------------
# ADD THIS TO THE INFO PANEL (VIEW3D_PT_view3d_shading)
#-------------------------------------------------------------------------------   
def toggle_object_wire_panel(self, context):
    cs = context.scene
    cs_props = cs.toggle_object_wire
    layout = self.layout

    #layout.separator()
    col = layout.column(True)
    col.operator("object.toggle_wire", icon='WIRE')
    col.operator("object.toggle_subsurf", icon='MOD_SUBSURF')
    
    row =  layout.row(True)
    row.prop(cs_props, "all_objects")
    row.prop(cs_props, "optimal_display")
   
    
#-------------------------------------------------------------------------------
# CUSTOM SCENE PROPS
#-------------------------------------------------------------------------------        
class ToggleObjectWire_Props(bpy.types.PropertyGroup):
    
    all_objects = BoolProperty(
        name = "All Objects",
        description = "Toggle wire and subsurf modifiers for all objects",
        default = True)
        
    optimal_display = BoolProperty(
        name = "Optimal Display",
        description = "Optimal display for subsurf modifiers",
        default = True,
        update = update_optimal_display)

    # Keep operator's toggle state
    toggle_wire = BoolProperty(default=False)
    toggle_subsurf = BoolProperty(default=True)
    

#-------------------------------------------------------------------------------
# REGISTER/UNREGISTER ADDON CLASSES
#-------------------------------------------------------------------------------
addon_keymaps = []

def register():
    bpy.utils.register_module(__name__)
    bpy.types.Scene.toggle_object_wire = PointerProperty(type=ToggleObjectWire_Props)
    bpy.types.VIEW3D_PT_view3d_shading.append(toggle_object_wire_panel)

    # Add custom shortcuts ('GRLESS' = backslash '\')
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Object Mode', space_type='EMPTY')
    kmi = km.keymap_items.new("object.toggle_wire", type='GRLESS', value='PRESS', ctrl=False, shift=False)
    kmi = km.keymap_items.new("object.toggle_subsurf", type='GRLESS', value='PRESS', ctrl=False, shift=True)
    addon_keymaps.append((km, kmi))
     
def unregister():
    # Remove custom shortcuts
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    bpy.utils.unregister_module(__name__)
    del bpy.types.Scene.toggle_object_wire
    bpy.types.VIEW3D_PT_view3d_shading.remove(toggle_object_wire_panel)
        
if __name__ == "__main__":
    register()
    
    
    