import pybullet as p
# import PySimpleGUI as sg
import pickle
from os import getcwd
from urdfpy import URDF
from os.path import abspath, dirname, basename, splitext
from transforms3d.affines import decompose
from transforms3d.quaternions import mat2quat
import numpy as np


class PyBulletRecorder:
    class CubeTracker:
        def __init__(self,
                     name,
                     body_id,
                     link_id,
                     link_origin,
                     cube_dims,
                     color,
                     mesh_scale):
            self.body_id = body_id
            self.link_id = link_id
            self.mesh_scale = mesh_scale
            self.cube_dims = cube_dims 
            decomposed_origin = decompose(link_origin)
            orn = mat2quat(decomposed_origin[1])
            orn = [orn[1], orn[2], orn[3], orn[0]]
            self.link_pose = [decomposed_origin[0],
                              orn]
            self.name = name
            self.color = color 

        def transform(self, position, orientation):
            return p.multiplyTransforms(
                position, orientation,
                self.link_pose[0], self.link_pose[1],
            )

        def get_keyframe(self):
            if self.link_id == -1:
                position, orientation = p.getBasePositionAndOrientation(
                    self.body_id)
                position, orientation = self.transform(
                    position=position, orientation=orientation)
            else:
                link_state = p.getLinkState(self.body_id,
                                            self.link_id,
                                            computeForwardKinematics=True)
                position, orientation = self.transform(
                    position=link_state[4],
                    orientation=link_state[5])
            return {
                'position': list(position),
                'orientation': list(orientation)
            }
    
    class LinkTracker:
        def __init__(self,
                     name,
                     body_id,
                     link_id,
                     link_origin,
                     mesh_path,
                     mesh_scale):
            self.body_id = body_id
            self.link_id = link_id
            self.mesh_path = mesh_path
            self.mesh_scale = mesh_scale
            decomposed_origin = decompose(link_origin)
            orn = mat2quat(decomposed_origin[1])
            orn = [orn[1], orn[2], orn[3], orn[0]]
            self.link_pose = [decomposed_origin[0],
                              orn]
            self.name = name

        def transform(self, position, orientation):
            return p.multiplyTransforms(
                position, orientation,
                self.link_pose[0], self.link_pose[1],
            )

        def get_keyframe(self):
            if self.link_id == -1:
                position, orientation = p.getBasePositionAndOrientation(
                    self.body_id)
                position, orientation = self.transform(
                    position=position, orientation=orientation)
            else:
                link_state = p.getLinkState(self.body_id,
                                            self.link_id,
                                            computeForwardKinematics=True)
                position, orientation = self.transform(
                    position=link_state[4],
                    orientation=link_state[5])
            return {
                'position': list(position),
                'orientation': list(orientation)
            }

    def __init__(self, filename):
        self.states = [[]]
        self.links = []
        self.filename = filename 

    def register_object(self, body_id, urdf_path, global_scaling=1):
        link_id_map = dict()
        n = p.getNumJoints(body_id)
        print(urdf_path)
        link_id_map[p.getBodyInfo(body_id)[0].decode('gb2312')] = -1
        for link_id in range(0, n):
            link_id_map[p.getJointInfo(body_id, link_id)[
                12].decode('gb2312')] = link_id

        dir_path = dirname(abspath(urdf_path))
        file_name = splitext(basename(urdf_path))[0]
        robot = URDF.load(urdf_path)
        for link in robot.links:
            link_id = link_id_map[link.name]
            if len(link.visuals) > 0:
                for i, link_visual in enumerate(link.visuals):
                    #TODO: SUPPORT PRIMIVITVES
                    if link_visual.geometry.mesh is None and link_visual.geometry.box is None:
                        print("Skipping ", link.name)
                        continue # this is for invisible things like cameras 
                    elif link_visual.geometry.box is not None:
                        mesh_scale = [global_scaling,
                                    global_scaling, global_scaling]
                            #         \
                            # if link_visual.geometry.mesh.scale is None \
                            # else link_visual.geometry.mesh.scale * global_scaling
                        self.links.append(
                            PyBulletRecorder.CubeTracker(
                                name=file_name + f'_{body_id}_{link.name}_{i}',
                                body_id=body_id,
                                link_id=link_id,
                                color = link_visual.material.color,
                                link_origin=  # If link_id == -1 then is base link,
                                # PyBullet will return
                                # inertial_origin @ visual_origin,
                                # so need to undo that transform
                                (np.linalg.inv(link.inertial.origin)
                                if link_id == -1
                                else np.identity(4)) @
                                link_visual.origin * global_scaling,
                                cube_dims = link_visual.geometry.box.size,
                                mesh_scale=mesh_scale))
                    else: 
                        mesh_scale = [global_scaling,
                                    global_scaling, global_scaling]\
                            if link_visual.geometry.mesh.scale is None \
                            else link_visual.geometry.mesh.scale * global_scaling
                        self.links.append(
                            PyBulletRecorder.LinkTracker(
                                name=file_name + f'_{body_id}_{link.name}_{i}',
                                body_id=body_id,
                                link_id=link_id,
                                link_origin=  # If link_id == -1 then is base link,
                                # PyBullet will return
                                # inertial_origin @ visual_origin,
                                # so need to undo that transform
                                (np.linalg.inv(link.inertial.origin)
                                if link_id == -1
                                else np.identity(4)) @
                                link_visual.origin * global_scaling,
                                mesh_path=dir_path + '/' +
                                link_visual.geometry.mesh.filename,
                                mesh_scale=mesh_scale))
    def new_episode(self):
        self.states.append(list())

    def add_keyframe(self):
        # Ideally, call every p.stepSimulation()
        current_state = {}
        for link in self.links:
            current_state[link.name] = link.get_keyframe()
        # print("\t", len(self.states))
        self.states[-1].append(current_state) # add to the current trajectory 

    # def prompt_save(self):
    #     layout = [[sg.Text('Do you want to save previous episode?')],
    #               [sg.Button('Yes'), sg.Button('No')]]
    #     window = sg.Window('PyBullet Recorder', layout)
    #     save = False
    #     while True:
    #         event, values = window.read()
    #         if event in (None, 'No'):
    #             break
    #         elif event == 'Yes':
    #             save = True
    #             break
    #     window.close()
    #     if save:
    #         layout = [[sg.Text('Where do you want to save it?')],
    #                   [sg.Text('Path'), sg.InputText(getcwd())],
    #                   [sg.Button('OK')]]
    #         window = sg.Window('PyBullet Recorder', layout)
    #         event, values = window.read()
    #         window.close()
    #         self.save(values[0])
    #     self.reset()

    def reset(self):
        self.states = []

    def get_formatted_output(self):
        retval = {}
        for link in self.links:
            print(link.name)
            if isinstance(link, PyBulletRecorder.LinkTracker):
                retval[link.name] = {
                    'type': 'mesh',
                    'mesh_path': link.mesh_path,
                    'mesh_scale': link.mesh_scale,
                    # 'frames': [state[link.name] for state in self.states]
                    'frames': [[state[link.name] for state in episode] for episode in self.states]
                }
            if isinstance(link, PyBulletRecorder.CubeTracker):
                retval[link.name] = {
                    'type': 'cube',
                    "scale" : link.cube_dims,
                    "color": link.color,
                    # 'frames': [state[link.name] for state in self.states]
                    'frames': [[state[link.name] for state in episode] for episode in self.states]
                }
        return retval

    def save(self): #, path = None):
        # if path is None:
        #     print("[Recorder] Path is None.. not saving")
        # else:
        print("[Recorder] Saving state to {}".format(self.filename))
        pickle.dump(self.get_formatted_output(), open(self.filename, 'wb'))
