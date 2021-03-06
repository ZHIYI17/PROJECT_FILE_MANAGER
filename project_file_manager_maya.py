import inspect
import os
import sys
import time
import subprocess
import ctypes
import shutil
import Queue
from pprint import pprint
from functools import partial, wraps

try:
    from PySide2.QtCore import * 
    from PySide2.QtGui import * 
    from PySide2.QtWidgets import *
    from PySide2.QtUiTools import *
    from shiboken2 import wrapInstance 
except ImportError:
    from PySide.QtCore import * 
    from PySide.QtGui import * 
    from PySide.QtUiTools import *
    from shiboken import wrapInstance 

from maya import OpenMayaUI as omui   
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

mayaMainWindowPtr = omui.MQtUtil.mainWindow() 
mayaMainWindow = wrapInstance(long(mayaMainWindowPtr), QWidget) 

import maya.cmds as cmds
import maya.mel as mel

current_python_file_directory = r'D:/DEV/PROJECT_FILE_MANAGER/'
sys.path.append(current_python_file_directory)
import configuration_maya

VLC_PLAYER = r'C:/Applications/vlc-2.2.4-win64/vlc.exe'
img_exts = ['png', 'jpg', 'jpeg', 'tif', 'tiff', 'bmp']
vid_exts = ['mov', 'mpeg', 'avi', 'mp4', 'wmv']

current_python_file_directory = r'D:/DEV/PROJECT_FILE_MANAGER/'

