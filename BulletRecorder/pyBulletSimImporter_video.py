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


########### FOR THE ROBOT  
powder_coated_metal_texture = bpy.data.materials.new(name="PowderCoatedMetal")
powder_coated_metal_texture.use_nodes = True
nodes = powder_coated_metal_texture.node_tree.nodes
links = powder_coated_metal_texture.node_tree.links
# Clear default nodes
nodes.clear()
# Create necessary nodes
output_node = nodes.new(type='ShaderNodeOutputMaterial')
output_node.location = (400, 0)
principled_node = nodes.new(type='ShaderNodeBsdfPrincipled')
principled_node.location = (0, 0)
principled_node.inputs["Metallic"].default_value = 0.5 #1.0
principled_node.inputs["Roughness"].default_value = 0.55
principled_node.inputs["Coat Weight"].default_value = 0.2
principled_node.inputs["Coat Roughness"].default_value = 0.1
# Add noise texture for subtle surface texture
noise_node = nodes.new(type='ShaderNodeTexNoise')
noise_node.location = (-600, -100)
noise_node.inputs["Scale"].default_value = 150.0
noise_node.inputs["Detail"].default_value = 2.0
noise_node.inputs["Roughness"].default_value = 0.5

# Add bump node
bump_node = nodes.new(type='ShaderNodeBump')
bump_node.location = (-200, -100)
bump_node.inputs["Strength"].default_value = 0.02 #0.1
bump_node.inputs["Distance"].default_value = 0.05

# Link nodes
links.new(principled_node.outputs["BSDF"], output_node.inputs["Surface"])
links.new(noise_node.outputs["Fac"], bump_node.inputs["Height"])
links.new(bump_node.outputs["Normal"], principled_node.inputs["Normal"])


########### FOR METAL 
# Create a new material
metal_texture = bpy.data.materials.new(name="RealisticMetal")
metal_texture.use_nodes = True
nodes = metal_texture.node_tree.nodes
links = metal_texture.node_tree.links
nodes.clear()

# Create shader nodes
output_node = nodes.new(type='ShaderNodeOutputMaterial')
output_node.location = (400, 0)

principled_node = nodes.new(type='ShaderNodeBsdfPrincipled')
principled_node.location = (0, 0)
principled_node.inputs['Metallic'].default_value = 1.0
principled_node.inputs['Roughness'].default_value = 0.3
principled_node.inputs['Anisotropic'].default_value = 0.9
principled_node.inputs['Anisotropic Rotation'].default_value = 0.0
links.new(principled_node.outputs["BSDF"], output_node.inputs["Surface"])


###### FOR GLASS
glass_texture = bpy.data.materials.new(name="Glass")
glass_texture.use_nodes = True
nodes = glass_texture.node_tree.nodes
bsdf = nodes.get("Principled BSDF")

#bsdf.inputs["Base Color"].default_value = color
bsdf.inputs["Transmission Weight"].default_value = 0.75
bsdf.inputs["Roughness"].default_value = 0.05
bsdf.inputs["IOR"].default_value = 1.5

new_collection = bpy.data.collections.new("BaseScene")
bpy.context.scene.collection.children.link(new_collection)



