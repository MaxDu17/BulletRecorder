# this code uses the tip of the robot gripper to add a trail of spheres in the scene 
DRY_RUN = False

if not DRY_RUN:
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
import json 

#EXCLUSION_LIST = [0, 1, 2, 3, 6, 8, 11, 12, 15, 19] # for ours switch
#KEEP_LIST = None 

# EXCLUSION_LIST = None # for base policy
# KEEP_LIST = [1, 2, 13, 20, 25, 26] 

EXCLUSION_LIST = None 
KEEP_LIST = None 

#EXCLUSION_LIST = None # for door drawers 
#KEEP_LIST = [1, 3, 5, 6, 8, 9, 11, 14, 16, 17, 19, 24, 27, 32, 34, 37, 38, 40, 41, 42] 


#EXCLUSION_LIST = [5, 12] # for door drawers 
#KEEP_LIST = None

import matplotlib.cm as cm
import matplotlib.colors as mcolors

# Function to map frame count to a plasma color
def frame_to_color(frame_count, min_frame, max_frame):
    norm = mcolors.Normalize(vmin=min_frame, vmax=max_frame)
    plasma = cm.get_cmap('plasma')
    rgba = plasma(norm(frame_count))
    return rgba  # Already returns (r, g, b, a)

## Function to map frame count to a color from blue to yellow
#def frame_to_color(frame_count, min_frame, max_frame):
#    t = (frame_count - min_frame) / (max_frame - min_frame)
#    # Blue to yellow interpolation (Blue: 0,0,1 -> Yellow: 1,1,0)
##    r = t
#    g = t
#    r = 0
#    b = 1 - t
#    return (r, g, b, 1)  # RGBA


def interpolate_points_3d(points, max_distance):
    """
    Given a list of 3D points, return a new list with interpolated points
    such that the distance between any two consecutive points is <= max_distance.

    :param points: List of points [(x1, y1, z1), (x2, y2, z2), ...]
    :param max_distance: Maximum allowed distance between consecutive points
    :return: List of points with interpolated segments
    """
    result = []

    for i in range(len(points) - 1):
        start = np.array(points[i])
        end = np.array(points[i + 1])
        result.append(tuple(start))  # Always include the start point

        segment = end - start
        length = np.linalg.norm(segment)

        if length > max_distance:
            num_segments = int(np.ceil(length / max_distance))
            for j in range(1, num_segments):
                interpolated = start + (segment * j / num_segments)
                result.append(tuple(interpolated))

    result.append(tuple(points[-1]))  # Always include the last point
    return result



skip_frames = 1
max_frames = 200
# filepath = '/store/real/maxjdu/repos/robotrainer/frames_base_policy_100.pkl'
filepath = '/Users/maxjdu/Dropbox/My Academics/Research/classifier_guidance/blender_renders/frames_base_policy_100.pkl'
# labelpath = "/Users/maxjdu/Dropbox/My Academics/Research/classifier_guidance/blender_renders/base_policy.json"
labelpath = "/Users/maxjdu/Dropbox/My Academics/Research/classifier_guidance/blender_renders/traj_labels_base_policy.json"


print(f'Processing {filepath}')


min_len = 20 
max_len = 110

context = bpy.context
trajectory_collection = bpy.data.collections.new(f"Trajectories") # groups spheres into each episode for ease of control 
bpy.context.scene.collection.children.link(trajectory_collection) # links the collection to the scene (I think)

label_list = json.load(open(labelpath, "r"))

behavior_color_dict = {"door_left" : (1, 1, 0, 1), "switch_on" : (1, 0, 0, 1), "button_on" : (0, 0, 1, 1), "drawer_open": (1, 0, 1, 1)}
behavior_material_dict = {} 

for behavior, color in behavior_color_dict.items():
    mat = bpy.data.materials.new(name=f"{behavior}")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Transmission Weight"].default_value = 0 #0.5
    bsdf.inputs["Roughness"].default_value = 0.05
    bsdf.inputs["IOR"].default_value = 1.45
    
    bsdf.inputs["Emission Color"].default_value = color 
    bsdf.inputs["Emission Strength"].default_value = 0.5 
    behavior_material_dict[behavior] = mat 


with open(filepath, 'rb') as pickle_file:
    data = pickle.load(pickle_file)
    collection_name = splitext(basename(filepath))[0]
    collection = bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(collection)
    context.view_layer.active_layer_collection = context.view_layer.layer_collection.children[-1]
    
    obj_key_1 = "panda_longer_finger_0_finger_right_tip_0"
    obj_key_2 = "panda_longer_finger_0_finger_left_tip_0"
    pybullet_obj_1 = data[obj_key_1]
    pybullet_obj_2 = data[obj_key_2] # average the position of the left and right grippper 
    ep_count = 0 
    for i, (episode_l, episode_r) in enumerate(zip(pybullet_obj_1['frames'], pybullet_obj_2['frames'])):
#        if i > 10:
#            break 
        if len(episode_l) < min_len or len(episode_l) > max_len: # reject episodes that are abnormally long or short for visualization 
            continue 
        if EXCLUSION_LIST is not None and ep_count in EXCLUSION_LIST:
            ep_count += 1 
            continue # this is for excluded trajectories for fast re-rendering 
        elif KEEP_LIST is not None and ep_count not in KEEP_LIST:
            ep_count += 1 
            continue # this is for excluded trajectories for fast re-rendering 

        # TODO: reinable 
        child_collection = bpy.data.collections.new(f"Episode_{ep_count}")
        trajectory_collection.children.link(child_collection)

        if label_list[i] not in behavior_color_dict: # we are excluding episodes that don't satisfy our requirements 
            ep_count += 1     
            continue 
        center_points = [(np.array(x["position"]) + np.array(y["position"])) / 2 for x, y in zip(episode_l, episode_r)]
        interpolated_center_points = interpolate_points_3d(center_points, max_distance = 0.003)
        for step, coord in enumerate(interpolated_center_points):
            bpy.ops.mesh.primitive_uv_sphere_add(location=coord)
            sphere = bpy.context.active_object
            sphere.scale = (0.001, 0.001, 0.001)
                
            sphere.data.materials.append(behavior_material_dict[label_list[i]])

            bpy.context.view_layer.objects.active = None # important line so the color doesn't bleed 

            for col in sphere.users_collection:
                col.objects.unlink(sphere)
            child_collection.objects.link(sphere)
        ep_count += 1 