# =======================================================
# ======= the implementation of Folder Structures =======
# =======================================================
class Maya_Project(object):
    """
    - create structural folders for the project
    - can dynamtically add new scene-shot folders for all the shot-based directories
    """
    def __init__(self, project_name, dict_amount):
        self.project_name = project_name
        self.project_root_directory = project_manager_gui.select_drive_combo_box.currentText()
        self.project_directory = self.project_root_directory + self.project_name + '/'
        self.dict_amount = dict_amount
        self.make_folder_structure()    

        # generates initial maya shot files
        self.make_init_maya_shot_files(self.dict_amount)  


    def generate_maya_project(self):
        '''
        - get the drive letter and project name 
        - use maya's commands to generate the project folder
        '''
        try:
            os.mkdir(self.project_directory)
        except WindowsError:
            pass
        cmds.workspace(directory = self.project_directory)
        mel.eval('setProject "{}"'.format(self.project_directory))
        mel.eval("projectWindow;")
        mel.eval("np_editCurrentProjectCallback;")

        #clean up some unuseful folders
        shutil.rmtree(self.project_directory + 'Time Editor/Clip Exports/')
        shutil.rmtree(self.project_directory + 'cache/bifrost/')
        shutil.rmtree(self.project_directory + 'cache/nCache/')
        shutil.rmtree(self.project_directory + 'cache/particles/')
        shutil.rmtree(self.project_directory + 'sourceimages/3dPaintTextures/')
        shutil.rmtree(self.project_directory + 'scenes/edits/')


    def directories_for_shots(self):
        '''
        - this function returns a list of directories that hold scene-shot hierarchical folders
        - it only works for the first time when the whole project structure is created and there's no scene-shot folders 
        '''        
        scenes_folder           = self.project_directory + 'scenes/'
        images_folder           = self.project_directory + 'images/'
        movies_folder           = self.project_directory + 'movies/'
        sound_folder            = self.project_directory + 'sound/'
        time_editor_folder      = self.project_directory + 'Time Editor/' 
        cache_folder            = self.project_directory + 'cache/'

        directories = [scenes_folder, images_folder, movies_folder, time_editor_folder, cache_folder, sound_folder]

        return directories    


    def __make_hierarchical_folders(self, parent_dir, parent_name, child_name):
        '''
        - this function generates folders based on given amount of parent folders and their amount of sub-folders
        - the amount of sub-folders might be vary 
        - parent_name is the base name of all the parent folders, it refers to "scene" folders in most of cases
        - child_name is the base name of all the child folders, it refers to "shot" folders in most of cases
        - parent_dir is a string type, make sure to be end with '/'
        - dict_amount is a dictionary type, it looks like: {<scn_num>:<amount_of_shots>}, for example: {1:10,2:7,...}
        - can pass a new dict, which adds new "scene" folders and their "shot" folders
        - for example: dir = r'Z:\CG_Production_File_Structure\ANIMATION\Finals'
        the first time you use make_hierarchical_folders(dir,'scn','__shot',{1:10,2:17,3:37})
        it generates:  "scn1" with 10 "__shot" sub folders 
                       "scn2" with 17 "__shot" sub folders 
                       "scn1" with 37 "__shot" sub folders 
        the second time you use make_hierarchical_folders(dir,'scn','__shot',{1:14,4:31})
        it updates: "scn1" with 14 "__shot" sub folders 
        and adds:   "scn4" with 31 "__shot" sub folders 
        '''
        dir = unix_format(parent_dir)
    
        #list all the folders in parent_dir
        current_folders = os.listdir(dir)

        parent_folder_surffix_digits = self.dict_amount.keys()

        #create parent folders
        for i in parent_folder_surffix_digits:
            #check whether the parent_folder is alread existed in current_folders or not
            parent_folder_name = parent_name + str(i)
            if parent_folder_name not in current_folders:
                make_folders(dir,parent_folder_name)
    
        #iterate all the parent folders and create their sub folders based on the given numbers
        for k, v in self.dict_amount.iteritems():
            # k is the scene number, and v is the amount of shots for certain scene
            # sub_dir is one of the parent_folders under the parent_dir, which should be the "scene" folders               
            sub_dir = dir + parent_name + str(k) + '/'
            #list all the sub folders under current "scene" folder
            current_sub_folders = os.listdir(sub_dir)
            amount_of_sub_folders = v
            sub_folder_surffix_digits = []
            if v < 1:
                break
            if v == 1: 
                sub_folder_name = child_name + str(v)
                if sub_folder_name not in current_sub_folders:
                    make_folders(sub_dir,sub_folder_name)
            if v > 1:
                sub_folder_surffix_digits = range(v)
                # range(v) --> [0,1,...,(v-1)]
                # we desire the surffix begins from 1 rather than 0
                if sub_folder_surffix_digits[0] == 0:          
                    start_num = 1              
                # sub_folder_surffix_digits[-1] = (v-1)
                # (v-1) + 2 = (v + 1)
                # range(1, (v+1)) --> [1,2,...,v]
                end_num = sub_folder_surffix_digits[-1] + 2
                for i in range(start_num, end_num):     
                    sub_folder_name = child_name + str(i)
                    if sub_folder_name not in current_sub_folders:
                        make_folders(sub_dir,sub_folder_name)


    def generate_scene_shot_folders(self):
        '''
        - this function generate scene-shots folders for directories_for_shots
        - can pass new dict_amount then call this function in order to add new scene-shot folders
        - dict_amount is a dictionary type, it looks like: {<scn_num>:<amount_of_shots>}, for example: {1:10,2:7,...}
        '''
        dirs_for_shots = self.directories_for_shots()
        try:
            for dir in dirs_for_shots:
                self.__make_hierarchical_folders(dir,'SCENE_','__Shot_')    

            self.make_hidden_folders('backup') 
            self.make_hidden_folders('script')   
                    
        except WindowsError:
            pass 

    def __make_dict_folders(self, parent_dir, folder_dict):
        '''
        - parent_dir is string type, which indicates the directory
        - folder_dict is dictionary, which the keys are the parent folders and values are the sub folders
        - folder_dict can be a nested dictionary, however, the type of all the values must be list.
        - for example,
              dir = r'Z:\zzz\2D' 
              d = {'a':['a1','a2','a3'],'b':['b1','b2',b3],'c':c,'z':v}     
              b3 = {'b3':['b3_1','b3_2'],'b4':['b4_1','b4_2'],'b5':b5}
              b5 = {'b5_5':['b5_1','b5_2']}
              v = {'av':['az']}
              c = {'cc':['c1','c2','c3']}
          make_dict_folders(dir,d) this will generate a folder structure like:
          a
          |----a1
          |----a2
          |----a3
          
          b
          |----b1
          |----b2
          |----b3
                |----b3_1
                |----b3_2
          |----b4
                |----b4_1
                |----b4_2
          |----b5
                |----b5_5
                        |----b5_1
                        |----b5_2
          
          c
          |----cc
                |----c1
                |----c2
                |----c3
          
          z
          |----av
                |----az
        '''
        dir = unix_format(parent_dir) 
        # list all the folders in current parent_dir
        current_parent_folders = os.listdir(dir)
        # iterate all keys in folder_dict, which are folders that contain child folders
        for folder in folder_dict.keys():
            folder_dir = dir + folder + '/'
            # creates parnet folders under the parent_dir
            if folder not in current_parent_folders:        
                os.mkdir(folder_dir)
            # list all the sub folders under current parent folder
            current_sub_folders = os.listdir(folder_dir)
            # use recursion to handle those "nested dict" in dict-values, 
            # it recursively iterates all the elements until there're no more dict, then execute codes from line 163
            if type(folder_dict[folder]) == dict:
                self.__make_dict_folders(folder_dir,folder_dict[folder])        
            else: 
                # if current dict-value is not dictionary, then we iterates elements of the list
                for sub_folder in folder_dict[folder]:
                    sub_folder_dir = folder_dir + str(sub_folder) + '/'  
                    # use recursion to handle those "nested dict" in list-elements
                    # it recursively iterates all the elements until there're no more dict, then execute codes from line 163
                    if type(sub_folder) == dict:
                        self.__make_dict_folders(folder_dir,sub_folder)
                    #can also pass an empty list, which indicates there's no sub folder under current parent folder
                    elif sub_folder == []:
                        os.mkdir(folder_dir)
                    else:
                    # finally, there're no more nested dict, can create folders one by one based on the elements from the list
                        if sub_folder not in current_sub_folders:                  
                            os.mkdir(sub_folder_dir)                 


    def make_folder_structure(self):
        '''
        this function enhances the Maya-generated project folder by adding extra folders based on the configuration_maya.py
        '''
        self.generate_maya_project()

        asset_directory = self.project_directory + r'assets/'

        try:
            # create department folders        
            self.__make_dict_folders(asset_directory, configuration_maya.assets)
            self.make_hidden_folders('backup') 
            self.make_hidden_folders('script') 
            # creates scene-shots hierarchical folders
            self.generate_scene_shot_folders()

        except AttributeError:
            pass


    def make_hidden_folders(self, folder_name):
        '''
        - create a hidden folders for all the 3d assets and shot files
        - useful for making '___backup' folder and '___script' folder 
        - can pass 'backup' or 'script' for the 'folder_name'
        '''
        # collect the proper dirs for the 'backup' folder
        dirs_for_hidden_folders = []

        for path, dirs, files in os.walk(self.project_directory):
            path = unix_format(path)
            if path.split('/')[-2][:2] == '__' and path.split('/')[-2][:3] != '___':
                dirs_for_hidden_folders.append(path) 
        
        # create the 'backup' folders in collected dirs above

        for dir in dirs_for_hidden_folders:
            folder_dir = unix_format(dir) + '___' + folder_name
            try:
                
                os.mkdir(folder_dir)
            except WindowsError:
                pass 
            # hide the folder 
            if os.path.isdir(folder_dir):               
                # SetFileAttributesW(unicode(folder_dir), 2) ----> hide the folder
                # SetFileAttributesW(unicode(folder_dir), 1) ----> unhide the folder
                ctypes.windll.kernel32.SetFileAttributesW(unicode(folder_dir), 2)


    def add_scene_shot_folders(self, new_dict_amount):
        '''
        - this function adds new scene-shots folders for directories_for_shots
        - can pass new dict_amount then call this function in order to add new scene-shot folders
        - dict_amount is a dictionary type, it looks like: {<scn_num>:<amount_of_shots>}, for example: {1:10,2:7,...}
        '''
        try:
            for k, v in new_dict_amount.iteritems():
                update_shot_dict(self.dict_amount, k, v)
            dirs_for_shots = self.directories_for_shots()
            for dir in dirs_for_shots:
                self.__make_hierarchical_folders(dir,'SCENE_','__Shot_')

            self.make_hidden_folders('backup') 
            self.make_hidden_folders('script')  

            self.make_init_maya_shot_files(new_dict_amount)  
        except AttributeError:
            pass            


    def exec_once_when_init(in_class_method):
        @wraps(in_class_method)
        def wrapper( *args, **kwargs):
            if not wrapper.called:
                return in_class_method(*args, **kwargs)
        wrapper.called = False
        return wrapper


    def get_char_rig_dir(self):
        '''
        - this function returns a list of directories for rigged chars.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'SETUP' and dir.split('/')[3] == 'Characters' and dir.split('/')[4] == 'Rigged':
                return dir


    def get_char_def_dir(self):
        '''
        - this function returns a list of directories for deformed chars.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'SETUP' and dir.split('/')[3] == 'Characters' and dir.split('/')[4] == 'Deformed':
                return dir


    def get_props_rig_dir(self):
        '''
        - this function returns a list of directories for rigged chars.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'SETUP' and dir.split('/')[3] == 'Props' and dir.split('/')[4] == 'Rigged':
                return dir


    def get_props_def_dir(self):
        '''
        - this function returns a list of directories for deformed props.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'SETUP' and dir.split('/')[3] == 'Props' and dir.split('/')[4] == 'Deformed':
                return dir                


    def get_props_hiGeo_dir(self):
        '''
        - this function returns a list of directories for hi-geo props.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'MODEL' and dir.split('/')[3] == 'Props' and dir.split('/')[4] == 'High_Resolution':
                return dir


    def get_props_lowGeo_dir(self):
        '''
        - this function returns a list of directories for low-geo props.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'MODEL' and dir.split('/')[3] == 'Props' and dir.split('/')[4] == 'Low_Resolution':
                return dir 


    def get_char_hiGeo_dir(self):
        '''
        - this function returns a list of directories for hi-geo chars.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'MODEL' and dir.split('/')[3] == 'Characters' and dir.split('/')[4] == 'High_Resolution':
                return dir


    def get_char_lowGeo_dir(self):
        '''
        - this function returns a list of directories for low-geo chars.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'MODEL' and dir.split('/')[3] == 'Characters' and dir.split('/')[4] == 'Low_Resolution':
                return dir 


    def get_env_hiGeo_dir(self):
        '''
        - this function returns a list of directories for hi-geo assembled-scenes.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'MODEL' and dir.split('/')[3] == 'Environments' and dir.split('/')[4] == 'High_Resolution' and dir.split('/')[5] == 'Assembled_Scenes':
                return dir


    def get_env_lowGeo_dir(self):
        '''
        - this function returns a list of directories for low-geo assembled-scenes.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'MODEL' and dir.split('/')[3] == 'Environments' and dir.split('/')[4] == 'Low_Resolution' and dir.split('/')[5] == 'Assembled_Scenes':
                return dir 


    def get_com_hiGeo_dir(self):
        '''
        - this function returns a list of directories for hi-geo components.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'MODEL' and dir.split('/')[3] == 'Environments' and dir.split('/')[4] == 'High_Resolution' and dir.split('/')[5] == 'Components':
                return dir


    def get_com_lowGeo_dir(self):
        '''
        - this function returns a list of directories for low-geo components.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'MODEL' and dir.split('/')[3] == 'Environments' and dir.split('/')[4] == 'Low_Resolution' and dir.split('/')[5] == 'Components':
                return dir 


    def get_char_shader_dir(self):
        '''
        - this function returns a list of directories for shaders of chars.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'SURFACING' and dir.split('/')[3] == 'Shaders' and dir.split('/')[4] == 'Characters':
                return dir 


    def get_env_shader_dir(self):
        '''
        - this function returns a list of directories for shaders of environment components.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'SURFACING' and dir.split('/')[3] == 'Shaders' and dir.split('/')[4] == 'Components':
                return dir     


    def get_props_shader_dir(self):
        '''
        - this function returns a list of directories for shaders of props.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'SURFACING' and dir.split('/')[3] == 'Shaders' and dir.split('/')[4] == 'Props':
                return dir   


    def get_char_texture_dir(self):
        '''
        - this function returns a list of directories for texture of chars.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'SURFACING' and dir.split('/')[3] == 'Textures' and dir.split('/')[4] == 'Characters':
                return dir 


    def get_env_texture_dir(self):
        '''
        - this function returns a list of directories for texture of environment components.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'SURFACING' and dir.split('/')[3] == 'Textures' and dir.split('/')[4] == 'Components':
                return dir     


    def get_props_texture_dir(self):
        '''
        - this function returns a list of directories for texture of props.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'SURFACING' and dir.split('/')[3] == 'Textures' and dir.split('/')[4] == 'Props':
                return dir                   


    def get_char_light_template_dir(self):
        '''
        - this function returns a list of directories for Templates of characters lighting.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'LIGHTING' and dir.split('/')[3] == 'Templates' and dir.split('/')[4] == 'Characters':
                return dir 


    def get_env_light_template_dir(self):
        '''
        - this function returns a list of directories for Templates of environment lighting.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'LIGHTING' and dir.split('/')[3] == 'Templates' and dir.split('/')[4] == 'Environments':
                return dir 


    def get_render_template_dir(self):
        '''
        - this function returns a list of directories for Templates of render settings.
        '''
        all_asset_dirs = self.get_directories_for_assets_attr
        for dir in all_asset_dirs:
            if dir.split('/')[2] == 'LIGHTING' and dir.split('/')[3] == 'Templates' and dir.split('/')[4] == 'Rendering':
                return dir 


    def make_render_template_dirs(self, template_name):
        '''
        - this function creates render template folders in the associated directories
        - if the given 'template_name' is already existed in the directory, then the function skips creating folder
        '''
        parent_directory = self.get_render_template_dir()
       
        if template_name[:2] != '__':
            add_double_under_scores(template_name)

        template_dir = parent_directory + template_name
                   
        if not os.path.exists(template_dir):
            os.mkdir(template_dir) 
            self.add_hidden_folders(template_dir)


    def make_char_template_dirs(self, template_name):
        '''
        - this function creates render template folders in the associated directories
        - if the given 'template_name' is already existed in the directory, then the function skips creating folder
        '''
        parent_directory = self.get_char_light_template_dir()
       
        if template_name[:2] != '__':
            add_double_under_scores(template_name)

        template_dir = parent_directory + template_name
                   
        if not os.path.exists(template_dir):
            os.mkdir(template_dir) 
            self.add_hidden_folders(template_dir)


    def make_env_template_dirs(self, template_name):
        '''
        - this function creates render template folders in the associated directories
        - if the given 'template_name' is already existed in the directory, then the function skips creating folder
        '''
        parent_directory = self.get_env_light_template_dir()
       
        if template_name[:2] != '__':
            add_double_under_scores(template_name)

        template_dir = parent_directory + template_name
                   
        if not os.path.exists(template_dir):
            os.mkdir(template_dir) 
            self.add_hidden_folders(template_dir)                        


    def get_char_dirs(self, *char_name):
        '''
        - this function returns a list of associated dirs for all characters.
        - if char_name is specified, then it only returns dirs for the given character.
        '''
        all_char_dirs = []
        all_char_dirs.append(self.get_char_rig_dir())
        all_char_dirs.append(self.get_char_def_dir())
        all_char_dirs.append(self.get_char_hiGeo_dir())
        all_char_dirs.append(self.get_char_lowGeo_dir())
        all_char_dirs.append(self.get_char_texture_dir())
        all_char_dirs.append(self.get_char_shader_dir())
        all_char_dirs.append(self.get_char_light_template_dir())
        
        char_dir = []
        if list(char_name) != []:
            for dir in all_char_dirs:
                char_folders = os.listdir(dir)        
                char_folder = '__' + char_name[0]
                if char_folders != [] and char_folder in char_folders: 
                    dir += char_folder + '/'
                    char_dir.append(dir)
                else:
                    #print dir + char_folder + '/ is not existed' 
                    pass
            return char_dir
        else:
            return all_char_dirs 


    def make_char_dirs(self, *chars_name):
        '''
        - this function creates character folders in all the associated directories
        - can pass multiple names of characters
        '''
        all_char_dirs = self.get_char_dirs()
        if list(chars_name) != []:
            for dir in all_char_dirs:
                for char in chars_name:
                    if char[:2] != '__':
                        add_double_under_scores(char)
                    char_dir = dir + char
                    if not os.path.exists(char_dir) :
                        os.mkdir(char_dir)
                        self.add_hidden_folders(char_dir)

            for char in chars_name:
                # create initial geo files
                self.make_init_maya_file('geo_hi_char', char)
                self.make_init_maya_file('geo_low_char', char)
                #create initial rig files
                self.make_init_maya_file_with_references(char, 'geo_hi_char', 'def_char')
                self.make_init_maya_file_with_references(char, 'geo_low_char', 'rig_char')
                #create initial surfacing files
                self.make_init_maya_file_with_references(char, 'geo_hi_char', 'surf_char')
                #create initial lighting template files
                self.make_init_maya_file_with_references(char, 'geo_hi_char', 'ligtemp_char')
           
           
    def get_props_dirs(self, *props_name):
        '''
        - this function returns a list of associated dirs for all props.
        - if props_name is specified, then it only returns dirs for the given character.
        '''
        all_props_dirs = []
        all_props_dirs.append(self.get_props_rig_dir())
        all_props_dirs.append(self.get_props_def_dir())
        all_props_dirs.append(self.get_props_hiGeo_dir())
        all_props_dirs.append(self.get_props_lowGeo_dir())
        all_props_dirs.append(self.get_props_texture_dir())
        all_props_dirs.append(self.get_props_shader_dir())
         
        props_dir = []
        if list(props_name) != []:
            for dir in all_props_dirs:
                props_folders = os.listdir(dir)        
                props_folder = '__' + props_name[0]
                if props_folders != [] and props_folder in props_folders: 
                    dir += props_folder + '/'
                    props_dir.append(dir)
                else:
                    #print dir + props_folder + '/ is not existed' 
                    pass
            return props_dir
        else:
            return all_props_dirs 


    def make_props_dirs(self, *props_name):
        '''
        - this function creates props folders in all the associated directories
        - can pass multiple names of props
        '''
        all_props_dirs = self.get_props_dirs()
        if list(props_name) != []:
            for dir in all_props_dirs:
                for props in props_name:
                    if props[:2] != '__':
                        add_double_under_scores(props)                    
                    props_dir = dir + props
                    if not os.path.exists(props_dir) :
                        os.mkdir(props_dir)
                        self.add_hidden_folders(props_dir)

            for props in props_name:
                # create initial geo files
                self.make_init_maya_file('geo_hi_props', props)
                self.make_init_maya_file('geo_low_props', props)
                #create initial rig files
                self.make_init_maya_file_with_references(props, 'geo_hi_props', 'def_props')
                self.make_init_maya_file_with_references(props, 'geo_low_props', 'rig_props')
                #create initial surfacing files
                self.make_init_maya_file_with_references(props, 'geo_hi_props', 'surf_props')        


    def get_com_dirs(self, *com_name):
        '''
        - this function returns a list of associated dirs for all components.
        - if com_name is specified, then it only returns dirs for the given component.
        '''
        all_com_dirs = []
        #all_com_dirs.append(self.get_env_hiGeo_dir()) 
        #all_com_dirs.append(self.get_env_lowGeo_dir()) 
        all_com_dirs.append(self.get_com_hiGeo_dir())
        all_com_dirs.append(self.get_com_lowGeo_dir())
        all_com_dirs.append(self.get_env_shader_dir())
        all_com_dirs.append(self.get_env_texture_dir())
        
        com_dir = []
        if list(com_name) != []:
            for dir in all_com_dirs:
                com_folders = os.listdir(dir)        
                com_folder = '__' + com_name[0]
                if com_folders != [] and com_folder in com_folders: 
                    dir += com_folder + '/'
                    com_dir.append(dir)
                else:
                    #print dir + com_folder + '/ is not existed' 
                    pass
            return com_dir
        else:
            return all_com_dirs 


    def make_com_dirs(self, *com_name):
        '''
        - this function creates components folders in all the associated directories
        - can pass multiple names of components
        '''
        all_com_dirs = self.get_com_dirs()
        if list(com_name) != []:
            for dir in all_com_dirs:
                for com in com_name:
                    if com[:2] != '__':
                        add_double_under_scores(com)                       
                    com_dir = dir + com
                    if not os.path.exists(com_dir) :
                        os.mkdir(com_dir)
                        self.add_hidden_folders(com_dir)

            for com in com_name:
                # create initial geo files
                self.make_init_maya_file('geo_hi_com', com)
                self.make_init_maya_file('geo_low_com', com)
                #create initial surfacing files
                self.make_init_maya_file_with_references(com, 'geo_hi_com', 'surf_com')     


    def get_env_dirs(self, *env_name):
        '''
        - this function returns a list of associated dirs for all environment.
        - if env_name is specified, then it only returns dirs for the given environment.
        '''
        all_env_dirs = []
        all_env_dirs.append(self.get_env_hiGeo_dir())
        all_env_dirs.append(self.get_env_lowGeo_dir())
        all_env_dirs.append(self.get_env_light_template_dir())
        
        #all_com_dirs.append(self.get_com_hiGeo_dir())
        #all_com_dirs.append(self.get_com_lowGeo_dir())
        #all_com_dirs.append(self.get_env_shader_dir())
        #all_com_dirs.append(self.get_env_texture_dir())
        
        env_dir = []
        if list(env_name) != []:
            for dir in all_env_dirs:
                env_folders = os.listdir(dir)        
                env_folder = '__' + env_name[0]
                if env_folders != [] and env_folder in env_folders: 
                    dir += env_folder + '/'
                    env_dir.append(dir)
                else:
                    #print dir + env_folder + '/ is not existed' 
                    pass
            return env_dir
        else:
            return all_env_dirs 


    def make_env_dirs(self, *envs_name):
        '''
        - this function creates environment folders in all the associated directories
        - can pass multiple names of environment
        '''
        all_env_dirs = self.get_env_dirs()
        if list(envs_name) != []:
            for dir in all_env_dirs:
                for env in envs_name:
                    if env[:2] != '__':
                        add_double_under_scores(env)                            
                    env_dir = dir + env
                    if not os.path.exists(env_dir):
                        os.mkdir(env_dir)
                        self.add_hidden_folders(env_dir)

            for env in envs_name:
                self.make_init_maya_file('geo_hi_env', env)
                self.make_init_maya_file('geo_low_env', env)
                #create initial lighting template files
                self.make_init_maya_file_with_references(env, 'geo_hi_env', 'ligtemp_env')    


    def make_file_version(self,dir,file_name):
        '''
        - the file_name should not come with the file extensions.
        - when calling current function, the given file_name SHOULD NOT CONTAIN ANY VERSION SUFFIX AND FILE EXTENSIONS.
        - this function determines if the given file name is already existed in the given directory.
        - it will automatically make an unique version suffix if the given name is existed.
        - also can generate an initial version as suffix if the given is not existed.
        - returns an usable file_name with a proper version number as suffix
        - for example: 
           "test.ma", "test_v17.ma", "xxx_v3.ma" are already existed in the dir
           make_file_version(dir,'test')        ---> returns "__test_v18"
           make_file_version(dir,'test_v19')    ---> returns "__test_v19_v0"
           make_file_version(dir,'xxx')         ---> returns "__xxx_v4"
        '''
        dir = unix_format(dir)
        all_exist_files = os.listdir(dir)
        
        matched_files = []
        current_versions = []
        new_version = 0
        
        
        # check if the given file_name or the base name is already existed
        # if not, then means the given file_name is a brand new file
        for file in all_exist_files:
            # remove the file extensions
            base_name = file.split('.')[0] # ---> 'XXX_v#' or 'XXX' without the version suffix
            # base_name is 'XXX_v#' with the version suffix 
            if '_v-' in base_name:
                exist_file_and_version = base_name.split('_v-') # ---> ['XXX', #]                
                if exist_file_and_version[0] == file_name: 
                    matched_files.append(file)                       
                
        # collect current versions
        if matched_files != []:
            for file in matched_files:
                # remove the file extensions
                base_name = file.split('.')[0] # ---> 'XXX_v#'

                exist_file_and_version = base_name.split('_v-') # ---> ['XXX', #]
                version = exist_file_and_version[1]
                current_versions.append(int(version))
       
            new_version = max(current_versions) + 1
            return file_name + '_v-' + str(new_version)
            
        else:
            new_version = 0
            return file_name + '_v-' + str(new_version)        



    def get_shot_file_dir(self, scn_number, shot_number): 
        '''
        - returns a directory for the given scene-shot Maya animation file
        '''
        parent_directory = self.project_directory + 'scenes/'
      
        shot_dir = parent_directory + 'SCENE_{0}/__Shot_{1}/'.format(str(scn_number), str(shot_number))        
  
        return unix_format(shot_dir)

        
    def make_maya_shot_file_strings(self, type, scn_number, shot_number):
        '''
        - returns a proper Maya file name and directory for the given type, scene and shot number.
        - type is string type, only accepts keys of self.maya_shot_directories_dict
        - scn_number and shot_number are int type.
        '''    
        
        # retrive the exact directory 

        shot_dir = self.get_shot_file_dir(scn_number, shot_number)

        shot = type + 'scene_{0}_shot_{1}.ma'.format(str(scn_number), str(shot_number))        
        #shot_file_name = self.make_file_version(dir, shot)
        
        return windows_format(shot_dir + shot)
        
    
    def make_init_maya_shot_files(self, dict_scene_shot):
        '''
        - this function generates empty maya files for all the shots based on the given dictionary of scene-shots
        - 'dict_scene_shot' is an argument of dict type
        '''
        empty_maya_file = windows_format(current_python_file_directory + 'empty.ma')

        for scn_number, shot_amount in dict_scene_shot.iteritems():          
            
            for shot_number in range(shot_amount):

                anim_shot_file          =   self.make_maya_shot_file_strings('anim_',       scn_number, (shot_number+1))
                layout_shot_file        =   self.make_maya_shot_file_strings('layout_',     scn_number, (shot_number+1))
                vfx_shot_file           =   self.make_maya_shot_file_strings('vfx_',        scn_number, (shot_number+1))
                render_shot_file        =   self.make_maya_shot_file_strings('render_',     scn_number, (shot_number+1))
                light_shot_file         =   self.make_maya_shot_file_strings('light_',      scn_number, (shot_number+1))
                geo_shot_file           =   self.make_maya_shot_file_strings('geo_',        scn_number, (shot_number+1))
               
                if not os.path.isfile(anim_shot_file):
                    shutil.copyfile(empty_maya_file, anim_shot_file)
                else:
                    pass

                if not os.path.isfile(layout_shot_file):
                    shutil.copyfile(empty_maya_file, layout_shot_file)
                else:
                    pass                    

                if not os.path.isfile(vfx_shot_file):
                    shutil.copyfile(empty_maya_file, vfx_shot_file)
                else:
                    pass                    

                if not os.path.isfile(render_shot_file):
                    shutil.copyfile(empty_maya_file, render_shot_file)      
                else:
                    pass                    
                    
                if not os.path.isfile(geo_shot_file):
                    shutil.copyfile(empty_maya_file, geo_shot_file)
                else:
                    pass                    

                if not os.path.isfile(anim_shot_file):
                    shutil.copyfile(empty_maya_file, anim_shot_file)
                else:
                    pass                    


    def get_char_design_dir(self):
        '''
        - return a paths for character design directory
        '''
        return self.project_directory + '/assets/2D_DESIGN/CHARACTER/'


    def get_props_design_dir(self):
        '''
        - return a paths for props design directory
        '''
        return self.project_directory + '/assets/2D_DESIGN/PROPS/'



    def get_com_design_dir(self):
        '''
        - return a paths for component design directory
        '''
        return self.project_directory + '/assets/2D_DESIGN/COMPONENT/'


    def get_env_design_dir(self):
        '''
        - return a paths for environment design directory
        '''
        return self.project_directory + '/assets/2D_DESIGN/ENVIRONMENT/'


    def get_2d_continuities_dir(self):
        '''
        - return a paths for 2D continuities directory
        '''
        return self.project_directory + '/assets/2D_DESIGN/CONTINUITY/'                


    def make_char_design_folder(self, char_name):
        '''
        - create a character folder in 2D design 
        '''
        parent_dir = self.get_char_design_dir() 
        make_folders(parent_dir,char_name)
        self.add_hidden_folders(unix_format(parent_dir) + char_name) 


    def make_props_design_folder(self, props_name):
        '''
        - create a props folder in 2D design 
        '''
        parent_dir = self.get_props_design_dir() 
        make_folders(parent_dir,props_name) 
        self.add_hidden_folders(unix_format(parent_dir) + props_name) 


    def make_environment_design_folder(self, environment_name):
        '''
        - create a environment folder in 2D design 
        '''
        parent_dir = self.get_env_design_dir() 
        make_folders(parent_dir,environment_name)  
        self.add_hidden_folders(unix_format(parent_dir) + environment_name) 


    def make_continuities_folder(self, folder_name):
        '''
        - create a 2D continuities folder in 2D design 
        '''
        parent_dir = self.get_2d_continuities_dir() 
        make_folders(parent_dir,folder_name)   
        self.add_hidden_folders(unix_format(parent_dir) + folder_name)


    def add_hidden_folders(self, parent_directory):
        '''
        - this function adds the hidden '___backup' and '___script' folders to those newly created asset folder or shot folder
        '''
        backup_dir = unix_format(parent_directory) + '___backup'
        script_dir = unix_format(parent_directory) + '___script'
        try:
            os.mkdir(backup_dir)
            os.mkdir(script_dir)
        except WindowsError:
            pass
        if os.path.isdir(backup_dir):
            ctypes.windll.kernel32.SetFileAttributesW(unicode(backup_dir), 2)
        if os.path.isdir(script_dir):
            ctypes.windll.kernel32.SetFileAttributesW(unicode(script_dir), 2)   


    def make_init_maya_file(self, file_type, object_name):
        '''
        - this function copies the 'empty.ma' file from current_python_file_directory to the destination directory and rename it 
        - dst_dir_filename should be a string like: x:\dst_dir\object_name.ma
        - object_name could refer to the actual name of the asset, such as character name, props name... etc. 
        '''
        src_dir_filename = current_python_file_directory + '/empty.ma'                    

        # the initial geo file name would be something like: geo_hi_char_charname.ma
        dst_dir_filename = eval(self.maya_asset_directories_dict.get(file_type)) + object_name + '/{}_{}.ma'.format(file_type, str(remove_double_under_scores(object_name)))
        
        shutil.copyfile(src_dir_filename, dst_dir_filename)

        return dst_dir_filename


    def make_init_maya_file_with_references(self, object_name, src_file_type, dst_file_type):
        '''
        - this function copies the 'empty.ma' file from current current_python_file_directory to the destination directory,
        - it then reference the corresponding maya file into the newly created maya file
        - object_name could refer to the actual name of the asset, such as character name, props name... etc. 
        '''
        src_file = eval(self.maya_asset_directories_dict.get(src_file_type)) + object_name + '/{}_{}.ma'.format(src_file_type, str(remove_double_under_scores(object_name)))
        dst_file = self.make_init_maya_file(dst_file_type, object_name)
        
        add_maya_reference_file_mel(src_file, dst_file)

        return dst_file



