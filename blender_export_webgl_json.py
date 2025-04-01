bl_info = {
    "name": "WebGL JSON (.json)",
    "blender": (4, 3, 2),
    "category": "Import-Export",
    "description": "Export to WebGL JSON",
}

import bpy
import os
import json

class ExportWebGLJSON(bpy.types.Operator):
    bl_idname = "export_scene.webgl_json"
    bl_label = "Export WebGL JSON"
    bl_options = {'PRESET'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH", default="export.json")
    export_normals: bpy.props.BoolProperty(name="Export Normals", default=True)
    export_all: bpy.props.BoolProperty(name="Export All Scene Objects", default=True)
    merge_objects: bpy.props.BoolProperty(name="Merge Objects", default=True)

    def execute(self, context):
        scene = context.scene

        if self.export_all:
            objects = [obj for obj in scene.objects if obj.type == 'MESH']
        else:
            objects = [obj for obj in context.selected_objects if obj.type == 'MESH']

        if len(objects) == 0:
            self.report({'ERROR'}, "Nothing to export. Please select a mesh.")
            return {'CANCELLED'}

        export_dir = os.path.dirname(self.filepath)
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        if self.merge_objects:
            bpy.ops.object.select_all(action='DESELECT')
            for obj in objects:
                obj.select_set(True)

            bpy.ops.object.duplicate()
            combined_object = context.selected_objects[-1]
            bpy.context.view_layer.objects.active = combined_object
            bpy.ops.object.join()
            combined_mesh = combined_object.data

            json_data = self.export_json(combined_object, combined_mesh)
            with open(self.filepath, 'w') as file:
                file.write(json_data)

            # Remove the temporary duplicate object after export
            bpy.data.objects.remove(combined_object, do_unlink=True)
        else:
            for obj in objects:
                mesh = obj.to_mesh(preserve_all_data_layers=True, depsgraph=context.evaluated_depsgraph_get())
                class_name = obj.name.replace(".", "")
                json_data = self.export_json(obj, mesh)
                file_path = os.path.join(export_dir, f"{class_name}.json")
                with open(file_path, 'w') as file:
                    file.write(json_data)
                bpy.data.meshes.remove(mesh, do_unlink=True)

        self.report({'INFO'}, "Export Successful")
        return {'FINISHED'}

    def export_json(self, obj, mesh):
        positions = []
        normals = []
        texture_coords = []
        indices = []

        vertex_map = {}
        vertex_list = []
        normal_list = []
        uv_list = []

        epsilon = 1e-6

        for face in mesh.polygons:
            for vertex_index in face.vertices:
                vertex = mesh.vertices[vertex_index]
                pos = tuple(0 if abs(coord) < epsilon else round(coord, 6) for coord in vertex.co)
                norm = tuple(0 if abs(coord) < epsilon else round(coord, 6) for coord in vertex.normal)
                uv = tuple(0 if abs(coord) < epsilon else round(coord, 6) for coord in mesh.uv_layers.active.data[vertex_index].uv) if mesh.uv_layers.active else None

                key = (pos, norm, uv)
                if key not in vertex_map:
                    vertex_map[key] = len(vertex_list)
                    vertex_list.append(pos)
                    normal_list.append(norm)
                    if uv:
                        uv_list.append(uv)
                indices.append(vertex_map[key])

        for vertex in vertex_list:
            positions.extend(vertex)
        for normal in normal_list:
            normals.extend(normal)
        for uv in uv_list:
            texture_coords.extend(uv)

        data = {
            "vertexPositions": positions,
            "vertexNormals": normals if self.export_normals else [],
            "vertexTextureCoords": texture_coords if mesh.uv_layers.active else [],
            "indices": indices
        }

        return json.dumps(data, separators=(',', ':'))

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}

def menu_func_export(self, context):
    self.layout.operator(ExportWebGLJSON.bl_idname, text="WebGL JSON (.json)")

def register():
    bpy.utils.register_class(ExportWebGLJSON)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(ExportWebGLJSON)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

if __name__ == "__main__":
    register()