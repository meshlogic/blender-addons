#-------------------------------------------------------------------------------
#                Collada Exporter for Second Life - Blender Addon
#
# - Export static mesh objects to Collada (.dae), including images assigned to 
#   the active UV layer. Tested with Firestorm Viewer for Second Life.
#
# - Requires python collada module https://github.com/pycollada/pycollada
# - Pycollada is not part of official Blender, so must be installed into
#   Blender's folder (eg. Blender/2.78/scripts/modules)
#
# Version: 0.2
# Revised: 17.05.2017
# Author: Miki (Meshlogic)
#-------------------------------------------------------------------------------
bl_info = {
    "name": "Collada Exporter SL",
    "author": "Miki (Meshlogic)",
    "category": "Import-Export",
    "description": "Export static mesh objects to Collada (.dae), including images assigned to the active UV layer. Tested with Firestorm Viewer for Second Life.",
    "location": "File > Export",
    "version": (0, 2),
    "blender": (2, 78, 0)
}

import bpy
import bpy_extras.io_utils as io_utils
import bmesh
import os
import re
import time
import numpy as np
import xml.etree.ElementTree as ET
from bpy.props import *
from bpy.types import Menu, Operator, Panel, UIList
from collada import *


#-------------------------------------------------------------------------------
# ColladaExporter OPERATOR
#-------------------------------------------------------------------------------
class ColladaExporter_OT(Operator, io_utils.ExportHelper):
    bl_idname = "export_mesh.collada_sl"
    bl_label = "Export Collada for SL"
    bl_description = "Export selected static mesh objects to Collada"
    bl_options = {'PRESET'}

    #--- Collada file extension
    filename_ext = ".dae"

    #--- Material props
    use_mat_color = BoolProperty(
            name = "Use Material Colors",
            description = "Use material diffuse color if no UV image included",
            default = True)
            
    use_uv_image = BoolProperty(
            name = "Include UV Images",
            description = "Include images assigned to the active UV layer",
            default = True)
            
    use_relative_path = BoolProperty(
            name = "Relative Path",
            description = "Use relative or absolute path for images",
            default = True)
            
    copy_images = BoolProperty(
            name = "Copy Images",
            description = "Copy images to subdir in the export folder",
            default = False)

    #--- Mesh props
    apply_modifiers = BoolProperty(
            name = "Apply Modifiers (View)",
            description = "Apply modifiers (view mode)",
            default = True)
            
    triangulate = BoolProperty(
            name = "Triangulate",
            description = "Triangulate mesh faces for export",
            default = False)
            
    round_values = BoolProperty(
            name = "Round Values",
            description = "Round values (vertex and normal coords) to given decimal places",
            default = False)
            
    round_decimals = IntProperty(
            name = "Decimals",
            description = "Round values (vertex and normal coords) to given decimal places",
            min = 3, max = 9,
            default = 6)

    #--- Draw properties in export dialog
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        row = box.row()
        row.label("Material Image Options:", icon='TEXTURE')
        row = box.row()
        row.prop(self, "use_mat_color")
        row = box.row()
        row.prop(self, "use_uv_image")
        row = box.row()
        row.prop(self, "use_relative_path")
        row = box.row()
        row.prop(self, "copy_images")
        
        box = layout.box()
        row = box.row()
        row.label("Mesh Options:", icon='MESH_DATA')
        row = box.row()
        row.prop(self, "apply_modifiers")
        row = box.row()
        row.prop(self, "triangulate")
        row = box.row(True)
        row.prop(self, "round_values")
        row.prop(self, "round_decimals")
    
    #--- Execute file export
    def execute(self, context):
        
        # Properties as a dictionary (incl. selected filepath from file dialog)
        kwargs = self.as_keywords()
        
        # Init ColladaExporter object and execute export
        collada_ex = ColladaExporter(context, **kwargs)
        info = collada_ex.export()
        
        self.report({'INFO'}, info)
        return {'FINISHED'}