class Maya_Project_Edit(Maya_Project):
    """
    - Edit projects that created by class Maya_Project()
    - can dynamtically add new scene-shot folders for all the shot-based directories
    """
    def __init__(self, drive, project_name):        
        self.project_name = project_name
        self.project_directory = unix_format(drive + self.project_name)   
        # override the original 'self.dict_amount'    
        self.dict_amount = self.get_current_scene_shot_dict()
        # pass the newly overrided 'self.dict_amount' attribute to the parent class's '__init__'
        Maya_Project.__init__(self, project_name, self.dict_amount)
        #self.get_directories_for_shots_attr = self.get_directories_for_shots()
        #self.get_directories_for_assets_attr = self.get_directories_for_assets()
               

    def get_current_scene_shot_dict(self, *get_dict): 
        if get_dict:
            self.shot_dirs = self.get_directories_for_shots()
            if self.shot_dirs == []: 
                return None
            else:
                # any path that inside the shot_dirs should help the calculation of scene-shots 
                # so just use the first path for calculation 
                dir = self.shot_dirs[0] 
                # collect the scene numbers 
                self.scenes = os.listdir(dir)   
                self.scene_shot_dict = {}
                
                try: 
                    for current_scene in self.scenes:
                        num = current_scene.split('_')[-1]
                        
                        # collect shot amounts from current scene                    
                        try:      
                            amounts = []
                            for current_shot in os.listdir(dir + current_scene):     
                                # current_shot is the exact shot folder "__Shot_#"
                                # extract the end digits from the folder name 

                                shot = current_shot.split('_')[-1]        

                                # collect above digitl into a list 
                                amounts.append(int(shot))
                            # sort the elements inside the "amount" list 
                            amounts.sort() 
                            # the last element of the list should be the exact number of amount 
                            self.scene_shot_dict[int(num)] = int(amounts[-1])
                        except IndexError:
                            pass 
                    return self.scene_shot_dict         
                except IndexError:
                    pass 
        else:
            return {}



# ========================================
# ======= the implementation of UI =======
# ========================================

