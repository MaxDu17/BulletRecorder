# this code uses the tip of the robot gripper to add a trail of spheres in the scene 
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
import numpy as np 

#EXCLUSION_LIST = [0, 1, 2, 3, 6, 8, 11, 12, 15, 19] # for ours switch
#KEEP_LIST = None 

EXCLUSION_LIST = None #[] # for door drawers 
KEEP_LIST = [1, 3, 5, 6, 8, 9, 11, 14, 16, 17, 19, 24, 27, 32, 34, 37, 38, 40, 41, 42] 

# Function to map frame count to a color from blue to yellow
def frame_to_color(frame_count, min_frame, max_frame):
    t = (frame_count - min_frame) / (max_frame - min_frame)
    # Blue to yellow interpolation (Blue: 0,0,1 -> Yellow: 1,1,0)
#    r = t
    g = t
    r = 0
    b = 1 - t
    return (r, g, b, 1)  # RGBA




skip_frames = 1
max_frames = 200
filepath = '/Users/maxjdu/Dropbox/My Academics/Research/classifier_guidance/blender_renders/frames_door_drawer.pkl'
#filepath = '/Users/maxjdu/Dropbox/My Academics/Research/classifier_guidance/blender_renders/ours_switch.pkl'

context = bpy.context
print(f'Processing {filepath}')


min_len = 20 
max_len = 100 

trajectory_collection = bpy.data.collections.new(f"Trajectories") # groups spheres into each episode for ease of control 
bpy.context.scene.collection.children.link(trajectory_collection) # links the collection to the scene (I think)


with open(filepath, 'rb') as pickle_file:
    data = pickle.load(pickle_file)
    # collection_name = splitext(basename(filepath))[0]
    # collection = bpy.data.collections.new(collection_name)
    # bpy.context.scene.collection.children.link(collection)
    # context.view_layer.active_layer_collection = \
    #     context.view_layer.layer_collection.children[-1]
    
    obj_key_1 = "panda_longer_finger_0_finger_right_tip_0"
    obj_key_2 = "panda_longer_finger_0_finger_left_tip_0"
    pybullet_obj_1 = data[obj_key_1]
    pybullet_obj_2 = data[obj_key_2] # average the position of the left and right grippper 
    
    ep_count = 0 
    for i, (episode_l, episode_r) in enumerate(zip(pybullet_obj_1['frames'], pybullet_obj_2['frames'])):
        if len(episode_l) < min_len or len(episode_l) > max_len: # reject episodes that are abnormally long or short for visualization 
            continue 
        if EXCLUSION_LIST is not None and ep_count in EXCLUSION_LIST:
            ep_count += 1 
            continue # this is for excluded trajectories for fast re-rendering 
        elif KEEP_LIST is not None and ep_count not in KEEP_LIST:
            ep_count += 1 
            continue # this is for excluded trajectories for fast re-rendering 
        
        child_collection = bpy.data.collections.new(f"Episode_{ep_count}")
        trajectory_collection.children.link(child_collection)
        last_loc = None 
        for step, (frame_data_l, frame_data_r) in enumerate(zip(episode_l, episode_r)):
            # Create UV Sphere
            current_loc_l = frame_data_l['position']
            current_loc_r = frame_data_r['position']
            current_loc = [(x + y) / 2 for x, y in zip(current_loc_l, current_loc_r)] # averaging the positions 

            # this makes sure that we don't put too many balls in close proximity 
            if last_loc is not None and np.linalg.norm(np.array(current_loc) - np.array(last_loc)) < 0.01:
                continue 

            bpy.ops.mesh.primitive_uv_sphere_add(location=current_loc)
            sphere = bpy.context.active_object
            sphere.scale = (0.005, 0.005, 0.005)
            color = frame_to_color(step, 0, len(episode_l))

            # Create colored material 
            # mat = bpy.data.materials.new(name=f"Mat_{ep_count}_{step}")
            # mat.use_nodes = True
            # bsdf = mat.node_tree.nodes.get("Principled BSDF")

            # # Get color based on frame count
            # bsdf.inputs['Base Color'].default_value = color

            # Create Glass-like Material with color tint
            mat = bpy.data.materials.new(name=f"GlassMat_{i}")
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            bsdf = nodes.get("Principled BSDF")

            if bsdf:
                # Color and glassy settings
                bsdf.inputs["Base Color"].default_value = color
                bsdf.inputs["Transmission Weight"].default_value = 0.5
                bsdf.inputs["Roughness"].default_value = 0.05
                bsdf.inputs["IOR"].default_value = 1.45
                
                bsdf.inputs["Emission Color"].default_value = color 
                bsdf.inputs["Emission Strength"].default_value = 1 
            else:
                print(f"Error: 'Principled BSDF' not found in material {mat.name}")
                
            sphere.data.materials.append(mat)

            bpy.context.view_layer.objects.active = None # important line so the color doesn't bleed 

            for col in sphere.users_collection:
                col.objects.unlink(sphere)
            child_collection.objects.link(sphere)
            last_loc = current_loc 
        ep_count += 1 