print(f'Processing {filepath}')
with open(filepath, 'rb') as pickle_file:
    data = pickle.load(pickle_file)
    # collection_name = splitext(basename(filepath))[0]
    # collection = bpy.data.collections.new(collection_name)
    # bpy.context.scene.collection.children.link(collection)
    # context.view_layer.active_layer_collection = \
    #     context.view_layer.layer_collection.children[-1]
    for obj_key in data:
        pybullet_obj = data[obj_key]
        # Load mesh of each link
        if pybullet_obj['type'] == 'cube':
            bpy.ops.mesh.primitive_cube_add(size=1) #, location=(x, y, z))
            cube = bpy.context.active_object
            cube.scale = pybullet_obj["scale"] # Blender cube default size is 2x2x2
            # Create a new material
            for col in cube.users_collection:
                col.objects.unlink(cube)
            new_collection.objects.link(cube)

            mat = bpy.data.materials.new(name=f"color_{obj_key}]")
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get("Principled BSDF")

            bsdf.inputs['Base Color'].default_value = pybullet_obj["color"]
            bsdf.inputs['Coat Weight'].default_value = 0.6
            bsdf.inputs['Coat Roughness'].default_value = 0.1
            # Assign material to the cube
            cube.data.materials.append(mat)
            bpy.context.view_layer.objects.active = None # important line so the color doesn't bleed 

            # cube = bpy.context.active_object
            frame_count = 0 
            for episode in pybullet_obj['frames']:
                for frame_data in episode: 
                    percentage_done = frame_count / len(pybullet_obj['frames'])
                    print(f'\r[{percentage_done*100:.01f}% | {obj_key}]', '#' * int(60*percentage_done), end='')
                    pos = frame_data['position']
                    orn = frame_data['orientation']
                    context.scene.frame_set(frame_count // skip_frames)
                    # Apply position and rotation
                    cube.location.x = pos[0]
                    cube.location.y = pos[1]
                    cube.location.z = pos[2]
                    cube.rotation_mode = 'QUATERNION'
                    cube.rotation_quaternion.x = orn[0]
                    cube.rotation_quaternion.y = orn[1]
                    cube.rotation_quaternion.z = orn[2]
                    cube.rotation_quaternion.w = orn[3]
                    bpy.ops.anim.keyframe_insert_menu(type='Rotation')
                    bpy.ops.anim.keyframe_insert_menu(type='Location')
                    frame_count += 1 


        if pybullet_obj['type'] == 'mesh':
            extension = pybullet_obj['mesh_path'].split(
                ".")[-1].lower()
            # Handle different mesh formats
            if 'obj' in extension:
                bpy.ops.wm.obj_import(filepath=pybullet_obj['mesh_path'],forward_axis='Y', up_axis='Z')
            elif 'dae' in extension:
                bpy.ops.wm.collada_import(filepath=pybullet_obj['mesh_path'])
            elif 'stl' in extension:
                bpy.ops.wm.stl_import(filepath=pybullet_obj['mesh_path'])
            else:
                print("Unsupported File Format:{}".format(extension))
                continue 
    
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
            mesh_obj = context.view_layer.objects.active
            mesh_obj.name = obj_key
            for col in mesh_obj.users_collection:
                col.objects.unlink(mesh_obj)
            new_collection.objects.link(mesh_obj)

            print(len(pybullet_obj['frames']))
            # Keyframe motion of imported object
            # for frame_count, frame_data in enumerate(pybullet_obj['frames']):
            frame_count = 0 
            for episode in pybullet_obj['frames']:
                for frame_data in episode:
                    percentage_done = frame_count / len(pybullet_obj['frames'])
                    print(f'\r[{percentage_done*100:.01f}% | {obj_key}]', '#' * int(60*percentage_done), end='')
                    pos = frame_data['position']
                    orn = frame_data['orientation']
                    context.scene.frame_set(frame_count // skip_frames)
                    # Apply position and rotation
                    mesh_obj.location.x = pos[0]
                    mesh_obj.location.y = pos[1]
                    mesh_obj.location.z = pos[2]
                    mesh_obj.rotation_mode = 'QUATERNION'
                    mesh_obj.rotation_quaternion.x = orn[0]
                    mesh_obj.rotation_quaternion.y = orn[1]
                    mesh_obj.rotation_quaternion.z = orn[2]
                    mesh_obj.rotation_quaternion.w = orn[3]
                    bpy.ops.anim.keyframe_insert_menu(type='Rotation')
                    bpy.ops.anim.keyframe_insert_menu(type='Location')
                    frame_count += 1 

            # RENDERING PARAMETERS
            if "left" in obj_key or "right" in obj_key:
                if len(mesh_obj.data.materials) > 0:
                    mesh_obj.data.materials[0] = metal_texture
                else:
                    mesh_obj.data.materials.append(metal_texture)
            elif "panda" in obj_key:
                if len(mesh_obj.data.materials) > 0:
                    mesh_obj.data.materials[0] = powder_coated_metal_texture
                else:
                    mesh_obj.data.materials.append(powder_coated_metal_texture)
            elif "calvin" in obj_key and "switch" not in obj_key and "led" not in obj_key and "light" not in obj_key and "button" not in obj_key:
                mat = mesh_obj.data.materials[0]
                mat.use_nodes = True
                nodes = mat.node_tree.nodes
                links = mat.node_tree.links
                # Find the Principled BSDF node
                principled = None
                for node in nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        principled = node
                        break
                # Add clearcoat properties
                principled.inputs['Coat Weight'].default_value = 0.4
                principled.inputs['Coat Roughness'].default_value = 0.25
                
            elif "calvin" in obj_key and "switch" in obj_key:
                mat = bpy.data.materials.new(name="Handle")
                mat.use_nodes = True
                nodes = mat.node_tree.nodes
                bsdf = nodes.get("Principled BSDF")
                bsdf.inputs["Base Color"].default_value = [0.2, 0.2, 0.2, 1]
                bsdf.inputs['Coat Weight'].default_value = 0.4
                bsdf.inputs['Coat Roughness'].default_value = 0.25
                
                mesh_obj.data.materials[0] = mat

            elif "calvin" in obj_key and ("led" in obj_key or "light" in obj_key):
                if len(mesh_obj.data.materials) > 0:
                    mesh_obj.data.materials[0] = glass_texture
                else:
                    mesh_obj.data.materials.append(glass_texture)
            
            elif "calvin" in obj_key and "button" in obj_key:
                mat = bpy.data.materials.new(name="Button")
                mat.use_nodes = True
                nodes = mat.node_tree.nodes
                bsdf = nodes.get("Principled BSDF")
                bsdf.inputs["Base Color"].default_value = [0, 0, 0, 1]
                bsdf.inputs['Coat Weight'].default_value = 0.6
                bsdf.inputs['Coat Roughness'].default_value = 0.1
                mesh_obj.data.materials.append(mat)
                
            bpy.context.view_layer.objects.active = None # important line so the color doesn't bleed 