class main_gui(MayaQWidgetDockableMixin, QWidget):
    
    def __init__(self, parent = None):
        super(main_gui, self).__init__(parent)

        self.setParent(mayaMainWindow)

        self.main_layout = QVBoxLayout()
        
        self.main_stacked_widget = QWidget()
        self.main_stacked_widget.setFixedHeight(777)
        self.main_stacked_layout = QStackedLayout(self.main_stacked_widget)   

        self.project_widget= QWidget()
        self.project_widget.setFixedHeight(37)
        self.project_widget.setFixedWidth(1000)        
        
        # create widget for buttons
        self.category_buttons_widgets = QWidget()
        self.category_buttons_layout = QHBoxLayout(self.category_buttons_widgets)   
        self.category_buttons_widgets.setFixedHeight(50)

        self.design_section_button = QPushButton('2D DRAWINGS')
        self.design_widget = QTabWidget()
        self.design_widget.setFixedHeight(770)
        
        self.asset_section_button = QPushButton('3D ASSETS')
        self.asset_widget = QTabWidget()
        self.asset_widget.setFixedHeight(770)
        #self.asset_main_layout = QVBoxLayout(self.asset_widget)
        
        self.shot_section_button= QPushButton('SHOTS')
        self.shot_widget = QWidget()
        self.shot_widget.setFixedHeight(770)
        
        self.top_buttons = [self.design_section_button, self.asset_section_button, self.shot_section_button]
                
        self.design_section_button.clicked.connect(lambda: self.main_stacked_layout.setCurrentIndex(0))
        self.design_section_button.clicked.connect(lambda: self.refresh_current_ui())
        self.design_section_button.clicked.connect(lambda: self.button_text_fx(self.design_section_button, self.top_buttons))
        self.design_section_button.clicked.connect(lambda: self.button_down_fx(self.design_section_button, self.top_buttons))
          
        self.asset_section_button.clicked.connect(lambda: self.main_stacked_layout.setCurrentIndex(1))
        self.asset_section_button.clicked.connect(lambda: self.refresh_current_ui())
        self.asset_section_button.clicked.connect(lambda: self.button_text_fx(self.asset_section_button, self.top_buttons))        
        self.asset_section_button.clicked.connect(lambda: self.button_down_fx(self.asset_section_button, self.top_buttons))

        self.shot_section_button.clicked.connect(lambda: self.main_stacked_layout.setCurrentIndex(2))
        self.shot_section_button.clicked.connect(lambda: self.refresh_current_ui())
        self.shot_section_button.clicked.connect(lambda: self.button_text_fx(self.shot_section_button, self.top_buttons))          
        self.shot_section_button.clicked.connect(lambda: self.button_down_fx(self.shot_section_button, self.top_buttons))

        self.category_buttons_layout.addWidget(self.design_section_button)
        self.category_buttons_layout.addWidget(self.asset_section_button)
        self.category_buttons_layout.addWidget(self.shot_section_button)
        
        self.main_layout.addWidget(self.project_widget)
        self.main_layout.addWidget(self.category_buttons_widgets)        
        self.main_layout.addWidget(self.main_stacked_widget)
        
        self.main_stacked_layout.addWidget(self.design_widget)
        self.main_stacked_layout.addWidget(self.asset_widget)
        self.main_stacked_layout.addWidget(self.shot_widget)
        
        self.asset_section_button.setFlat(True) 
        self.asset_section_button.setText('[ ' + self.asset_section_button.text() + ' ]')
        self.main_stacked_layout.setCurrentIndex(1)
        
        self.main_layout.setAlignment(Qt.AlignCenter)
        
        # create elements for the "PROJECT" section
        self.project_layout = QHBoxLayout(self.project_widget) 
        
        #project section
        self.project_name_line_edit = QLineEdit()
        self.project_name_line_edit.setFixedWidth(170) 
        self.project_name_line_edit.setFixedHeight(24) 
        self.project_name_line_edit.setPlaceholderText('Please type project name here...')                        
        self.project_name_line_edit.returnPressed.connect(lambda: self.select_texts(self.project_name_line_edit))

        self.select_drive_combo_box = QComboBox()
        self.select_drive_combo_box.setFixedWidth(47)       

        # clear and populate drive letters into the combox
        self.select_drive_combo_box.clear()
        self.drive_list = get_drives_letters()
        self.select_drive_combo_box.addItems(self.drive_list)        
        
        self.create_project_button = QPushButton('Create Project')
        self.create_project_button.setFixedWidth(170)  
        self.create_project_button.setFixedHeight(24) 
        self.create_project_button.clicked.connect(lambda: self.create_project())
        self.create_project_button.clicked.connect(lambda: self.project_name_line_edit.clear())      

        self.set_project_button = QPushButton('Set Project')
        self.set_project_button.setFixedWidth(170)
        self.set_project_button.setFixedHeight(24)
        self.set_project_button.clicked.connect(lambda: self.set_project())

        self.refresh_button = QPushButton('REFRESH')
        self.refresh_button.setFixedWidth(170)
        self.refresh_button.setFixedHeight(24)
        self.refresh_button.clicked.connect(lambda: self.eval_get_current_project())
        self.refresh_button.clicked.connect(lambda: self.refresh_current_ui())

        self.current_project_label = QLabel('Current Project: ')

        self.project_layout.addWidget(self.select_drive_combo_box)
        self.project_layout.addWidget(self.project_name_line_edit)
        self.project_layout.addWidget(self.create_project_button)
        self.project_layout.addWidget(self.set_project_button)        
        self.project_layout.addWidget(self.refresh_button)       
        self.project_layout.addWidget(self.current_project_label)       
        
        # container that holds the UI widgets in "create_shot_tab"
        self.create_shot_tab_widgets = {}
 
        # container that holds the UI widgets in "create_design_tab"        
        self.create_design_tab_widgets = {}

        # container that holds the UI widgets in "create_asset_tab"        
        self.create_asset_tab_widgets = {}        
 
        
        self.folder_type_directories_dict = {   'CHARACTER':                    'self.current_project.get_char_design_dir()',
                                                'PROPS':                        'self.current_project.get_props_design_dir()',
                                                'COMPONENT':                    'self.current_project.get_com_design_dir()',
                                                'ENVIRONMENT':                  'self.current_project.get_env_design_dir()',
                                                'CONTINUITY':                   'self.current_project.get_2d_continuities_dir()',

                                                'Model':                        'self.current_project.get_geo_shot_dir()',
                                                'Layout':                       'self.current_project.get_layout_shot_dir()',
                                                'Layout_MOV':                   'self.current_project.get_layout_playblast_dir()',
                                                'Animation':                    'self.current_project.get_anim_shot_dir()',
                                                'Animation_MOV':                'self.current_project.get_anim_playblast_dir()',
                                                'Anim_Cache':                   'self.current_project.get_anim_cache_shot_dir()',
                                                'Lighting':                     'self.current_project.get_lighting_shot_dir()',
                                                'VFX':                          'self.current_project.get_vfx_shot_dir()',
                                                'VFX_Cache':                    'self.current_project.get_vfx_cache_shot_dir()',
                                                'Rendering':                    'self.current_project.get_rendering_shot_dir()',

                                                'CHARACTER_SHADER':             'self.current_project.get_char_shader_dir()', 
                                                'COMPONENT_SHADER':             'self.current_project.get_env_shader_dir()', 
                                                'PROPS_SHADER':                 'self.current_project.get_props_shader_dir()', 
                                                'PROPS_TEXTURE':                'self.current_project.get_props_texture_dir()', 
                                                'COMPONENT_TEXTURE':            'self.current_project.get_env_texture_dir()', 
                                                'CHARACTER_TEXTURE':            'self.current_project.get_char_texture_dir()',
                                                'HIGH-RESOLUTION_CHARACTER':    'self.current_project.get_char_hiGeo_dir()', 
                                                'HIGH-RESOLUTION_COMPONENT':    'self.current_project.get_com_hiGeo_dir()', 
                                                'HIGH-RESOLUTION_ENVIRONMENT':  'self.current_project.get_env_hiGeo_dir()', 
                                                'HIGH-RESOLUTION_PROPS':        'self.current_project.get_props_hiGeo_dir()', 
                                                'LOW-RESOLUTION_CHARACTER':     'self.current_project.get_char_lowGeo_dir()', 
                                                'LOW-RESOLUTION_COMPONENT':     'self.current_project.get_com_lowGeo_dir()', 
                                                'LOW-RESOLUTION_ENVIRONMENT':   'self.current_project.get_env_lowGeo_dir()', 
                                                'LOW-RESOLUTION_PROPS':         'self.current_project.get_props_lowGeo_dir()',             
                                                'RIGGED_CHARACTER':             'self.current_project.get_char_rig_dir()', 
                                                'RIGGED_PROPS':                 'self.current_project.get_props_rig_dir()', 
                                                'DEFORMED_CHARACTER':           'self.current_project.get_char_def_dir()', 
                                                'DEFORMED_PROPS':               'self.current_project.get_props_def_dir()',  
                                                'TEMPLATE_CHARACTER':           'self.current_project.get_char_light_template_dir()', 
                                                'TEMPLATE_ENVIRONMENT':         'self.current_project.get_env_light_template_dir()',
                                                'TEMPLATE_RENDERING':           'self.current_project.get_render_template_dir()'     } 

        # create elements for DESIGN section 
        self.design_categories = ['CHARACTER', 'PROPS', 'COMPONENT','ENVIRONMENT', 'CONTINUITY']
        
        for single_design_tab in self.design_categories:
            design_type = single_design_tab
            treeView1 = single_design_tab + '_treeView1'
            model1 = single_design_tab + '_model1'
            treeView2 = single_design_tab + '_treeView2'
            model2 = single_design_tab + '_model2'
            button2 = single_design_tab + '_button2'            
            self.create_design_tab(design_type, self.design_widget, treeView1, model1, treeView2, model2, button2)            

        self.create_design_tab_widgets['CHARACTER_treeView2']    .doubleClicked.connect  (lambda: self.open_file_in_design_tabs('Character_Design'))
        self.create_design_tab_widgets['PROPS_treeView2']        .doubleClicked.connect  (lambda: self.open_file_in_design_tabs('Props_Design'))
        self.create_design_tab_widgets['ENVIRONMENT_treeView2']  .doubleClicked.connect  (lambda: self.open_file_in_design_tabs('Environment_Design'))
        self.create_design_tab_widgets['CONTINUITY_treeView2']     .doubleClicked.connect  (lambda: self.open_file_in_design_tabs('2D_Continuities'))                    

        self.create_design_tab_widgets['CHARACTER_button2']      .clicked.connect        (lambda: self.open_file_in_explorer_design_tabs('Character_Design'))
        self.create_design_tab_widgets['PROPS_button2']          .clicked.connect        (lambda: self.open_file_in_explorer_design_tabs('Props_Design'))
        self.create_design_tab_widgets['ENVIRONMENT_button2']    .clicked.connect        (lambda: self.open_file_in_explorer_design_tabs('Environment_Design'))
        self.create_design_tab_widgets['CONTINUITY_button2']       .clicked.connect        (lambda: self.open_file_in_explorer_design_tabs('2D_Continuities'))

        #self.refresh_tabwidget(self.design_widget)

        # create elements for ASSET section
        self.shot_categories = ['CHARACTER', 'COMPONENT', 'ENVIRONMENT', 'PROPS', 'TEMPLATE']
        
        for single_shot_tab in self.shot_categories:            
            treeView1   = single_shot_tab + '_treeView1'
            model1      = single_shot_tab + '_model1'
            treeView2   = single_shot_tab + '_treeView2'
            model2      = single_shot_tab + '_model2'
            treeView3   = single_shot_tab + '_treeView3'
            model3      = single_shot_tab + '_model3'            
            line_edit1  = single_shot_tab + '_line_edit1'
            line_edit2  = single_shot_tab + '_line_edit2'
            button1     = single_shot_tab + '_button1'
            button2     = single_shot_tab + '_button2'
            button3     = single_shot_tab + '_button3'
            button4     = single_shot_tab + '_button4'
            button5     = single_shot_tab + '_button5'            
            self.create_asset_tab(single_shot_tab, self.asset_widget, treeView1, model1, treeView2, model2, treeView3, model3, line_edit1, line_edit2, button1, button2, button3, button4, button5)            
        
        #self.refresh_tabwidget(self.asset_widget)

        # create elements for SHOT section
        self.create_shot_tab(self.shot_widget, treeView1, model1, treeView2, model2, treeView3, model3, line_edit1, line_edit2, button1, button2, button3, button4, button5)

        # set the miscellaneous attributes
        self.setFixedHeight(900)
        self.setFixedWidth(1070)
        self.setMinimumSize(1070,900)
        self.setMaximumSize(1070,900)

        self.setLayout(self.main_layout)

        self.setWindowFlags(Qt.Dialog)
        self.setWindowTitle('PROJECT FILE MANAGER')
        
        self.refresh_design_tabs_dict = { 0:        'self.populate_items_in_focused_tab("CHARACTER", self.create_design_tab_widgets)', 
                                          1:        'self.populate_items_in_focused_tab("PROPS", self.create_design_tab_widgets)',
                                          2:        'self.populate_items_in_focused_tab("COMPONENT", self.create_design_tab_widgets)',
                                          3:        'self.populate_items_in_focused_tab("ENVIRONMENT", self.create_design_tab_widgets)',
                                          4:        'self.populate_items_in_focused_tab("CONTINUITY", self.create_design_tab_widgets)'}        

        self.refresh_shot_tabs_dict = {   0:        'self.populate_items_in_shot_tab("Model")',
                                          1:        'self.populate_items_in_shot_tab("Layout")',
                                          2:        'self.populate_items_in_shot_tab("Layout_MOV")',
                                          3:        'self.populate_items_in_shot_tab("Animation")',
                                          4:        'self.populate_items_in_shot_tab("Animation_MOV")',
                                          5:        'self.populate_items_in_shot_tab("Anim_Cache")',    
                                          6:        'self.populate_items_in_shot_tab("Lighting")',
                                          7:        'self.populate_items_in_shot_tab("VFX")',
                                          8:        'self.populate_items_in_shot_tab("VFX_Cache")',
                                          9:        'self.populate_items_in_shot_tab("Rendering")' }
        
        self.refresh_asset_tabs_dict = {  (0,0):    'self.populate_asset_model_char_tab()',
                                          (0,1):    'self.populate_asset_model_component_tab()',
                                          (0,2):    'self.populate_asset_model_environment_tab()',
                                          (0,3):    'self.populate_asset_model_props_tab()',
                                          (1,0):    'self.populate_asset_rig_char_tab()',
                                          (1,1):    'self.populate_asset_rig_props_tab()',
                                          (2,0):    'self.populate_asset_shader_tab()',
                                          (2,1):    'self.populate_asset_texture_tab()',
                                          (3,0):    'self.populate_items_in_asset_tab("TEMPLATE_CHARACTER")',
                                          (3,1):    'self.populate_items_in_asset_tab("TEMPLATE_ENVIRONMENT")',
                                          (3,2):    'self.populate_items_in_asset_tab("TEMPLATE_RENDERING")' }

        self.refresh_ui_dict = { 0: 'self.refresh_design_tabs_dict.get(self.get_design_tabs_current_index())',
                                 1: 'self.refresh_asset_tabs_dict.get(self.get_asset_tabs_current_index())' ,
                                 2: ''}        


        self.current_project = None
        

    def eval_get_current_project(self):        
        self.current_project = self.get_current_project()
        return self.current_project



    # ===============================================================
    # ======= implemment the 'template' of the 2D-Drawing Tab =======
    # ===============================================================

    def create_design_tab(self, design_type, parent_tab_widget, treeView1, model1, treeView2, model2, button2):    
        self.design_type_tab = QWidget()
        self.design_type_tab.setFixedHeight(750)
        self.design_type_tab_layout = QHBoxLayout(self.design_type_tab )
        parent_tab_widget.addTab(self.design_type_tab, design_type.upper())
                       
        self.design_type_utilities_widget = QWidget()
        self.design_type_utilities_layout = QFormLayout(self.design_type_utilities_widget)                   
        
        self.design_type_folder_widget = QTreeWidget()
        self.design_type_folder_widget.setFixedHeight(730)
        self.design_type_folder_widget.setFixedWidth(407)    
        self.create_design_tab_widgets[treeView1] = QTreeView(self.design_type_folder_widget)
        self.create_design_tab_widgets[treeView1].setFixedHeight(730)
        self.create_design_tab_widgets[treeView1].setFixedWidth(407)   
        self.create_design_tab_widgets[treeView1].setSelectionBehavior(QAbstractItemView.SelectRows)
        self.create_design_tab_widgets[treeView1].setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.create_design_tab_widgets[model1] = QStandardItemModel()
        self.create_design_tab_widgets[model1].setHorizontalHeaderLabels(['>>> {} <<<'.format(design_type).upper()])  
        self.create_design_tab_widgets[treeView1].setModel(self.create_design_tab_widgets[model1])    
        #self.create_design_tab_widgets[treeView1].doubleClicked.connect(lambda: self.refresh_current_ui())
        #self.create_design_tab_widgets[treeView1].doubleClicked.connect(lambda: self.populate_items_in_design_tabs())
        
        self.design_type_file_widget = QTreeWidget()
        self.design_type_file_widget.setFixedHeight(730)
        self.design_type_file_widget.setFixedWidth(407)    
        self.create_design_tab_widgets[treeView2] = QTreeView(self.design_type_file_widget)
        self.create_design_tab_widgets[treeView2].setFixedHeight(730)
        self.create_design_tab_widgets[treeView2].setFixedWidth(407)   
        self.create_design_tab_widgets[treeView2].setSelectionBehavior(QAbstractItemView.SelectRows)
        self.create_design_tab_widgets[treeView2].setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.create_design_tab_widgets[model2] = QStandardItemModel()
        self.create_design_tab_widgets[model2].setHorizontalHeaderLabels(['>>> FILE <<<'.upper()])   
        self.create_design_tab_widgets[treeView2].setModel(self.create_design_tab_widgets[model2])            

        self.create_design_tab_widgets[button2] = QPushButton('Open in File Explorer')
        self.create_design_tab_widgets[button2].setMinimumWidth(177)
        self.create_design_tab_widgets[button2].setMaximumWidth(177)       
        
        self.design_type_tab_layout.addWidget(self.design_type_folder_widget )
        self.design_type_tab_layout.addWidget(self.design_type_file_widget )
    
        self.design_type_utilities_layout.addWidget(self.create_design_tab_widgets[button2])   

        self.design_type_tab_layout.addWidget(self.design_type_utilities_widget )  


    # ===============================================================
    # ======= implemment the 'template' of the 3D-Asset Tab =========
    # ===============================================================
    def create_asset_tab(self, asset_type, parent_tab_widget, treeView1, model1, treeView2, model2, treeView3, model3, line_edit1, line_edit2, button1, button2, button3, button4, button5):    
        self.asset_type_tab = QWidget()
        self.asset_type_tab.setFixedHeight(750)
        self.asset_type_tab_layout = QHBoxLayout(self.asset_type_tab )
        parent_tab_widget.addTab(self.asset_type_tab, asset_type.upper())
                       
        self.asset_type_utilities_widget = QWidget()
        self.asset_type_utilities_layout = QFormLayout(self.asset_type_utilities_widget)

        self.asset_type_folder_widget = QTreeWidget()
        self.asset_type_folder_widget.setFixedHeight(730)
        self.asset_type_folder_widget.setFixedWidth(277)    
        self.create_asset_tab_widgets[treeView1] = QTreeView(self.asset_type_folder_widget)
        self.create_asset_tab_widgets[treeView1].setFixedHeight(730)
        self.create_asset_tab_widgets[treeView1].setFixedWidth(277)   
        self.create_asset_tab_widgets[treeView1].setSelectionBehavior(QAbstractItemView.SelectRows)
        self.create_asset_tab_widgets[treeView1].setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.create_asset_tab_widgets[model1] = QStandardItemModel()
        self.create_asset_tab_widgets[model1].setHorizontalHeaderLabels(['>>> {} <<<'.format(asset_type).upper()])   
        self.create_asset_tab_widgets[treeView1].setModel(self.create_asset_tab_widgets[model1])  

        self.asset_type_file_widget = QTreeWidget()
        self.asset_type_file_widget.setFixedHeight(730)
        self.asset_type_file_widget.setFixedWidth(277)    
        self.create_asset_tab_widgets[treeView2] = QTreeView(self.asset_type_file_widget)
        self.create_asset_tab_widgets[treeView2].setFixedHeight(730)
        self.create_asset_tab_widgets[treeView2].setFixedWidth(277)   
        self.create_asset_tab_widgets[treeView2].setSelectionBehavior(QAbstractItemView.SelectRows)
        self.create_asset_tab_widgets[treeView2].setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.create_asset_tab_widgets[model2] = QStandardItemModel()
        self.create_asset_tab_widgets[model2].setHorizontalHeaderLabels(['>>> File <<<'.upper()])   
        self.create_asset_tab_widgets[treeView2].setModel(self.create_asset_tab_widgets[model2])   

        self.asset_type_history_file_widget = QTreeWidget()
        self.asset_type_history_file_widget.setFixedHeight(730)
        self.asset_type_history_file_widget.setFixedWidth(277)    
        self.create_asset_tab_widgets[treeView3] = QTreeView(self.asset_type_history_file_widget)
        self.create_asset_tab_widgets[treeView3].setFixedHeight(730)
        self.create_asset_tab_widgets[treeView3].setFixedWidth(277)   
        self.create_asset_tab_widgets[treeView3].setSelectionBehavior(QAbstractItemView.SelectRows)
        self.create_asset_tab_widgets[treeView3].setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.create_asset_tab_widgets[model3] = QStandardItemModel()
        self.create_asset_tab_widgets[model3].setHorizontalHeaderLabels(['>>> HISTORY <<<'.upper()])   
        self.create_asset_tab_widgets[treeView3].setModel(self.create_asset_tab_widgets[model3])
        
        self.create_asset_tab_widgets[button2] = QPushButton('Open')
        self.create_asset_tab_widgets[button2].setFixedWidth(170)
             
        self.create_asset_tab_widgets[button3] = QPushButton('Reference')
        self.create_asset_tab_widgets[button3].setFixedWidth(170)

        self.create_asset_tab_widgets[button4] = QPushButton('Create New Variation')
        self.create_asset_tab_widgets[button4].setFixedWidth(170)
        self.create_asset_tab_widgets[button4].setEnabled(False)
             
        self.create_asset_tab_widgets[button5] = QPushButton('Set Active')
        self.create_asset_tab_widgets[button5].setFixedWidth(170)   
        self.create_asset_tab_widgets[button5].setEnabled(False)     
                 
        self.asset_type_tab_layout.addWidget(self.asset_type_folder_widget )
        self.asset_type_tab_layout.addWidget(self.asset_type_file_widget)
        self.asset_type_tab_layout.addWidget(self.asset_type_history_file_widget)        
              
        self.asset_type_utilities_layout.addWidget(self.create_asset_tab_widgets[button2])   
        self.asset_type_utilities_layout.addWidget(self.create_asset_tab_widgets[button3]) 
        self.asset_type_utilities_layout.addWidget(self.create_asset_tab_widgets[button4])   
        self.asset_type_utilities_layout.addWidget(self.create_asset_tab_widgets[button5]) 

        self.asset_type_tab_layout.addWidget(self.asset_type_utilities_widget )         


    # ==========================================================
    # ======= implemment the 'template' of the Shots Tab =======    
    # ==========================================================

    def create_shot_tab(self, parent_tab_widget, treeView1, model1, treeView2, model2, treeView3, model3, line_edit1, line_edit2, button1, button2, button3, button4, button5):    
        parent_tab_widget.setFixedHeight(770)
        self.shot_type_tab_layout = QHBoxLayout(parent_tab_widget)
                       
        self.shot_type_utilities_widget = QWidget()
        self.shot_type_utilities_layout = QFormLayout(self.shot_type_utilities_widget)

        self.shot_type_folder_widget = QTreeWidget()
        self.shot_type_folder_widget.setFixedHeight(730)
        self.shot_type_folder_widget.setFixedWidth(277)    
        self.create_shot_tab_widgets[treeView1] = QTreeView(self.shot_type_folder_widget)
        self.create_shot_tab_widgets[treeView1].setFixedHeight(730)
        self.create_shot_tab_widgets[treeView1].setFixedWidth(277)   
        self.create_shot_tab_widgets[treeView1].setSelectionBehavior(QAbstractItemView.SelectRows)
        self.create_shot_tab_widgets[treeView1].setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.create_shot_tab_widgets[model1] = QStandardItemModel()
        self.create_shot_tab_widgets[model1].setHorizontalHeaderLabels(['>>> Folder <<<'.upper()])   
        self.create_shot_tab_widgets[treeView1].setModel(self.create_shot_tab_widgets[model1])  

        self.shot_type_file_widget = QTreeWidget()
        self.shot_type_file_widget.setFixedHeight(730)
        self.shot_type_file_widget.setFixedWidth(277)    
        self.create_shot_tab_widgets[treeView2] = QTreeView(self.shot_type_file_widget)
        self.create_shot_tab_widgets[treeView2].setFixedHeight(730)
        self.create_shot_tab_widgets[treeView2].setFixedWidth(277)   
        self.create_shot_tab_widgets[treeView2].setSelectionBehavior(QAbstractItemView.SelectRows)
        self.create_shot_tab_widgets[treeView2].setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.create_shot_tab_widgets[model2] = QStandardItemModel()
        self.create_shot_tab_widgets[model2].setHorizontalHeaderLabels(['>>> File <<<'.upper()])   
        self.create_shot_tab_widgets[treeView2].setModel(self.create_shot_tab_widgets[model2])   

        self.shot_type_history_file_widget = QTreeWidget()
        self.shot_type_history_file_widget.setFixedHeight(730)
        self.shot_type_history_file_widget.setFixedWidth(277)    
        self.create_shot_tab_widgets[treeView3] = QTreeView(self.shot_type_history_file_widget)
        self.create_shot_tab_widgets[treeView3].setFixedHeight(730)
        self.create_shot_tab_widgets[treeView3].setFixedWidth(277)   
        self.create_shot_tab_widgets[treeView3].setSelectionBehavior(QAbstractItemView.SelectRows)
        self.create_shot_tab_widgets[treeView3].setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.create_shot_tab_widgets[model3] = QStandardItemModel()
        self.create_shot_tab_widgets[model3].setHorizontalHeaderLabels(['>>> HISTORY <<<'.upper()])   
        self.create_shot_tab_widgets[treeView3].setModel(self.create_shot_tab_widgets[model3])

        self.create_shot_tab_widgets[line_edit1] = QLineEdit()
        self.create_shot_tab_widgets[line_edit1].setFixedWidth(170) 
        self.create_shot_tab_widgets[line_edit1].setPlaceholderText('Scene numbers....')  
        self.create_shot_tab_widgets[line_edit1].returnPressed.connect(lambda: self.select_texts(self.create_shot_tab_widgets[line_edit1] ))

        self.create_shot_tab_widgets[line_edit2] = QLineEdit()
        self.create_shot_tab_widgets[line_edit2].setFixedWidth(170)
        self.create_shot_tab_widgets[line_edit2].setPlaceholderText('Shot amounts...')   
        self.create_shot_tab_widgets[line_edit2].returnPressed.connect(lambda: self.select_texts(self.create_shot_tab_widgets[line_edit2] ))
        
        self.create_shot_tab_widgets[button1] = QPushButton('Generate Scene-Shot Folders')
        self.create_shot_tab_widgets[button1].setFixedWidth(170)    
        self.create_shot_tab_widgets[button1].clicked.connect(lambda: self.generate_new_scene_shot_folders())
        self.create_shot_tab_widgets[button1].clicked.connect(lambda: self.refresh_current_ui())
        self.create_shot_tab_widgets[button1].clicked.connect(lambda: self.create_shot_tab_widgets[line_edit1].clear())
        self.create_shot_tab_widgets[button1].clicked.connect(lambda: self.create_shot_tab_widgets[line_edit2].clear())
        
        self.create_shot_tab_widgets[button2] = QPushButton('Open')
        self.create_shot_tab_widgets[button2].setFixedWidth(170)
             
        self.create_shot_tab_widgets[button3] = QPushButton('Reference')
        self.create_shot_tab_widgets[button3].setFixedWidth(170)

        self.create_shot_tab_widgets[button4] = QPushButton('Create New Variation')
        self.create_shot_tab_widgets[button4].setFixedWidth(170)
        self.create_shot_tab_widgets[button4].setEnabled(False)
             
        self.create_shot_tab_widgets[button5] = QPushButton('Set Active')
        self.create_shot_tab_widgets[button5].setFixedWidth(170)   
        self.create_shot_tab_widgets[button5].setEnabled(False)     
                 
        self.shot_type_tab_layout.addWidget(self.shot_type_folder_widget )
        self.shot_type_tab_layout.addWidget(self.shot_type_file_widget)
        self.shot_type_tab_layout.addWidget(self.shot_type_history_file_widget)        
        
        self.shot_type_utilities_layout.addWidget(self.create_shot_tab_widgets[line_edit1] )
        self.shot_type_utilities_layout.addWidget(self.create_shot_tab_widgets[line_edit2] )
        self.shot_type_utilities_layout.addWidget(self.create_shot_tab_widgets[button1])        
        self.shot_type_utilities_layout.addWidget(self.create_shot_tab_widgets[button2])   
        self.shot_type_utilities_layout.addWidget(self.create_shot_tab_widgets[button3]) 
        self.shot_type_utilities_layout.addWidget(self.create_shot_tab_widgets[button4])   
        self.shot_type_utilities_layout.addWidget(self.create_shot_tab_widgets[button5]) 

        self.shot_type_tab_layout.addWidget(self.shot_type_utilities_widget )         
     
 
    # ======================================================
    # ======= some back-end functions for UI widgets =======
    # ======================================================        
    def button_down_fx(self, current_button, buttons):

        current_button.setFlat(True)    

        for button in buttons:
            if button != current_button:  
                button.setFlat(False)


    def button_text_fx(self, current_button, buttons):        

        current_button.setText('[ ' + current_button.text() + ' ]')  


        for button in buttons:
            text = button.text().split('[ ')[-1].split(' ]')[0]
            
            if button != current_button:
                button.setText(text)
                button.setDefault(False)

            else:
                button.setText('[ ' + text + ' ]')  
                button.setDefault(True)

        
    def select_texts(self, line_edit):
        line_edit.selectAll()
        
    
    def create_project(self):
        project_name = self.project_name_line_edit.text()
        if project_name == '':     
            return
        else:
            project = Maya_Project(project_name, {1:1})
            self.current_project_label.setText('Current Project: [ {} ]'.format(project.project_directory))
            return project       


    def set_project(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.Directory)
        file_dialog.setOption(QFileDialog.ShowDirsOnly)
        #file_dialog.exec_()
        selected_directory = file_dialog.getExistingDirectory()
        # verify the selected directory is a maya project folder or not
        if os.path.isfile(selected_directory + '/workspace.mel'):
            print selected_directory
            self.current_project_label.setText('Current Project: [ {} ]'.format(selected_directory))
        else:
            return

    def get_current_project(self):
        self.current_project = None
        drive = self.select_drive_combo_box.currentText() 
        project_name = self.current_project_combo_box.currentText()
        
        if project_name != '':
            return Maya_Project_Edit(drive, project_name)     
        else:
            return None
        
        
    def update_scene_shot_dict(self):
        #current_project = self.get_current_project()
        new_scene_shot_dict = {}
        if self.current_project != None:

            current_scene_shot_dict = self.current_project.get_current_scene_shot_dict(True)      
            
            try:        
                for single_shot_tab in self.shot_categories:     
                
                    treeView1   = single_shot_tab + '_treeView1'
                    model1      = single_shot_tab + '_model1'
                    treeView2   = single_shot_tab + '_treeView2'
                    model2      = single_shot_tab + '_model2'
                    line_edit1  = single_shot_tab + '_line_edit1'
                    line_edit2  = single_shot_tab + '_line_edit2'
                    button1     = single_shot_tab + '_button1'
                    button2     = single_shot_tab + '_button2'
                    button3     = single_shot_tab + '_button3'     
                    
                    new_scenes = convert_digit_strings_to_int_list(self.create_shot_tab_widgets[line_edit1].text())
                    new_shots = convert_digit_strings_to_int_list(self.create_shot_tab_widgets[line_edit2].text())
                
                    if new_scenes != None and new_shots != None:
                        for new_scn, new_shot in zip(new_scenes, new_shots):
                            new_scene_shot_dict = update_shot_dict(current_scene_shot_dict, new_scn, new_shot)    
                                    
                    else:
                        continue   
                
                return new_scene_shot_dict
           
            except TypeError, ValueError:
                pass
        else:
            return None


    def generate_new_scene_shot_folders(self):
        #current_project = self.get_current_project()
        new_scene_shot_dict = self.update_scene_shot_dict()

        try:            
            self.current_project.add_scene_shot_folders(new_scene_shot_dict)
            self.current_project.dict_amount = new_scene_shot_dict

        except AttributeError:
            pass 


    def clear_non_focus_qtreeview_selection(self, current_folder_type, widget_dict, treeview_num):
        '''
        - this function clears the selection for those qtreeviews, which are not clicked by mouse cursor
        - treeview_num is an int type, which is the exact number of '_treeView#', usually should pass 1 or 2 in this app
        '''
        

        for folder_type in self.folder_type_directories_dict.keys():
            if folder_type != current_folder_type:
                treeView = folder_type + '_treeView' + str(treeview_num)
                try:
                    widget_dict[treeView].clearSelection()
                except KeyError:
                    pass


    def populate_folders_into_qtreeview(self, folder_type, widget_dict, parent_directory):

        treeView1 = folder_type + '_treeView1'
        model1 = folder_type + '_model1'

        try:
            widget_dict[model1].clear()
            widget_dict[model1].setHorizontalHeaderLabels(['>>> {} <<<'.format(folder_type).upper()])  

            if os.path.isdir(parent_directory):
                for folder in os.listdir(parent_directory):

                    item = QStandardItem(remove_double_under_scores(folder))

                    item.setIcon(widget_dict[treeView1].style().standardIcon(QStyle.SP_DirIcon))
                    item.setEditable(False)
                    if os.path.isdir(parent_directory + folder):
                        widget_dict[model1].appendRow([item])                                           

            widget_dict[treeView1].clicked.connect(lambda: self.populate_files_into_qtreeview(folder_type, widget_dict, parent_directory))

            
        except UnboundLocalError, WindowsError:
            pass                                                            


    def populate_hierarchical_folders_into_qtreeview(self, folder_type, widget_dict, parent_directory):
        
        treeView1 = folder_type + '_treeView1'
        model1 = folder_type + '_model1'

        try:            
            widget_dict[model1].clear()                    
            widget_dict[model1].setHorizontalHeaderLabels(['>>> {} <<<'.format(folder_type).upper()])  
            
            try:
                if os.path.isdir(parent_directory):
                    
                    for folder in os.listdir(parent_directory):
                       
                        
                        item = QStandardItem(remove_double_under_scores(folder))
                  
                        item.setIcon(widget_dict[treeView1].style().standardIcon(QStyle.SP_DirIcon))
                     
                        item.setEditable(False)
                   
                        sub_dir = unix_format(os.path.join(parent_directory, folder))
                   
                        if os.path.isdir(sub_dir):
                            
                            sub_folders = os.listdir(sub_dir)
                        
                            for sub_folder in sub_folders: 
                              
                                #  filter out those hidden '___Backup' folders
                                test_dir = unix_format(os.path.join(sub_dir, sub_folder))
                             
                                if os.path.isdir(test_dir) and not(folder_is_hidden(test_dir)):  
                                                                                             
                                    sub_item = QStandardItem(remove_double_under_scores(sub_folder)) 
                                
                                    sub_item.setIcon(widget_dict[treeView1].style().standardIcon(QStyle.SP_DirIcon))
                                    sub_item.setEditable(False)
                             
                                    item.appendRow([sub_item])                        
                              
                        widget_dict[model1].appendRow([item])     
                   
            except TypeError:
                pass                                      
       
            widget_dict[treeView1].clicked.connect(lambda: self.populate_files_into_qtreeview(folder_type, widget_dict, parent_directory))
  
        except UnboundLocalError, WindowsError:
            pass  


    def populate_files_into_qtreeview(self, folder_type, widget_dict, parent_directory):

        treeView2 = folder_type + '_treeView2'
        treeView3 = folder_type + '_treeView3'

        model2 = folder_type + '_model2'
        model3 = folder_type + '_model3'

        # extract the selected folder
        folder_name = self.get_selected_hierarchical_folder(folder_type, widget_dict)
        
        if '/' not in folder_name and 'SCENE_' in folder_name:
            # if '/' not in folder_name means current selected folder is not a child folder
            # and if 'SCENE_' not in folder_name means current selected folder should be an asset folder so it could jump to the 'else' block below.
            
            widget_dict[model2].clear()
            widget_dict[model2].setHorizontalHeaderLabels(['>>> file <<<'.upper()])     
            
            try:
                widget_dict[model3].clear()
                widget_dict[model3].setHorizontalHeaderLabels(['>>> history <<<'.upper()])    
            except KeyError:
                pass        
        else:       
            
            try:
                # populate the active files
                folder_directory = unix_format(parent_directory) + folder_name

                widget_dict[model2].clear()
                widget_dict[model2].setHorizontalHeaderLabels(['>>> file <<<'.upper()])   

                try:
                    widget_dict[model3].clear()
                    widget_dict[model3].setHorizontalHeaderLabels(['>>> history <<<'.upper()])  
                except KeyError:
                    pass                       

                if os.path.isdir(folder_directory):
                    for file in os.listdir(folder_directory):                                            
                        # filter out the hidden folder '___backup'
                        candidate_dir = os.path.join(unix_format(folder_directory), file)

                        if not(os.path.isdir(candidate_dir)):  

                            #self.clear_non_focus_qtreeview_selection(folder_type, widget_dict, 2)  
                            item = QStandardItem(file)                

                            item.setIcon(widget_dict[treeView2].style().standardIcon(QStyle.SP_FileIcon))
                            item.setEditable(False)

                            widget_dict[model2].appendRow([item])
                else:
                    widget_dict[model2].clear()
                    widget_dict[model2].setHorizontalHeaderLabels(['>>> file <<<'.upper()]) 

                    try:
                        widget_dict[model3].clear()
                        widget_dict[model3].setHorizontalHeaderLabels(['>>> history <<<'.upper()])   
                    except KeyError:
                        pass                      

                # populate the history files
                backup_directory = unix_format(parent_directory) + folder_name + '\___backup'
                try:
                    widget_dict[model3].clear()
                    widget_dict[model3].setHorizontalHeaderLabels(['>>> history <<<'.upper()])        
                except KeyError:
                    pass

                if os.path.isdir(backup_directory):
                    for file in os.listdir(backup_directory):
                        # filter out the hidden folder '___script'
                        candidate_dir = os.path.join(unix_format(folder_directory), file)
                        if not(os.path.isdir(candidate_dir)):      
                            try:
                                #self.clear_non_focus_qtreeview_selection(folder_type, widget_dict, 3)                                               
                                item = QStandardItem(file)                            
                                           
                           
                                item.setIcon(widget_dict[treeView3].style().standardIcon(QStyle.SP_FileIcon))
                                item.setEditable(False)

                                widget_dict[model3].appendRow([item])
                            except KeyError:
                                pass
                else:
                    widget_dict[model2].clear()
                    widget_dict[model2].setHorizontalHeaderLabels(['>>> file <<<'.upper()]) 

                    try:
                        widget_dict[model3].clear()
                        widget_dict[model3].setHorizontalHeaderLabels(['>>> history <<<'.upper()])     
                    except KeyError:
                        pass                  

                widget_dict[treeView2].clicked.connect(lambda: self.clear_non_focus_qtreeview_selection(folder_type, widget_dict, 2))    
                #widget_dict[treeView2].clicked.connect(lambda: self.get_selected_file_dir(folder_type, 'maya', widget_dict, parent_directory))
                try:
                    widget_dict[treeView3].clicked.connect(lambda: self.clear_non_focus_qtreeview_selection(folder_type, widget_dict, 3)) 
                    #widget_dict[treeView3].clicked.connect(lambda: self.get_selected_file_dir(folder_type, 'history', widget_dict, parent_directory))
                except KeyError:
                    pass

            except UnboundLocalError, WindowsError:
                pass


    def get_selected_item_index(self, folder_type, widget_dict):
        '''
        returns an int that indicates the exact index of selected folder in the treeview
        '''
        treeView1 = folder_type + '_treeView1'
        model1 = folder_type + '_model1'

        return  widget_dict[treeView1].selectedIndexes()[0].row()


    def get_all_root_item_indexes(self, folder_type, widget_dict):
        '''
        returns a list of indexes of all root level items 
        '''

        treeView1 = folder_type + '_treeView1'
        model1 = folder_type + '_model1'

        all_root_indexes = []

        widget_dict[treeView1].selectAll()

        for sel_item_index in widget_dict[treeView1].selectedIndexes():
            index = sel_item_index.row()
            all_root_indexes.append(index)

        widget_dict[treeView1].clearSelection()

        return all_root_indexes


    def get_parent_item_in_qtreeview(self, folder_type, widget_dict):
        '''
        - returns the parent item text of current selected item
        '''
        treeView1 = folder_type + '_treeView1'

        item = widget_dict[treeView1].selectedIndexes()[0].model().itemFromIndex(widget_dict[treeView1].selectedIndexes()[0])

        try:
            return item.parent().text()      
        except AttributeError:
            return None 


    def get_selected_folders(self, folder_type, widget_dict):
        '''
        returns a list of selected folders in the treeview
        '''

        treeView1 = folder_type + '_treeView1'
        #model1 = folder_type + '_model1'

        texts = []

        for sel_item_index in widget_dict[treeView1].selectedIndexes():
            item = sel_item_index.model().itemFromIndex(sel_item_index).text()
            texts.append(item)

        '''
        for sel_item_index in widget_dict[treeView1].selectedIndexes():
            index = sel_item_index.row()
            sel_indexes.append(index)

        for index in sel_indexes:
            item = widget_dict[model1].item(index)
            texts.append(item.text())
        '''
        return texts

    

    def get_selected_maya_file(self, folder_type, widget_dict):
        '''
        returns a list of selected file in the treeview
        '''
        treeView2 = folder_type + '_treeView2'

        texts = []

        for sel_item_index in widget_dict[treeView2].selectedIndexes():
            item = sel_item_index.model().itemFromIndex(sel_item_index).text()
            texts.append(item)

        return texts[0]


    def get_selected_history_file(self, folder_type, widget_dict):
        '''
        returns a list of selected folders in the treeview
        '''
        treeView3 = folder_type + '_treeView3'
        
        texts = []

        for sel_item_index in widget_dict[treeView3].selectedIndexes():
            item = sel_item_index.model().itemFromIndex(sel_item_index).text()
            texts.append(item)

        return texts[0]       


    def get_selected_file_dir(self, folder_type, file_type, widget_dict, parent_directory):
        '''
        - return a full path of selected file
        - folder_type should be the 'xxx', which is the prefix name of  the 'xxx_treeView2' or 'xxx_treeView3' in the widget_dict
        - widget_dict are those 'self.create_shot_tab_widgets', 'self.create_design_tab_widgets' and 'self.create_asset_tab_widgets'
        - file_type specifies the maya file or history file, only passes '2d', maya' or 'history' for this argument    
        '''
        try:
            selected_file = ''
            selected_folder = self.get_selected_hierarchical_folder(folder_type, widget_dict)

            if file_type == 'maya' or file_type == '2d':

                selected_file += self.get_selected_maya_file(folder_type, widget_dict)

                sel_file_directory = unix_format(parent_directory) + selected_folder + '/' + selected_file
                if os.path.isfile(sel_file_directory):
               
                    return sel_file_directory
                      
            elif file_type == 'history':

                selected_file += self.get_selected_history_file(folder_type, widget_dict)

                sel_file_directory = unix_format(parent_directory) + selected_folder + '/___backup/' + selected_file

                if os.path.isfile(sel_file_directory):
                    return sel_file_directory

        except IndexError:
            pass
    

    def get_selected_hierarchical_folder(self, folder_type, widget_dict): 
        '''
        - returns an exact directory of selected folder or sub-folder
        '''
        try:
            #current_project = self.get_current_project() 
            
            if self.current_project == None:
                return None
            else:
                parent_folder = self.get_parent_item_in_qtreeview(folder_type, widget_dict)
                folder = ''

                if parent_folder != None: 
                    sub_folder = self.get_selected_folders(folder_type, widget_dict)[0]
                    folder += parent_folder + '/' + add_double_under_scores(sub_folder)
                else:
                    name = self.get_selected_folders(folder_type, widget_dict)[0]
                    if 'SCENE_' in name:
                        folder += name
                    else:
                        folder += add_double_under_scores(name)

                return folder
                                        
        except WindowsError:  
            pass


    def populate_items_in_focused_tab(self, folder_type, ui_widget):

        #current_project = self.get_current_project()
        get_design_folders_dict = {}

        if self.current_project != None:

            try:
                parent_folder = self.folder_type_directories_dict.get(folder_type)
                self.populate_folders_into_qtreeview(folder_type, ui_widget, eval(parent_folder))

            except AttributeError, WindowsError:
                pass

        else:
            return           


    def populate_items_in_design_tabs(self):
        self.populate_items_in_focused_tab('CHARACTER', self.create_design_tab_widgets)
        self.populate_items_in_focused_tab('PROPS', self.create_design_tab_widgets)
        self.populate_items_in_focused_tab('COMPONENT', self.create_design_tab_widgets)
        self.populate_items_in_focused_tab('ENVIRONMENT', self.create_design_tab_widgets)
        self.populate_items_in_focused_tab('CONTINUITY', self.create_design_tab_widgets)


    def open_file_in_design_tab(self, design_category, parent_folder):

        selected_file = self.get_selected_file_dir(design_category, '2d', self.create_design_tab_widgets, parent_folder)
        
        try:
            file_ext = selected_file.split('.')[-1]

            if file_ext in img_exts:
                open_image_file(selected_file)                       
            if file_ext in vid_exts:
                open_video_file(selected_file)
        except AttributeError:
            return


    def open_file_in_design_tabs(self, design_category):        

        design_categories_dict = {  'CHARACTER':    self.open_file_in_design_tab,
                                    'PROPS':        self.open_file_in_design_tab,
                                    'COMPONENT':    self.open_file_in_design_tab,
                                    'ENVIRONMENT':  self.open_file_in_design_tab,
                                    'CONTINUITY':   self.open_file_in_design_tab  }

        
        open_image_file = design_categories_dict.get(design_category, 'none')
        try:
            return open_image_file(design_category, eval(self.folder_type_directories_dict[design_category]))
        except TypeError:
            return


    def open_file_in_explorer_design_tab(self, design_category, parent_folder):

        selected_file = self.get_selected_file_dir(design_category, '2d', self.create_design_tab_widgets, parent_folder)
        
        if selected_file == None:
            return 
        else:
            subprocess.Popen(r'explorer /select, {}'.format(windows_format(selected_file)))


    def open_file_in_explorer_design_tabs(self, design_category):        

        design_categories_dict = {  'CHARACTER':     'self.open_file_in_explorer_design_tab',
                                    'PROPS':         'self.open_file_in_explorer_design_tab',
                                    'COMPONENT':     'self.open_file_in_explorer_design_tab',
                                    'ENVIRONMENT':   'self.open_file_in_explorer_design_tab',
                                    'CONTINUITY':    'self.open_file_in_explorer_design_tab' }

        open_file_explorer = eval(design_categories_dict.get(design_category))
        try:
            return open_file_explorer(design_category, eval(self.folder_type_directories_dict[design_category]))
        except TypeError:
            return


    def populate_items_in_shot_tab(self, folder_type):

        #current_project = self.get_current_project()
   
        if self.current_project == None:
            return

        else:
            try:
          
                shot_directory = self.folder_type_directories_dict.get(folder_type)
    
                self.populate_hierarchical_folders_into_qtreeview(folder_type, self.create_shot_tab_widgets, eval(shot_directory))
       
            except WindowsError, AttributeError:
                return 


    def populate_items_in_shot_tabs(self):
        self.populate_items_in_shot_tab('Model')
        self.populate_items_in_shot_tab('Layout')
        self.populate_items_in_shot_tab('Animation')
        self.populate_items_in_shot_tab('Lighting')
        self.populate_items_in_shot_tab('VFX')
        self.populate_items_in_shot_tab('Rendering')


    def populate_items_in_asset_tab(self, folder_type):

        #current_project = self.get_current_project()

        if self.current_project == None:
            return 

        else:                   
            try:
                asset_directory = self.folder_type_directories_dict.get(folder_type) 
                self.populate_hierarchical_folders_into_qtreeview(folder_type, self.create_asset_tab_widgets, eval(asset_directory))

            except WindowsError, AttributeError:
                return


    def populate_items_in_asset_tabs(self):
        self.populate_items_in_asset_tab('CHARACTER_SHADER')
        self.populate_items_in_asset_tab('COMPONENT_SHADER')
        self.populate_items_in_asset_tab('PROPS_SHADER')
        self.populate_items_in_asset_tab('PROPS_TEXTURE')
        self.populate_items_in_asset_tab('COMPONENT_TEXTURE')
        self.populate_items_in_asset_tab('CHARACTER_TEXTURE')
        self.populate_items_in_asset_tab('HIGH-RESOLUTION_CHARACTER')
        self.populate_items_in_asset_tab('HIGH-RESOLUTION_COMPONENT')
        self.populate_items_in_asset_tab('HIGH-RESOLUTION_ENVIRONMENT')
        self.populate_items_in_asset_tab('HIGH-RESOLUTION_PROPS')
        self.populate_items_in_asset_tab('LOW-RESOLUTION_CHARACTER')
        self.populate_items_in_asset_tab('LOW-RESOLUTION_COMPONENT')
        self.populate_items_in_asset_tab('LOW-RESOLUTION_ENVIRONMENT')
        self.populate_items_in_asset_tab('LOW-RESOLUTION_PROPS')
        self.populate_items_in_asset_tab('RIGGED_CHARACTER')
        self.populate_items_in_asset_tab('RIGGED_PROPS')
        self.populate_items_in_asset_tab('DEFORMED_CHARACTER')
        self.populate_items_in_asset_tab('DEFORMED_PROPS')
        self.populate_items_in_asset_tab('TEMPLATE_CHARACTER')
        self.populate_items_in_asset_tab('TEMPLATE_ENVIRONMENT')


    def populate_asset_shader_tab(self):
        self.populate_items_in_asset_tab('CHARACTER_SHADER')
        self.populate_items_in_asset_tab('COMPONENT_SHADER')
        self.populate_items_in_asset_tab('PROPS_SHADER')


    def populate_asset_texture_tab(self):
        self.populate_items_in_asset_tab('CHARACTER_TEXTURE')
        self.populate_items_in_asset_tab('COMPONENT_TEXTURE')
        self.populate_items_in_asset_tab('PROPS_TEXTURE')


    def populate_asset_rig_char_tab(self):
        self.populate_items_in_asset_tab('RIGGED_CHARACTER')
        self.populate_items_in_asset_tab('DEFORMED_CHARACTER')


    def populate_asset_rig_props_tab(self):
        self.populate_items_in_asset_tab('RIGGED_PROPS')
        self.populate_items_in_asset_tab('DEFORMED_PROPS')


    def populate_asset_model_char_tab(self):
        self.populate_items_in_asset_tab('HIGH-RESOLUTION_CHARACTER')
        self.populate_items_in_asset_tab('LOW-RESOLUTION_CHARACTER')


    def populate_asset_model_props_tab(self):
        self.populate_items_in_asset_tab('HIGH-RESOLUTION_PROPS')
        self.populate_items_in_asset_tab('LOW-RESOLUTION_PROPS')


    def populate_asset_model_environment_tab(self):
        self.populate_items_in_asset_tab('HIGH-RESOLUTION_ENVIRONMENT')
        self.populate_items_in_asset_tab('LOW-RESOLUTION_ENVIRONMENT')


    def populate_asset_model_component_tab(self):
        self.populate_items_in_asset_tab('HIGH-RESOLUTION_COMPONENT')
        self.populate_items_in_asset_tab('LOW-RESOLUTION_COMPONENT')


    def get_main_stacked_layout_current_index(self):
     
        return int(self.main_stacked_layout.currentIndex())


    def get_design_tabs_current_index(self):
     
        return int(self.design_widget.currentIndex())

    
    def get_asset_tabs_current_index(self):
   
        return int(self.asset_widget.currentIndex())

        
    def refresh_current_ui(self):   
     
        exec( eval( self.refresh_ui_dict.get( self.get_main_stacked_layout_current_index() ) ) )        
     
    
    def refresh_tabwidget(self, tab_widget):
 
        tab_widget.currentChanged.connect(lambda: self.refresh_current_ui())


    def create_folder_button(self, folder_type, ui_widget ):

        lineEdit = folder_type + '_line_edit'
        button1 = folder_type + '_button1' 

        #current_project = self.get_current_project()

        if self.current_project == None:
            ui_widget[lineEdit].clear()
            ui_widget[button1].setEnabled(False)
            return
        
        # the keys of below dictionary are the 'folder_type'
        make_folders_dict = { '1_MODEL_CHARACTER':          'self.current_project.make_char_dirs',
                              '1_MODEL_PROPS':              'self.current_project.make_props_dirs',
                              '1_MODEL_COMPONENT':          'self.current_project.make_com_dirs',
                              '1_MODEL_ENVIRONMENT':        'self.current_project.make_env_dirs', 
                              '4_TEMPLATES_RENDERING':      'self.current_project.make_render_template_dirs',
                              '4_TEMPLATES_ENVIRONMENT':    'self.current_project.make_env_template_dirs',
                              '4_TEMPLATES_CHARACTER':      'self.current_project.make_char_template_dirs'}

        folder_name = ui_widget[lineEdit].text()

        if folder_name != '':
         
            try:
                exec( make_folders_dict.get(folder_type) + '("__" + folder_name)' )                
                ui_widget[lineEdit].clear()
                self.refresh_current_ui()                
            except WindowsError:
                ui_widget[lineEdit].clear()
                ui_widget[button1].setEnabled(False)
                return
        else:
            ui_widget[lineEdit].clear()
            ui_widget[button1].setEnabled(False)


    def create_new_variation(self, widget_dict, *folder_types):
        '''
        - current function only works for 'Create New Variation' button
        '''
        for folder_type in folder_types:
            
            temp_dir = self.folder_type_directories_dict.get(folder_type)
          

            sel_file_directory = self.get_selected_file_dir(folder_type, 'maya', widget_dict, eval(temp_dir))
   

            if sel_file_directory != None:

                parent_directory = self.extract_directory_name_extension(sel_file_directory, 0) + '___backup/'

                name = self.extract_directory_name_extension(sel_file_directory, 1)
                
                new_file_name = self.current_project.make_file_version(parent_directory, name)

                new_file_directory = parent_directory + new_file_name + self.extract_directory_name_extension(sel_file_directory, 2)

                shutil.copy(sel_file_directory, new_file_directory)

                self.refresh_history_qtreeview(folder_type, widget_dict, parent_directory)

                break


    def extract_directory_name_extension(self, sel_file_directory, return_value):
        '''
        - 'sel_file_directory' is a string that looks like 'c:/file_directory/objname_v-7.ma'
        - this function extracts the file directory 'c:/file_directory/' and the base name of the file 'objname', which filters out
          the version number and file extension 
        - 'return_value' only accepts 0, 1, 2, which indicates the function returns directory, name, extension accordingly.
        '''
        try:
            file_name = sel_file_directory.split('/')[-1]
            directory = sel_file_directory.replace(file_name , '')  
            name = file_name.split('.')[0]
            extension = file_name.split('.')[1]

            if return_value == 0:
                return directory
            if return_value == 1:
                return name
            if return_value == 2:
                return '.' + extension 

        except KeyError:
            return None


    def refresh_history_qtreeview(self, folder_type, widget_dict, parent_directory):

        treeView3 = folder_type + '_treeView3'
        model3 = folder_type + '_model3'

        try:
            widget_dict[model3].clear()
            widget_dict[model3].setHorizontalHeaderLabels(['>>> history <<<'.upper()])        
        except KeyError:
            pass

        if os.path.isdir(parent_directory):
            for file in os.listdir(parent_directory):   
                try:                                                  
                    item = QStandardItem(file)                            

                    item.setIcon(widget_dict[treeView3].style().standardIcon(QStyle.SP_FileIcon))
                    item.setEditable(False)

                    widget_dict[model3].appendRow([item])
                except KeyError:
                    pass
        else:
            try:
                widget_dict[model3].clear()
                widget_dict[model3].setHorizontalHeaderLabels(['>>> history <<<'.upper()])     
            except KeyError:
                pass        


    def set_active(self, widget_dict, *folder_types):
        '''
        - set selected history file as an active file
        - automatically backup the current file as a new variation
        '''
        for folder_type in folder_types:

            temp_dir = self.folder_type_directories_dict.get(folder_type)       

            sel_file_directory = self.get_selected_file_dir( folder_type, 'history', widget_dict, eval(temp_dir) )

            if sel_file_directory != None:

                directory = self.extract_directory_name_extension(sel_file_directory, 0)    

                parent_directory = ''
                if '/___backup/' in directory or '/___backup' in directory:
                    parent_directory += directory.replace('___backup/' , '')

                name_with_version = self.extract_directory_name_extension(sel_file_directory, 1)

                name = name_with_version.split('_v-')[0]
 
                new_file_directory = unix_format(parent_directory) + name + self.extract_directory_name_extension(sel_file_directory, 2)

                src_file_directory = new_file_directory

                os.remove(src_file_directory)

                shutil.copy(sel_file_directory, new_file_directory)
     
                break           


    def sel_file_activate_button_fx(self, create_new_variation_button, switcher1, set_active_button, switcher2):
    
        create_new_variation_button.setEnabled(switcher1)
        set_active_button.setEnabled(switcher2)


    def reference_maya_file(self, maya_file, *batch_amount):
        '''
        - 'maya_file' should be a complete path and file name with extension, which looks like 'c:\folder\mayafile.ma'
        - 'batch_amount' is optional, which indicates the amount of given file to be referenced
        '''
        amount_of_referencing = 0

        if batch_amount:
            amount_of_referencing = batch_amount[0]
        else:
            amount_of_referencing = 1    
   
        script_path = windows_format(self.extract_directory_name_extension(maya_file, 0) + '___script')

        mel_file_dir = script_path + '\\referencing.mel'

        mel_file_obj = open(mel_file_dir, 'w')
        mel_file_obj.flush()
        mel_file_obj.close()

        if amount_of_referencing < 2:

            namespace = self.extract_directory_name_extension(maya_file, 1) 

            referencing_mel_strings = 'file -r -type "mayaAscii"  -ignoreVersion -gl -mergeNamespacesOnClash false -namespace "{0}" -options "v=0;" "{1}";\n'.format(namespace, maya_file)
            
            export_strings_to_file(referencing_mel_strings, mel_file_dir)

        elif amount_of_referencing >= 2: 

            referencing_mel_strings = ''

            for i in range(amount_of_referencing):

                namespace = self.extract_directory_name_extension(maya_file, 1) + str(i+1)

                referencing_mel_strings += 'file -r -type "mayaAscii"  -ignoreVersion -gl -mergeNamespacesOnClash false -namespace "{0}" -options "v=0;" "{1}";\n'.format(namespace, maya_file)
                
                export_strings_to_file(referencing_mel_strings, mel_file_dir)

        os.system('start maya.exe -script "{}"'.format(mel_file_dir) )


    def reference_maya_file_button(self, widget_dict, *folder_types):

        for folder_type in folder_types:
            try:
                temp_dir = self.folder_type_directories_dict.get(folder_type)          

                sel_file_directory = self.get_selected_file_dir( folder_type, 'maya', widget_dict, eval(temp_dir) )

                amount = self.get_amount_of_referencing(folder_type) 
           
                self.reference_maya_file( sel_file_directory, amount)

                break

            except AttributeError:
                pass


    def get_amount_of_referencing(self, folder_type):

        amount_of_file_type_dict = {    'CHARACTER_SHADER':             '1', 
                                        'COMPONENT_SHADER':             '1', 
                                        'PROPS_SHADER':                 '1', 
                                        'HIGH-RESOLUTION_CHARACTER':    'self.create_asset_tab_widgets["1_MODEL_CHARACTER_lineEdit2"].text()', 
                                        'HIGH-RESOLUTION_COMPONENT':    'self.create_asset_tab_widgets["1_MODEL_COMPONENT_lineEdit2"].text()', 
                                        'HIGH-RESOLUTION_ENVIRONMENT':  'self.create_asset_tab_widgets["1_MODEL_ENVIRONMENT_lineEdit2"].text()', 
                                        'HIGH-RESOLUTION_PROPS':        'self.create_asset_tab_widgets["1_MODEL_PROPS_lineEdit2"].text()', 
                                        'LOW-RESOLUTION_CHARACTER':     'self.create_asset_tab_widgets["1_MODEL_CHARACTER_lineEdit2"].text()', 
                                        'LOW-RESOLUTION_COMPONENT':     'self.create_asset_tab_widgets["1_MODEL_COMPONENT_lineEdit2"].text()', 
                                        'LOW-RESOLUTION_ENVIRONMENT':   'self.create_asset_tab_widgets["1_MODEL_ENVIRONMENT_lineEdit2"].text()', 
                                        'LOW-RESOLUTION_PROPS':         'self.create_asset_tab_widgets["1_MODEL_PROPS_lineEdit2"].text()',             
                                        'RIGGED_CHARACTER':             'self.create_asset_tab_widgets["2_RIG_CHARACTER_lineEdit2"].text()', 
                                        'RIGGED_PROPS':                 'self.create_asset_tab_widgets["2_RIG_PROPS_lineEdit2"].text()', 
                                        'DEFORMED_CHARACTER':           'self.create_asset_tab_widgets["2_RIG_CHARACTER_lineEdit2"].text()', 
                                        'DEFORMED_PROPS':               'self.create_asset_tab_widgets["2_RIG_PROPS_lineEdit2"].text()', 
                                        'TEMPLATE_CHARACTER':           '1', 
                                        'TEMPLATE_ENVIRONMENT':         '1',
                                        'TEMPLATE_RENDERING':           '1', 


                                        'Model':                        '1',
                                        'Layout':                       '1',
                                        'Animation':                    '1',                         
                                        'Anim_Cache':                   '1',
                                        'Lighting':                     '1',
                                        'VFX':                          '1',
                                        'VFX_Cache':                    '1',
                                        'Rendering':                    '1' }

        amount = eval(amount_of_file_type_dict.get(folder_type))

        if amount == '':
            return 1
        else: 
            return int(amount)


    def open_maya_file_button(self, widget_dict, *folder_types):

        for folder_type in folder_types:
            try:
                temp_dir = self.folder_type_directories_dict.get(folder_type)          

                sel_file_directory = self.get_selected_file_dir( folder_type, 'maya', widget_dict, eval(temp_dir) )                
                
                if sel_file_directory != None:
                    os.system('start maya.exe "{}"'.format(sel_file_directory))
                    break
                else:
                    pass 

            except AttributeError:
                pass    