#-------------------------------------------------------------------------------
# Misc Functions
#-------------------------------------------------------------------------------
# Convert list/tuple items to string separated by sep
def list2str(items, sep):
    return sep.join(map(str, items))


#-------------------------------------------------------------------------------
# COLLADA EXPORTER CLASS
#-------------------------------------------------------------------------------
class ColladaExporter:
    
    def __init__(self, context, **kwargs):
            
        # Collada file export path
        self.export_path = kwargs["filepath"]
        self.export_dir  = os.path.dirname(self.export_path)
                
        # Directory of this blend file
        self.source_dir = os.path.dirname(bpy.data.filepath)
        
        # Export options
        self.use_mat_color     = kwargs["use_mat_color"]
        self.use_uv_image      = kwargs["use_uv_image"]
        self.use_relative_path = kwargs["use_relative_path"]
        self.copy_images       = kwargs["copy_images"]
        self.apply_modifiers   = kwargs["apply_modifiers"]
        self.triangulate       = kwargs["triangulate"]
        self.round_values      = kwargs["round_values"]
        self.round_decimals    = kwargs["round_decimals"]

        # Init Collada object for export
        self.collada = Collada(validate_output=True)
        self.scene_nodes = []
        
        # Collada Asset Info
        self.collada.assetInfo.upaxis = 'Z_UP'
        self.collada.assetInfo.unitname = "meter"
        self.collada.assetInfo.unitmeter = 1.0
        cont = asset.Contributor(
                "Blender %s" % list2str(bpy.app.version, "."),
                "Addon: %s %s" % (bl_info["name"], list2str(bl_info["version"], ".")),
                "Applly Modifiers: %s, Triangulate: %s" % (self.apply_modifiers, self.triangulate),
                )
        self.collada.assetInfo.contributors.append(cont)
        

    #---------------------------------------------------------------------------
    # EXPORT
    #---------------------------------------------------------------------------
    def export(self): 
        
        #--- Exit edit mode before exporting
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
        
        #--- Measure script execution time
        start_time = time.time()
        
        #--- Export all selected objects (sorted by name)
        obj_list = bpy.context.selected_objects
        obj_list.sort(key = lambda obj : obj.name)
        
        for obj in obj_list:
            self.export_object(obj)
            
        #--- Finish scene nodes
        c_scene = scene.Scene("Scene", self.scene_nodes)
        self.collada.scenes.append(c_scene)
        self.collada.scene = c_scene

        #--- Write Collada to file
        self.collada.write(self.export_path)
        
        #--- Sort XML to fix upload to SL
        self.sortxml()
        
        #--- Print and return info text
        info = "%d objects saved to '%s' (%.3fsec)" %\
                (len(bpy.context.selected_objects), self.export_path, time.time()-start_time)
        print(info)
        return info
 
 
    #---------------------------------------------------------------------------
    # IDNAME - Format name strings for Collada ids
    #---------------------------------------------------------------------------        
    def idname(self, str):
        return re.sub("\.", "_", str) # Replace any dot in the string
 
 
    #---------------------------------------------------------------------------
    # ADD COLLADA IMAGE
    # - Add image to collada.images and return the CImage object
    # - Copy image to a subdir in the export dir if desired
    #---------------------------------------------------------------------------
    def add_collada_image(self, img):
        
        #--- Add image to collada.images
        if img.name not in self.collada.images:
            
            #--- Copy image to a subdir in the export dir
            if self.copy_images:
                
                # Image source path and basename
                img_sourcepath = bpy.path.abspath(img.filepath)
                img_basename = bpy.path.basename(img_sourcepath)
                
                # Copy image to subdir in export dir
                export_filename = bpy.path.display_name_from_filepath(self.export_path)
                subdir = export_filename + "_textures"
                
                img_destpath = os.path.join(self.export_dir, subdir, img_basename)
                copy_set = {(img_sourcepath, img_destpath)}
                io_utils.path_reference_copy(copy_set)
                
                # Relative path to the copied image
                path = io_utils.path_reference(img_destpath, self.source_dir, self.export_dir, 'RELATIVE')
                
            #--- Reference image where it is
            else:
                if self.use_relative_path:
                    path_mode = 'RELATIVE'
                else:   
                    path_mode = 'ABSOLUTE'
                path = io_utils.path_reference(img.filepath, self.source_dir, self.export_dir, path_mode)
            
            #--- Create and add CImage object
            c_img = material.CImage(img.name, path)
            self.collada.images.append(c_img)
            
        #--- Image already added to collada.images
        else:
            c_img = self.collada.images[img.name]
        
        return c_img


    #---------------------------------------------------------------------------
    # ADD COLLADA VOIDMAT
    # - Add this material in case of empty or no material slot
    #---------------------------------------------------------------------------
    def add_collada_voidmat(self, name):
        
        # Collada material effect
        c_effect = material.Effect(name +"-effect", [], 'phong',
                diffuse = (0.5,0.5,0.5,1.0),
                ambient = (0.25,0.25,0.25,1.0),
                specular = (1.0,1.0,1.0,1.0),
                shininess = 50.0)
        self.collada.effects.append(c_effect)
        
        # Collada material
        c_mat = material.Material(name +"-material", name, c_effect)
        self.collada.materials.append(c_mat)
        return scene.MaterialNode(name +"-material", c_mat, inputs=[])
        
        
    #---------------------------------------------------------------------------
    # ADD COLLADA MATERIALS
    # - Add object materials to collada.materials and collada.effects 
    #---------------------------------------------------------------------------
    def add_collada_materials(self, obj, me):
        material_nodes = []
        
        #--- Get active uv map layer and texture
        uvlayer = me.uv_layers.active
        if uvlayer:
            uvtex = me.uv_textures[uvlayer.name]
        
        # [1] No material slot - Add void material
        if len(me.materials) == 0:
            c_matnode = self.add_collada_voidmat(self.idname(obj.name) +"_voidmat_0")
            material_nodes.append(c_matnode)
            return material_nodes

        # [2] Go trough all slots in object materials
        for i, mat in enumerate(me.materials):
            
            #--- Empty material slot - Add void material
            if mat == None:
                c_matnode = self.add_collada_voidmat(self.idname(obj.name) +"_voidmat_"+ str(i))
                material_nodes.append(c_matnode)
                continue
            
            #--- Look for uv image assigned to the given material and uv face
            img = None
            if self.use_uv_image and uvlayer:
                for f in me.polygons:
                    if f.material_index == i:
                        img = uvtex.data[f.index].image     # Get image assigned to the uv face
                        c_img = self.add_collada_image(img) # Add image to collada images
                        break
            
            #--- Include image map in the material effect
            if img:
                c_surface = material.Surface(img.name +"-surface", c_img, format=None)
                c_sampler = material.Sampler2D(img.name +"-sampler", c_surface)
                params_list = [c_sampler, c_surface]
                inputs_list = [(uvlayer.name, 'TEXCOORD', '0')]
                diffuse_map = material.Map(c_sampler, uvlayer.name)
                
            #--- No image map for the material effect
            else:
                params_list = []
                inputs_list = []
                diffuse_color = list(mat.diffuse_color) + [1.0]
                diffuse_map = np.around(diffuse_color,6) if self.use_mat_color else (1.0,1.0,1.0,1.0)
                
            #--- Add material effect to collada.effects
            c_name = self.idname(obj.name) +"_"+ self.idname(mat.name)
            c_effect = material.Effect(c_name +"-effect", params_list, 'phong',
                    diffuse = diffuse_map,
                    ambient = (.25,.25,.25,1.0),
                    specular = (1.0,1.0,1.0,1.0),
                    shininess = 50.0)
            self.collada.effects.append(c_effect)
            
            #--- Add material to collada.materials
            c_mat = material.Material(c_name +"-material", c_name, c_effect)
            c_matnode = scene.MaterialNode(c_name +"-material", c_mat, inputs=inputs_list)
            self.collada.materials.append(c_mat)
            material_nodes.append(c_matnode)
        
        #--- Return scene.MaterialNode for each material
        return material_nodes
        
        
    #---------------------------------------------------------------------------
    # EXPORT OBJECT
    #---------------------------------------------------------------------------
    def export_object(self, obj):
        cs = bpy.context.scene
        
        #-----------------------------------------------------------------------
        # Prepare object's mesh data (me)
        #-----------------------------------------------------------------------
        # Create mesh for export & apply modifiers if desired
        me = obj.to_mesh(cs, self.apply_modifiers, 'PREVIEW')
        
        # Triangulate mesh if desired
        if self.triangulate:
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.triangulate(bm, faces=bm.faces)
            bm.to_mesh(me)
            bm.free()
        
        #-----------------------------------------------------------------------
        # Material & effect nodes for each object's material
        #-----------------------------------------------------------------------
        material_nodes = self.add_collada_materials(obj, me)
            
        #-----------------------------------------------------------------------
        # Source list for vertex coords
        #-----------------------------------------------------------------------
        verts_srcid = self.idname(obj.name) + "-verts"
        verts_co = np.array([co for v in me.vertices for co in v.co])
        if self.round_values:
            verts_co = np.round(verts_co, self.round_decimals)
        verts_src = source.FloatSource(verts_srcid, verts_co, ('X', 'Y', 'Z'))
        
        #-----------------------------------------------------------------------
        # Source list for normals
        #-----------------------------------------------------------------------
        normals_srcid = self.idname(obj.name) + "-normals"
        normals = []
        
        for f in me.polygons:
            # Smooth shaded face - use vertex normals
            if f.use_smooth:
                for v_id in f.vertices:
                    v = me.vertices[v_id]
                    normals.extend(v.normal)
            # Flat shaded face - use face normal for each polygon vert
            else:
                for v_id in f.vertices:
                    normals.extend(f.normal)
        
        normals = np.array(normals)
        if self.round_values:
            normals = np.round(normals, self.round_decimals)
        
        normals_src = source.FloatSource(normals_srcid, normals, ('X', 'Y', 'Z'))
        sources = [verts_src, normals_src]

        #-----------------------------------------------------------------------
        # Source list for the active UV map texture coords
        #-----------------------------------------------------------------------
        uvlayer = me.uv_layers.active
        if uvlayer:
            tex_srcid = self.idname(obj.name) + "-tex-" + uvlayer.name
            tex_uv = []
            
            for f in me.polygons:
                for loop_id in range(f.loop_start, f.loop_start + f.loop_total):
                    tex_uv.extend([x for x in uvlayer.data[loop_id].uv])
            
            tex_uv = np.array(tex_uv)
            if self.round_values:
                tex_uv = np.round(tex_uv, self.round_decimals)
            
            tex_src = source.FloatSource(tex_srcid, tex_uv, ('S', 'T'))
            sources.append(tex_src)

        #-----------------------------------------------------------------------
        # Geometry node for this object incl. source lists
        #-----------------------------------------------------------------------
        c_geom = geometry.Geometry(self.collada, self.idname(obj.name)+"-geom", self.idname(obj.name), sources)
                
        #-----------------------------------------------------------------------
        # Create Polylist for each material
        #-----------------------------------------------------------------------
        for i, matnode in enumerate(material_nodes):
            
            #--- Input list to define data binding to the source lists
            inlist = source.InputList()
            inlist.addInput(0, 'VERTEX', '#'+verts_srcid)
            inlist.addInput(1, 'NORMAL', '#'+normals_srcid)
            if uvlayer:
                inlist.addInput(1, 'TEXCOORD', '#'+tex_srcid, set=0)
            
            #--- List of indicies to the source lists for each face f, for each vert v
            indices = []
            vcounts = []
            n_id = 0
            for f in me.polygons:
                if f.material_index == i:
                    vcounts.extend([len(f.vertices)])
                    for v_id in f.vertices:
                        indices.extend([v_id, n_id])
                        n_id += 1
                else:
                    for v_id in f.vertices:
                        n_id += 1
            
            #--- Bind polylist with existing material node
            material_id = matnode.symbol
            
            #--- Append polylist to geometry
            c_poly = c_geom.createPolylist(np.array(indices), np.array(vcounts), inlist, material_id)
            c_geom.primitives.append(c_poly)

        #-----------------------------------------------------------------------
        # Create scene node for this object
        #-----------------------------------------------------------------------
        self.collada.geometries.append(c_geom)
        c_geom_node = scene.GeometryNode(c_geom, material_nodes)
        
        #--- Object transformation matrix
        matrix = np.array(obj.matrix_world).flatten()
        if self.round_values:
            matrix = np.round(matrix, self.round_decimals)
        c_matrix = scene.MatrixTransform(matrix)
        
        #--- Scene node
        c_node = scene.Node(self.idname(obj.name), children=[c_matrix, c_geom_node])
        self.scene_nodes.append(c_node)
        
        #--- Clean up mesh used for export
        bpy.data.meshes.remove(me)
        

    #---------------------------------------------------------------------------
    # Sort XML nodes to fix Second Life upload
    # - With the default sorting, SL fails to upload textures
    # - newparam/surface node must be before newparam/sampler2D for each effect
    #---------------------------------------------------------------------------
    def sortxml(self):
        
        #--- Load Collada XML file
        tree = ET.parse(self.export_path)
        root = tree.getroot()
        
        # Collada namespace
        ns = {'ns':'http://www.collada.org/2005/11/COLLADASchema'}
        
        # Get node tag without namespace
        gettag = lambda node : re.sub("{.*}", "", node.tag)

        #-----------------------------------------------------------------------
        # Re-order root nodes
        #-----------------------------------------------------------------------
        root_order = [
            'asset',
            'library_images',
            'library_effects',
            'library_materials',
            'library_geometries',
            'library_visual_scenes',
            'scene']
        
        root[:] = sorted(root, key = lambda root : root_order.index(gettag(root)))
        
        #-----------------------------------------------------------------------
        # Reverse sort of effect nodes newparam/surface and newparam/sampler2D
        #-----------------------------------------------------------------------
        for effect in root.findall('.//ns:effect/ns:profile_COMMON', ns):
            
            # Find and remove newparam nodes from the tree
            newparam = effect.findall("ns:newparam", ns)
            for item in newparam:
                effect.remove(item)
         
            # Insert sorted newparam nodes
            # <surface> node must be before <sampler2D>, thus reverse order
            newparam = sorted(newparam, key = lambda newparam : newparam.get('sid'), reverse=True)

            for i, item in enumerate(newparam):
                effect.insert(i, newparam[i])
        
        #--- Write XML to file
        spath = os.path.splitext(self.export_path)
        #tree.write(spath[0] +"_sortxml"+ spath[1])
        tree.write(self.export_path)


#-------------------------------------------------------------------------------
# MENU
#-------------------------------------------------------------------------------
def menu_export(self, context):
    self.layout.operator(ColladaExporter_OT.bl_idname, text="Collada for SL (.dae)")


#-------------------------------------------------------------------------------
# REGISTER/UNREGISTER ADDON CLASSES
#-------------------------------------------------------------------------------
def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_export.prepend(menu_export)
     
def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_export.remove(menu_export)
        
if __name__ == "__main__":
    register()
    
    
    