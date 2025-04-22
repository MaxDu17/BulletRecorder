import bpy

# Iterate through all objects in the scene
for obj in bpy.data.objects:
    # Check if the object has animation data
    if obj.animation_data:
        # Clear all keyframes by removing the action
        obj.animation_data_clear()