# ======================================
# ======= some backend functions =======
# ======================================

def get_drives_letters():
    physical_drives = []
    from string import ascii_uppercase
    for letter in ascii_uppercase[2:]:
        if os.path.exists(letter + r':/'):
            physical_drives.append(letter + r':/')
    return physical_drives

def export_strings_to_file(strings, dst_file_dir):
    '''
    - this function writes the given 'strings' to an exact file from the 'dst_file_dir'
    - 'strings' should be something like 'abcdefghijk lmnopq rstuvxyz'
    - 'dst_file_dir' should be a complete path and file name with extension, which looks like 'c:\folder\file.ext'
    '''
    import array 
    file_object = open(dst_file_dir, 'w')
    array.array('c', strings).tofile(file_object)
    file_object.close()


def unix_format(path_of_directory):
    '''
    convert the format of Windows path to Unix style, 
    Windows style: '\' -->  Unix style: '/'
    '''
    if '\\' in path_of_directory:
        path_of_directory = path_of_directory.replace('\\','/')
    if path_of_directory[-1] != '/':
        path_of_directory += '/' 
    return path_of_directory


def windows_format(path_of_directory):
    '''
    convert the unix_format directory to windows style
    '''
    if '/' in path_of_directory:
        path_of_directory = path_of_directory.replace('/','\\')
    if path_of_directory.endswith('\\'):
        path_of_directory = path_of_directory[:-1]
    return path_of_directory




