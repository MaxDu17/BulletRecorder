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
# filepath = '/Users/maxjdu/Downloads/frames.pkl'
filepath = '/Users/maxjdu/Dropbox/My Academics/Research/classifier_guidance/blender_renders/frames_base_policy.pkl'
context = bpy.context

# Iterate through all objects in the scene
for obj in bpy.data.objects:
    # Check if the object has animation data
    if obj.animation_data:
        # Clear all keyframes by removing the action
        obj.animation_data_clear()


print(f'Processing {filepath}')
with open(filepath, 'rb') as pickle_file:
    data = pickle.load(pickle_file)
    # collection_name = splitext(basename(filepath))[0]
    # collection = bpy.data.collections.new(collection_name)
    # bpy.context.scene.collection.children.link(collection)
    # context.view_layer.active_layer_collection = \
    #     context.view_layer.layer_collection.children[-1]
    for obj_key in data:
        print(obj_key)
        obj = bpy.data.objects.get(obj_key)
        bpy.ops.object.select_all(action='DESELECT')

        # Select and activate the object
#        obj.select_set(True)
        context.view_layer.objects.active = obj
        
        print(obj, obj.name)
        if obj is None:
            print(obj)
            raise Exception("whoops")
            continue 
        pybullet_obj = data[obj_key]
        frame_count = 0 
        for episode in pybullet_obj['frames']:
            for frame_data in episode: 
                percentage_done = frame_count / len(pybullet_obj['frames'])
                # print(f'\r[{percentage_done*100:.01f}% | {obj_key}]', '#' * int(60*percentage_done), end='')
                pos = frame_data['position']
                orn = frame_data['orientation']
                context.scene.frame_set(frame_count // skip_frames)
                # Apply position and rotation
                obj.location.x = pos[0]
                obj.location.y = pos[1]
                obj.location.z = pos[2]
                obj.rotation_mode = 'QUATERNION'
                obj.rotation_quaternion.x = orn[0]
                obj.rotation_quaternion.y = orn[1]
                obj.rotation_quaternion.z = orn[2]
                obj.rotation_quaternion.w = orn[3]
#                bpy.ops.anim.keyframe_insert_menu(type='Rotation')
#                bpy.ops.anim.keyframe_insert_menu(type='Location')
                obj.keyframe_insert(data_path='location')
                obj.keyframe_insert(data_path='rotation_quaternion')
                
                frame_count += 1 