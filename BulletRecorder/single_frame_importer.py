# this code will render a single frame of your choice (this is for stillframe renders)

from bpy.types import (
    Operator,
    OperatorFileListElement,
    Panel
)
from bpy.props import (
    StringProperty,
    CollectionProperty
)
from bpy_extras.io_utils import ImportHelper
import bpy
import pickle
from os.path import splitext, join, basename
skip_frames = 1
max_frames = 200
filepath = '/Users/maxjdu/Downloads/frames.pkl'
context = bpy.context
print(f'Processing {filepath}')

SELECTED_EPISODE = 1 

new_collection = bpy.data.collections.new("BaseScene")
bpy.context.scene.collection.children.link(new_collection)

with open(filepath, 'rb') as pickle_file:
    data = pickle.load(pickle_file)
    collection_name = splitext(basename(filepath))[0]
    collection = bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(collection)
    context.view_layer.active_layer_collection = \
        context.view_layer.layer_collection.children[-1]
    for obj_key in data:
        pybullet_obj = data[obj_key]
        # Load mesh of each link
        if pybullet_obj['type'] == 'cube':
            bpy.ops.mesh.primitive_cube_add(size=1) #, location=(x, y, z))
            cube = bpy.context.active_object
            cube.scale = pybullet_obj["scale"] # Blender cube default size is 2x2x2
            # Create a new material
            mat = bpy.data.materials.new(name=f"color_{obj_key}]")
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            # Assign color to the material
            bsdf.inputs['Base Color'].default_value = pybullet_obj["color"]
            # Assign material to the cube
            cube.data.materials.append(mat)

            frame_data = pybullet_obj['frames'][SELECTED_EPISODE][0]
            pos = frame_data['position']
            orn = frame_data['orientation']
            # Apply position and rotation
            cube.location.x = pos[0]
            cube.location.y = pos[1]
            cube.location.z = pos[2]
            cube.rotation_mode = 'QUATERNION'
            cube.rotation_quaternion.x = orn[0]
            cube.rotation_quaternion.y = orn[1]
            cube.rotation_quaternion.z = orn[2]
            cube.rotation_quaternion.w = orn[3]
            new_collection.objects.link(cube)



        if pybullet_obj['type'] == 'mesh':
            extension = pybullet_obj['mesh_path'].split(
                ".")[-1].lower()
            # Handle different mesh formats
            if 'obj' in extension:
                bpy.ops.wm.obj_import(
                    filepath=pybullet_obj['mesh_path'],
                    forward_axis='Y', up_axis='Z')
            elif 'dae' in extension:
                bpy.ops.wm.collada_import(
                    filepath=pybullet_obj['mesh_path'])
            elif 'stl' in extension:
                bpy.ops.wm.stl_import(
                    filepath=pybullet_obj['mesh_path'])
            else:
                print("Unsupported File Format:{}".format(extension))
                pass
            # bpy.ops.mesh.primitive_cube_aded(location=(x, y, z), rotation = (x,y,z), scale = (x, y, z))
            # Delete lights and camera
            parts = 0
            final_objs = []
            for import_obj in context.selected_objects:
                bpy.ops.object.select_all(action='DESELECT')
                import_obj.select_set(True)
                if 'Camera' in import_obj.name \
                        or 'Light' in import_obj.name\
                        or 'Lamp' in import_obj.name:
                    bpy.ops.object.delete(use_global=True)
                else:
                    scale = pybullet_obj['mesh_scale']
                    if scale is not None:
                        import_obj.scale.x = scale[0]
                        import_obj.scale.y = scale[1]
                        import_obj.scale.z = scale[2]
                    final_objs.append(import_obj)
                    parts += 1
            bpy.ops.object.select_all(action='DESELECT')
            for obj in final_objs:
                if obj.type == 'MESH':
                    obj.select_set(True)
            if len(context.selected_objects):
                context.view_layer.objects.active =\
                    context.selected_objects[0]
                # join them
                bpy.ops.object.join()
            blender_obj = context.view_layer.objects.active
            blender_obj.name = obj_key
            print(len(pybullet_obj['frames']))
            # Keyframe motion of imported object
            # for frame_count, frame_data in enumerate(pybullet_obj['frames']):
            frame_data = pybullet_obj['frames'][SELECTED_EPISODE][0]
            pos = frame_data['position']
            orn = frame_data['orientation']
            # Apply position and rotation
            blender_obj.location.x = pos[0]
            blender_obj.location.y = pos[1]
            blender_obj.location.z = pos[2]
            blender_obj.rotation_mode = 'QUATERNION'
            blender_obj.rotation_quaternion.x = orn[0]
            blender_obj.rotation_quaternion.y = orn[1]
            blender_obj.rotation_quaternion.z = orn[2]
            blender_obj.rotation_quaternion.w = orn[3]
            new_collection.objects.link(blender_obj)