def convert_digit_strings_to_int_list(input_strings):
    '''
    - this tiny function converts strings like '1 2 3 4 5' to a list [1,2,3,4,5]
    '''
    strings_list = input_strings.split(' ')
    int_list = []
    try:
        for element in strings_list:
            i = int(element)
            int_list.append(i)
        return int_list
    except ValueError:
        return None 
            

def initial_shot_dict():
    '''
    - collect input data from gui, which represent the scene numbers and associated shot amounts
    - the amount of given scene numbers must equal to the shot ones, otherwise, it only returns an empty dictionary
    '''
    # collect data from the "scene-numbers" line_edit and "shot-amounts" line_edit 
    scene_numbers = convert_digit_strings_to_int_list(project_manager_gui.scene_line_edit.text())
    shot_amount = convert_digit_strings_to_int_list(project_manager_gui.shot_line_edit.text())
    
    init_scene_shot_dict = {}
    try:
        if len(scene_numbers) != len(shot_amount):
            return init_scene_shot_dict # returns an empty dictionary

        elif scene_numbers == None or shot_amount == None:
            init_scene_shot_dict = {1:1}
            return init_scene_shot_dict # if there're no inputs from UI, thenreturns an initial {1:1} dict

        else:
            for scn, shot in zip(scene_numbers, shot_amount):
                init_scene_shot_dict[scn] = shot

            return init_scene_shot_dict

    except TypeError:
        pass

             
def update_shot_dict(dict_amount,scene_num,shot_amount):
    '''
    - this function returns an updated dict_amount, which based on the given scene_num and shot_amount
    - dict_amount is a dictionary type, this function accepts empty/non-empty dictionary, it looks like: {<scn_num>:<amount_of_shots>}, for example: {1:10,2:7,...}
    - scene_num and shot_amount are int type, which indicates the scene number and its corresponding amount of shots
    '''
    if dict_amount == None:
        dict_amount = {1:1}
        update_shot_dict(dict_amount,scene_num,shot_amount)
    else:
        dict_amount.keys().append(scene_num)
        dict_amount[scene_num] = shot_amount
       
        return dict_amount

    
def make_folders(parent_dir,base_name):    
    '''
    parent_dir is a string type, make sure to be end with '/'
    base_name is the name of folder
    '''
    dir = unix_format(parent_dir)
    folder = dir + base_name
    os.mkdir(folder)    
    
    
def folder_is_hidden(dir):

    if os.path.isdir(dir):
        attribute = win32api.GetFileAttributes(dir)
        if attribute & (win32con.FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_SYSTEM):
            return True
        else:
            return False
    

def add_double_under_scores(folder_name):
    if folder_name[:2] != '__':
        return '__' + folder_name
    else:
        return folder_name


def remove_double_under_scores(folder_name):
    if folder_name[:2] == '__':
        return folder_name.split('__')[-1]
    else:
        return folder_name


def open_image_file(img_file):
    '''
    - img_file must represent a full directory of the file, e.g. c:/folder/img_file.jpg
    - opens the given image file with the default OS's image application
    - normally in Windows it uses the "Windows Photo Viewer" app to view the image file
    '''
    try:
        os.system(img_file)
    except WindowsError:
        pass 


def open_video_file(vid_file):
    '''
    - vid_file must represent a full directory of the file, e.g. c:/folder/vid_file.mov
    - opens the given video file with the VLC player
    - needs to install VLC player prior to use current function
    '''
    try:
        subprocess.Popen([VLC_PLAYER, windows_format(vid_file)])
    except WindowsError:
        pass


def add_maya_reference_file_mel(src_file, dst_file):
    '''
    return a MEL string for file referencing
    'src_file' should include the file path as well, make sure it's using unix_format(), e.g.: x:/proj/mayafile.ma
    '''
    name = src_file.split('.')[0].split('/')[-1]

    mel1 = 'file -rdi 1 -ns "{0}" -rfn "{0}RN" -op "v=0;" -typ "mayaAscii" "{1}";\n'.format(name, src_file)
    mel2 = 'file -r -ns "{0}" -dr 1 -rfn "{0}RN" -op "v=0;" -typ "mayaAscii" "{1}";\n'.format(name, src_file)

    maya_file = open(dst_file, 'r')
    contents = maya_file.readlines()
    maya_file.close()

    contents.insert(4, mel1)
    contents.insert(5, mel2)
    
    contents = "".join(contents)

    maya_file = open(dst_file, 'w')
    maya_file.write(contents)
    maya_file.close()


project_manager_gui = main_gui()   

project_manager_gui.show(dockable=True)          