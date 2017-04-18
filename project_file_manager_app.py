import inspect
import os
import sys
import time
import subprocess
import ctypes
import win32api, win32con
import win32file
import shutil
import Queue
from pprint import pprint
from functools import partial, wraps
from PySide.QtCore import *
from PySide.QtGui import * 

author_info = 'Designed and Implemented by PREDATOR'
ver_info = '|   Build_At_ '
for t in time.localtime()[:5]:
    ver_info += str(t)

current_python_file_directory = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

if current_python_file_directory not in sys.path:
    sys.path.append(current_python_file_directory)
    
import configuration
reload(configuration)

VLC_PLAYER = r'C:/Applications/vlc-2.2.4-win64/vlc.exe'
img_exts = ['png', 'jpg', 'jpeg', 'tif', 'tiff', 'bmp']
vid_exts = ['mov', 'mpeg', 'avi', 'mp4', 'wmv']

desktop_scaled = 1.5

# =======================================================
# ========= Set some MAYA Environment Variables =========
# =======================================================

if os.environ['PATH'][-1] != ';':
    os.environ['PATH'] += '; '

#check if '...\maya\bin' is stored in system 'PATH' variable
try:
    os.environ['PATH'] += '; ' + os.environ['MAYA_LOCATION'] + '\\bin;'
except KeyError: # when KeyError occurs, which means 'MAYA_LOCATION' is not in system's environment variables
    maya_location_variable = 'c:\\program files\\autodesk\\maya2017'
    os.environ['MAYA_LOCATION'] = maya_location_variable 

    os.environ['PATH'] += os.environ['MAYA_LOCATION'] + '\\bin; '

# enable the crash log file, and the file will be saved in the directory of os.environ['TMP']
os.environ['MAYA_ENABLE_MULTI_DRAW_CONSOLIDATION']      = "2"
os.environ['MAYA_DEBUG_ENABLE_CRASH_REPORTING']         = "1"
os.environ['MAYA_DISALLOW_DUPLICATE_ATTRIBUTE_NAMES']   = "1"
os.environ['MAYA_USE_MALLOC']                           = "1"
os.environ['MAYA_ENABLE_NG_CONSOLE_STATS']              = "1"
os.environ['MAYA_ASCII_ENABLE_BULK_PARSING']            = "1"
os.environ['MAYA_ASCII_SUPPORT_MAC_LINE_ENDINGS']       = "0"


# =======================================================
# ======= the implementation of Folder Structures =======
# =======================================================
class CG_Project(object):
    """
    - create structural folders for the project
    - can dynamtically add new scene-shot folders for all the shot-based directories
    """
    def __init__(self, project_name, dict_amount):

        self.maya_asset_directories_dict = {    #geo assets:
                                                'geo_hi_char':      'self.get_char_hiGeo_dir()',
                                                'geo_low_char':     'self.get_char_lowGeo_dir()',                                    
                                                'geo_hi_props':     'self.get_props_hiGeo_dir()',
                                                'geo_low_props':    'self.get_props_lowGeo_dir()',
                                                'geo_hi_com':       'self.get_com_hiGeo_dir()',
                                                'geo_low_com':      'self.get_com_lowGeo_dir()',
                                                'geo_hi_env':       'self.get_env_hiGeo_dir()',
                                                'geo_low_env':      'self.get_env_lowGeo_dir()',

                                                # rig assets:
                                                'rig_char':         'self.get_char_rig_dir()',
                                                'def_char':         'self.get_char_def_dir()',
                                                'rig_props':        'self.get_props_rig_dir()',
                                                'def_props':        'self.get_props_def_dir()',

                                                # surfacing assets:
                                                'surf_char':        'self.get_char_shader_dir()',    
                                                'surf_props':       'self.get_props_shader_dir()',
                                                'surf_com':         'self.get_env_shader_dir()',

                                                # templates assets:
                                                'ligtemp_char':     'self.get_char_light_template_dir()',
                                                'ligtemp_env':      'self.get_env_light_template_dir()',
                                                'render_template':  'self.get_render_template_dir()'}       

        self.maya_shot_directories_dict = {     'anim_':        'self.get_anim_shot_dir()',
                                                'layout_':      'self.get_layout_shot_dir()',                                    
                                                'vfx_':         'self.get_vfx_shot_dir()',
                                                'light_':       'self.get_lighting_shot_dir()',
                                                'render_':      'self.get_rendering_shot_dir()',
                                                'geo_':         'self.get_geo_shot_dir()',
                                                'anim_cache_':  'self.get_anim_cache_shot_dir()',
                                                'vfx_cache_':   'self.get_vfx_cache_shot_dir()' }   

        self.project_name = project_name
        self.project_directory = project_manager_gui.select_drive_combo_box.currentText() + self.project_name + '/'
        self.dict_amount = dict_amount
        self.make_folder_structure()
        self.make_hidden_folders('backup') 
        self.make_hidden_folders('script')        
        self.get_directories_for_shots_attr = self.get_directories_for_shots()
        self.get_directories_for_assets_attr = self.get_directories_for_assets()
        # generates initial maya shot files
        self.make_init_maya_shot_files(self.dict_amount)  


    def directories_for_shots(self):
        '''
        - this function returns a list of directories that hold scene-shot hierarchical folders
        - it only works for the first time when the whole project structure is created and there's no scene-shot folders 
        '''
        no_shot_dirs = configuration.no_shot_folders
        directories = []
        for paths, dirs, files in os.walk(self.project_directory):
            paths = unix_format(paths)
            if paths.split('/')[-2] not in no_shot_dirs and paths.split('/')[-2][:2] != '__' and os.listdir(paths) == [] :
                directories.append(paths)
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
        for dir in dirs_for_shots:
            self.__make_hierarchical_folders(dir,'SCENE_','__Shot_')              


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
        #root_directory = configuration.network_drive
        root_directory = project_manager_gui.select_drive_combo_box.currentText()
        project_directory = self.project_directory
        # create the project root folder
        if self.project_name not in os.listdir(root_directory) and self.project_name != '':
            os.mkdir(self.project_directory)
        try:
            # create department folders        
            self.__make_dict_folders(self.project_directory,configuration.Departments)
            # creates scene-shots hierarchical folders
            self.generate_scene_shot_folders()

        except AttributeError:
            pass


    def add_scene_shot_folders(self, new_dict_amount):
        '''
        - this function adds new scene-shots folders for directories_for_shots
        - can pass new dict_amount then call this function in order to add new scene-shot folders
        - dict_amount is a dictionary type, it looks like: {<scn_num>:<amount_of_shots>}, for example: {1:10,2:7,...}
        '''
        try:
            for k, v in new_dict_amount.iteritems():
                update_shot_dict(self.dict_amount, k, v)
            dirs_for_shots = self.get_directories_for_shots_attr
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


    @exec_once_when_init 
    def get_directories_for_shots(self):
        '''
        - this function returns a list of directories that hold scene-shot hierarchical folders
        - it works for the project that parts of the scene-shot folders have been created
        '''
        no_shot_dirs = configuration.no_shot_folders
        directories = []

        for paths, dirs, files in os.walk(self.project_directory):
            paths = unix_format(paths)
            
            if paths.split('/')[-2] not in no_shot_dirs and paths.split('/')[-2][:2] != '__' :
                
                if os.listdir(paths) != [] and os.listdir(paths)[0][:6] == 'SCENE_' :
                    
                    directories.append(paths)
        
        return directories


    @exec_once_when_init 
    def get_directories_for_assets(self):
        '''
        - this function returns a list of directories that hold project assets
        '''
        asset_parent_folders = configuration.asset_folders
        asset_directories = []
        for paths, dirs, files in os.walk(self.project_directory):
            paths = unix_format(paths)
            if len(paths.split('/')) > 4 and paths.split('/')[2] in configuration.asset_folders:
                if os.listdir(paths) != [] and paths.split('/')[-3] != 'SHOTS':
                    if os.listdir(paths)[0][:2] == '__':
                        asset_directories.append(paths)
        return asset_directories


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


    def get_anim_shot_dir(self): 
        '''
        - returns a directory for the Maya animation files
        '''
        all_shots_dirs = self.get_directories_for_shots_attr
        
        shot_dir = ''
        
        for dir in all_shots_dirs:
            if dir.split('/')[2] == 'ANIMATION' and dir.split('/')[3] == 'Finals':
                shot_dir = dir
                break
        
        return unix_format(shot_dir)
             

    def get_anim_playblast_dir(self):
        '''
        - returns a directory for the Animation Playblasts movie file
        '''
        all_shots_dirs = self.get_directories_for_shots_attr
        
        shot_dir = ''
        
        for dir in all_shots_dirs:
            if dir.split('/')[2] == 'ANIMATION' and dir.split('/')[3] == 'Playblasts'and dir.split('/')[4] == 'Finals_MOV':
                shot_dir = dir
                break
        
        return shot_dir


    def get_layout_playblast_dir(self):
        '''
        - returns a directory for the Animation Playblasts movie file
        '''
        all_shots_dirs = self.get_directories_for_shots_attr
        
        shot_dir = ''
        
        for dir in all_shots_dirs:
            if dir.split('/')[2] == 'ANIMATION' and dir.split('/')[3] == 'Playblasts'and dir.split('/')[4] == 'Layouts_MOV':
                shot_dir = dir
                break

        return shot_dir


    def get_layout_shot_dir(self): 
        '''
        - returns a directory for the Maya layout file
        '''
        all_shots_dirs = self.get_directories_for_shots_attr
        
        shot_dir = ''
        
        for dir in all_shots_dirs:
            if dir.split('/')[2] == 'ANIMATION' and dir.split('/')[3] == 'Layouts':
                shot_dir += dir 
                break
         
        return shot_dir         
         

    def get_anim_cache_shot_dir(self): 
        '''
        - returns a directory for the Maya animation file
        '''
        all_shots_dirs = self.get_directories_for_shots_attr
        
        shot_dir = ''
        
        for dir in all_shots_dirs:
            if dir.split('/')[2] == 'ANIMATION' and dir.split('/')[3] == 'Cached':
                shot_dir = dir
                break
        
        return shot_dir


    def get_lighting_shot_dir(self): 
        '''
        - returns a directory for the Maya lighting file
        '''
        all_shots_dirs = self.get_directories_for_shots_attr
        
        shot_dir = ''
        
        for dir in all_shots_dirs:
            if dir.split('/')[2] == 'LIGHTING' :
                shot_dir += dir 
                break
         
        return shot_dir         
         

    def get_rendering_shot_dir(self): 
        '''
        - returns a directory for the Maya rendering file
        '''
        all_shots_dirs = self.get_directories_for_shots_attr
        
        shot_dir = ''
        
        for dir in all_shots_dirs:
            if dir.split('/')[2] == 'RENDERING' :
                shot_dir += dir
                break
         
        return shot_dir 


    def get_geo_shot_dir(self): 
        '''
        - returns a directory for the shot-based Maya model file
        '''
        all_shots_dirs = self.get_directories_for_shots_attr
        
        shot_dir = ''
        
        for dir in all_shots_dirs:
            if dir.split('/')[2] == 'MODEL' :
                shot_dir += dir 
                break
         
        return shot_dir            


    def get_vfx_shot_dir(self): 
        '''
        - returns a directory for the Maya vfx file
        '''
        all_shots_dirs = self.get_directories_for_shots_attr
        
        shot_dir = ''
        
        for dir in all_shots_dirs:
            if dir.split('/')[2] == 'VFX' and dir.split('/')[3] == 'SHOTS': 
                shot_dir += dir 
                break
         
        return shot_dir         


    def get_vfx_cache_shot_dir(self): 
        '''
        - returns a directory for the Maya vfx file
        '''
        all_shots_dirs = self.get_directories_for_shots_attr
        
        shot_dir = ''
        
        for dir in all_shots_dirs:
            if dir.split('/')[2] == 'VFX' and dir.split('/')[3] == 'Cached': 
                shot_dir += dir 
                break
         
        return shot_dir   


    def get_shot_file_dir(self, type, scn_number, shot_number): 
        '''
        - returns a directory for the given scene-shot Maya animation file
        - 'type' should be the keys of the self.maya_shot_directories_dict
        '''
        parent_directory = eval(self.maya_shot_directories_dict.get(type))
      
        shot_dir = parent_directory + 'SCENE_{0}/__Shot_{1}/'.format(str(scn_number), str(shot_number))        
  
        return unix_format(shot_dir)

        
    def make_maya_shot_file_strings(self, type, scn_number, shot_number):
        '''
        - returns a proper Maya file name and directory for the given type, scene and shot number.
        - type is string type, only accepts keys of self.maya_shot_directories_dict
        - scn_number and shot_number are int type.
        '''    
        
        # retrive the exact directory 

        shot_dir = self.get_shot_file_dir(type, scn_number, shot_number)

        shot = type + 'scene_{0}_shot_{1}.ma'.format(str(scn_number), str(shot_number))        
        #shot_file_name = self.make_file_version(dir, shot)
        
        return windows_format(shot_dir + shot)
        
    
    def make_init_maya_shot_files(self, dict_scene_shot):
        '''
        - this function generates empty maya files for all the shots based on the given dictionary of scene-shots
        - 'dict_scene_shot' is an argument of dict type
        '''
        empty_maya_file = windows_format(current_python_file_directory + '/empty.ma')

        for scn_number, shot_amount in dict_scene_shot.iteritems():          
            
            for shot_number in range(shot_amount):

                anim_shot_file          =   self.make_maya_shot_file_strings('anim_',       scn_number, (shot_number+1))
                layout_shot_file        =   self.make_maya_shot_file_strings('layout_',     scn_number, (shot_number+1))
                vfx_shot_file           =   self.make_maya_shot_file_strings('vfx_',        scn_number, (shot_number+1))
                render_shot_file        =   self.make_maya_shot_file_strings('render_',     scn_number, (shot_number+1))
                light_shot_file         =   self.make_maya_shot_file_strings('light_',      scn_number, (shot_number+1))
                geo_shot_file           =   self.make_maya_shot_file_strings('geo_',        scn_number, (shot_number+1))
                anim_cache_shot_file    =   self.make_maya_shot_file_strings('anim_cache_', scn_number, (shot_number+1))
                vfx_cache_shot_file     =   self.make_maya_shot_file_strings('vfx_cache_',  scn_number, (shot_number+1))

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

                if not os.path.isfile(anim_cache_shot_file):
                    shutil.copyfile(empty_maya_file, anim_cache_shot_file)
                else:
                    pass                    

                if not os.path.isfile(vfx_cache_shot_file):
                    shutil.copyfile(empty_maya_file, vfx_cache_shot_file)                                                         
                else:
                    pass


    def get_maya_file_dirs(self):
        '''
        - returns a list of all the paths that holding the Maya files
        '''
        maya_folders = []
        all_folders = []
        for paths, dirs, files in os.walk(self.project_directory):
            all_folders.append(paths)
        
        for folder in all_folders:            
            dir = unix_format(folder)
            folder_name = dir.split('/')[-2]            
            if '__' in folder_name:
                maya_folders.append(dir)
                
        return maya_folders 
                
                
    def get_maya_files(self):
        '''
        - returns a dictionary, which looks like {dir1:[maya_file1,maya_file2...], dir1:[maya_file1,maya_file2...]}
        '''
        maya_file_dirs = self.get_maya_file_dirs()
        maya_files = {}
        
        for dir in maya_file_dirs:
            files = os.listdir(dir)
            maya_files[dir] = files
        
        return maya_files

    def get_char_design_dir(self):
        '''
        - return a paths for character design directory
        '''
        return self.project_directory + '2D/Concept_Design/Characters/'


    def get_props_design_dir(self):
        '''
        - return a paths for props design directory
        '''
        return self.project_directory + '2D/Concept_Design/Props/'


    def get_env_design_dir(self):
        '''
        - return a paths for environment design directory
        '''
        return self.project_directory + '2D/Concept_Design/Environments/'


    def get_2d_continuities_dir(self):
        '''
        - return a paths for 2D continuities directory
        '''
        return self.project_directory + '2D/Continuities/'                


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



class CG_Project_Edit(CG_Project):
    """
    - Edit projects that created by class CG_Project()
    - can dynamtically add new scene-shot folders for all the shot-based directories
    """
    def __init__(self, drive, project_name):        
        self.project_name = project_name
        self.project_directory = unix_format(drive + self.project_name)   
        # override the original 'self.dict_amount'    
        self.dict_amount = self.get_current_scene_shot_dict()
        # pass the newly overrided 'self.dict_amount' attribute to the parent class's '__init__'
        CG_Project.__init__(self, project_name, self.dict_amount)
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
             
class main_gui(QWidget):
    
    def __init__(self, parent = None):
        super(main_gui, self).__init__(parent)

        self.main_layout = QVBoxLayout()
        
        self.main_stacked_widget = QWidget()
        self.main_stacked_widget.setFixedHeight(877*desktop_scaled)
        self.main_stacked_layout = QStackedLayout(self.main_stacked_widget)   

        self.project_widget= QWidget()
        self.project_widget.setFixedHeight(110*desktop_scaled)
        self.project_widget.setFixedWidth(1000*desktop_scaled)        
        
        # create widget for buttons
        self.category_buttons_widgets = QWidget()
        self.category_buttons_layout = QHBoxLayout(self.category_buttons_widgets)   
        self.category_buttons_widgets.setFixedHeight(50*desktop_scaled)

        self.design_section_button = QPushButton('2D DRAWINGS')
        self.design_widget = QTabWidget()
        self.design_widget.setFixedHeight(870*desktop_scaled)
        
        self.asset_section_button = QPushButton('3D ASSETS')
        self.asset_widget = QWidget()
        self.asset_widget.setFixedHeight(870*desktop_scaled)
        #self.asset_main_layout = QVBoxLayout(self.asset_widget)
        
        self.shot_section_button= QPushButton('SHOTS')
        self.shot_widget = QTabWidget()
        self.shot_widget.setFixedHeight(870*desktop_scaled)
        
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

        self.create_project_widget = QWidget()    
        self.set_project_widget = QWidget()
        self.init_scene_widget = QWidget()      
       
        self.project_layout.addWidget(self.init_scene_widget)       
        self.project_layout.addWidget(self.create_project_widget)                      
        self.project_layout.addWidget(self.set_project_widget )  
        
        self.create_project_layout = QVBoxLayout(self.create_project_widget)
        self.set_project_layout = QVBoxLayout(self.set_project_widget)
        self.init_scene_layout = QVBoxLayout(self.init_scene_widget)        
        
        # create project section
        self.create_project_label = QLabel('==== Create New Project ====')
        self.create_project_label.setFixedHeight(17*desktop_scaled)
        self.create_project_label.setAlignment(Qt.AlignLeft)
        
        self.select_drive_combo_box = QComboBox()
        self.select_drive_combo_box.setFixedWidth(47*desktop_scaled)       

        # clear and populate drive letters into the combox
        self.select_drive_combo_box.clear()
        self.drive_list = get_drives_letters()
        self.select_drive_combo_box.addItems(self.drive_list)
        
        # emit a signal when switching drives
        self.select_drive_combo_box.currentIndexChanged.connect(lambda:self.update_combo_box_list())
        
        self.project_name_line_edit = QLineEdit()
        self.project_name_line_edit.setFixedWidth(170*desktop_scaled) 
        self.project_name_line_edit.setFixedHeight(20*desktop_scaled) 
        self.project_name_line_edit.setPlaceholderText('Please type project name here...')                        
        self.project_name_line_edit.returnPressed.connect(lambda: self.select_texts(self.project_name_line_edit))
        
        self.create_project_button = QPushButton('Create Project')
        self.create_project_button.setFixedWidth(171*desktop_scaled)  
        self.create_project_button.setFixedHeight(24*desktop_scaled) 
        self.create_project_button.clicked.connect(lambda: self.create_project())
        self.create_project_button.clicked.connect(lambda: self.set_to_newly_created_project())
        self.create_project_button.clicked.connect(lambda: self.project_name_line_edit.clear())
        self.create_project_button.clicked.connect(lambda: self.scene_line_edit.clear())
        self.create_project_button.clicked.connect(lambda: self.shot_line_edit.clear())        

        self.create_project_layout.addWidget(self.create_project_label)        
        self.create_project_layout.addWidget(self.select_drive_combo_box)
        self.create_project_layout.addWidget(self.project_name_line_edit)
        self.create_project_layout.addWidget(self.create_project_button)
        
        # set project section
        self.set_project_label = QLabel('==== Select A Project ====')
        self.set_project_label.setFixedHeight(17*desktop_scaled)
        self.set_project_label.setAlignment(Qt.AlignLeft)

        self.current_project_combo_box = QComboBox()
        self.current_project_combo_box.setFixedWidth(170*desktop_scaled)
        self.current_project_combo_box.currentIndexChanged.connect(lambda: self.eval_get_current_project())
        self.current_project_combo_box.currentIndexChanged.connect(lambda: self.refresh_current_ui())

        self.refresh_button = QPushButton('REFRESH')
        self.refresh_button.setFixedWidth(170*desktop_scaled)
        self.refresh_button.setFixedHeight(24*desktop_scaled)

        #self.refresh_button.clicked.connect(lambda: self.get_current_project())  
        self.refresh_button.clicked.connect(lambda: self.eval_get_current_project())
        self.refresh_button.clicked.connect(lambda: self.refresh_current_ui())

        #self.track_button = QPushButton('TRACK DIRECTORY')
        #self.track_button.setFixedWidth(170)
        #self.track_button.setFixedHeight(24)

        self.set_project_layout.addWidget(self.set_project_label)
        self.set_project_layout.addWidget(self.current_project_combo_box)
        self.set_project_layout.addWidget(self.refresh_button) 
        #self.set_project_layout.addWidget(self.track_button)        
        
        # scene-shot section         
        self.scene_shot_label = QLabel('==== Record Scene-Shot Folders ====')
        self.scene_shot_label.setFixedHeight(17*desktop_scaled)
        self.scene_shot_label.setAlignment(Qt.AlignLeft)
        
        self.scene_line_edit = QLineEdit()
        self.scene_line_edit.setFixedWidth(177*desktop_scaled)  
        self.scene_line_edit.setFixedHeight(20*desktop_scaled)             
        self.scene_line_edit .setPlaceholderText('Scene numbers...')    
        self.scene_line_edit.returnPressed.connect(lambda: self.select_texts(self.scene_line_edit))
        
        self.shot_line_edit = QLineEdit()
        self.shot_line_edit.setFixedWidth(177*desktop_scaled)    
        self.shot_line_edit.setFixedHeight(20*desktop_scaled)          
        self.shot_line_edit .setPlaceholderText('Shot amounts...')  
        self.shot_line_edit.returnPressed.connect(lambda: self.select_texts(self.shot_line_edit))
     
        self.record_button = QPushButton('Record Scene-Shot')        
        self.record_button.setFixedWidth(178*desktop_scaled)
        self.record_button.setFixedHeight(24*desktop_scaled)
        self.record_button.clicked.connect(lambda: initial_shot_dict())
 
        self.init_scene_layout.addWidget(self.scene_shot_label)
        self.init_scene_layout.addWidget(self.scene_line_edit)        
        self.init_scene_layout.addWidget(self.shot_line_edit) 
        self.init_scene_layout.addWidget(self.record_button) 
 
        # container that holds the UI widgets in "create_shot_tab"
        self.create_shot_tab_widgets = {}
 
        # container that holds the UI widgets in "create_design_tab"        
        self.create_design_tab_widgets = {}

        # container that holds the UI widgets in "create_asset_tab"        
        self.create_asset_tab_widgets = {}        
 
        
        self.folder_type_directories_dict = {   'Character_Design':             'self.current_project.get_char_design_dir()',
                                                'Props_Design':                 'self.current_project.get_props_design_dir()',
                                                'Environment_Design':           'self.current_project.get_env_design_dir()',
                                                '2D_Continuities':              'self.current_project.get_2d_continuities_dir()',

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
        self.design_categories = ['Character_Design', 'Props_Design', 'Environment_Design', '2D_Continuities']
        
        for single_design_tab in self.design_categories:
            design_type = single_design_tab
            treeView1 = single_design_tab + '_treeView1'
            model1 = single_design_tab + '_model1'
            treeView2 = single_design_tab + '_treeView2'
            model2 = single_design_tab + '_model2'
            lineEdit = single_design_tab + '_line_edit'            
            button1 = single_design_tab + '_button1'
            button2 = single_design_tab + '_button2'            
            self.create_design_tab(design_type, self.design_widget, treeView1, model1, treeView2, model2, lineEdit, button1, button2)            

        self.create_design_tab_widgets['Character_Design_treeView2']    .doubleClicked.connect  (lambda: self.open_file_in_design_tabs('Character_Design'))
        self.create_design_tab_widgets['Props_Design_treeView2']        .doubleClicked.connect  (lambda: self.open_file_in_design_tabs('Props_Design'))
        self.create_design_tab_widgets['Environment_Design_treeView2']  .doubleClicked.connect  (lambda: self.open_file_in_design_tabs('Environment_Design'))
        self.create_design_tab_widgets['2D_Continuities_treeView2']     .doubleClicked.connect  (lambda: self.open_file_in_design_tabs('2D_Continuities'))

        self.create_design_tab_widgets['Character_Design_button1']      .clicked.connect        (lambda: self.create_folder_button('Character_Design',       self.create_design_tab_widgets))
        self.create_design_tab_widgets['Props_Design_button1']          .clicked.connect        (lambda: self.create_folder_button('Props_Design',           self.create_design_tab_widgets))
        self.create_design_tab_widgets['Environment_Design_button1']    .clicked.connect        (lambda: self.create_folder_button('Environment_Design',     self.create_design_tab_widgets))
        self.create_design_tab_widgets['2D_Continuities_button1']       .clicked.connect        (lambda: self.create_folder_button('2D_Continuities',        self.create_design_tab_widgets))                        

        self.create_design_tab_widgets['Character_Design_button2']      .clicked.connect        (lambda: self.open_file_in_explorer_design_tabs('Character_Design'))
        self.create_design_tab_widgets['Props_Design_button2']          .clicked.connect        (lambda: self.open_file_in_explorer_design_tabs('Props_Design'))
        self.create_design_tab_widgets['Environment_Design_button2']    .clicked.connect        (lambda: self.open_file_in_explorer_design_tabs('Environment_Design'))
        self.create_design_tab_widgets['2D_Continuities_button2']       .clicked.connect        (lambda: self.open_file_in_explorer_design_tabs('2D_Continuities'))

        self.refresh_tabwidget(self.design_widget)

        # create elements for ASSET section
        self.dict_asset = {'1_MODEL':       ['CHARACTER', 'PROPS', 'COMPONENT', 'ENVIRONMENT'],
                           '2_RIG':         ['CHARACTER', 'PROPS'],
                           '3_SURFACING':   ['SHADER', 'TEXTURE'],
                           '4_TEMPLATES':   ['CHARACTER', 'ENVIRONMENT','RENDERING']}     
                                  
        self.dict_asset_file_utility_widgets = self.create_asset_buttons_widgets(self.asset_widget, self.dict_asset )

        for asset_type in self.dict_asset_file_utility_widgets.keys():
            if asset_type == '1_MODEL':
                # self.dict_asset_file_utility_widgets[asset_type] is a sub-level dictionary
                for sub_type in self.dict_asset_file_utility_widgets[asset_type].keys():
                    
                    # self.dict_asset_file_utility_widgets[asset_type][sub_type] should return a desired parent layout
                    parent_layout = self.dict_asset_file_utility_widgets[asset_type][sub_type] 

                    section_names = ['HIGH-RESOLUTION', 'LOW-RESOLUTION']

                    treeView1   =   sub_type + '_treeView1'
                    model1      =   sub_type + '_model1'
                    treeView2   =   sub_type + '_treeView2'
                    model2      =   sub_type + '_model2'
                    treeView3   =   sub_type + '_treeView3'
                    model3      =   sub_type + '_model3'                    
                    self.asset_file_section(treeView1, model1, treeView2, model2, treeView3, model3, parent_layout, section_names, 670)

                    lineEdit1   = '1_MODEL_' + sub_type + '_line_edit'
                    button1     = '1_MODEL_' + sub_type + '_button1' 
                    button2     = '1_MODEL_' + sub_type + '_button2' 
                    button4     = '1_MODEL_' + sub_type + '_button4'
                    lineEdit2   = '1_MODEL_' + sub_type + '_lineEdit2'
                    button5     = '1_MODEL_' + sub_type + '_button5'
                    button6     = '1_MODEL_' + sub_type + '_button6'
                    self.asset_utility_section(lineEdit1, button1, button2, button4, lineEdit2, button5, button6, parent_layout, 107, True, True, True)

            if asset_type == '2_RIG':
                # self.dict_asset_file_utility_widgets[asset_type] is a sub-level dictionary
                for sub_type in self.dict_asset_file_utility_widgets[asset_type].keys():

                    # self.dict_asset_file_utility_widgets[asset_type][sub_type] should return a desired parent layout
                    parent_layout = self.dict_asset_file_utility_widgets[asset_type][sub_type] 
                    section_names = ['RIGGED', 'DEFORMED']

                    treeView1   = sub_type + '_treeView1'
                    model1      = sub_type + '_model1'
                    treeView2   = sub_type + '_treeView2'
                    model2      = sub_type + '_model2'
                    treeView3   = sub_type + '_treeView3'
                    model3      = sub_type + '_model3'                                        
                    self.asset_file_section(treeView1, model1, treeView2, model2, treeView3, model3, parent_layout, section_names, 670)

                    lineEdit1   = '2_RIG_' + sub_type + '_lineEdit1'
                    button1     = '2_RIG_' + sub_type + '_button1' 
                    button2     = '2_RIG_' + sub_type + '_button2' 
                    button4     = '2_RIG_' + sub_type + '_button4'
                    lineEdit2   = '2_RIG_' + sub_type + '_lineEdit2'
                    button5     = '2_RIG_' + sub_type + '_button5'
                    button6     = '2_RIG_' + sub_type + '_button6'
                    self.asset_utility_section(lineEdit1, button1, button2, button4, lineEdit2, button5, button6, parent_layout, 107, False, True, True)                

            if asset_type == '3_SURFACING':
                # self.dict_asset_file_utility_widgets[asset_type] is a sub-level dictionary
                for sub_type in self.dict_asset_file_utility_widgets[asset_type].keys():
                    # self.dict_asset_file_utility_widgets[asset_type][sub_type] should return a desired parent layout
                    parent_layout = self.dict_asset_file_utility_widgets[asset_type][sub_type]                     
                    section_names = ['CHARACTER', 'PROPS', 'COMPONENT']

                    treeView1   = sub_type + '_treeView1'
                    model1      = sub_type + '_model1'
                    treeView2   = sub_type + '_treeView2'
                    model2      = sub_type + '_model2'
                    treeView3   = sub_type + '_treeView3'
                    model3      = sub_type + '_model3'                                        
                    self.asset_file_section(treeView1, model1, treeView2, model2, treeView3, model3, parent_layout, section_names, 670)
                    
                    lineEdit1   = '3_SURFACING_' + sub_type + '_lineEdit1'
                    button1     = '3_SURFACING_' + sub_type + '_button1' 
                    button2     = '3_SURFACING_' + sub_type + '_button2' 
                    button4     = '3_SURFACING_' + sub_type + '_button4'
                    lineEdit2   = '3_SURFACING_' + sub_type + '_lineEdit2'
                    button5     = '3_SURFACING_' + sub_type + '_button5'
                    button6     = '3_SURFACING_' + sub_type + '_button6'

                    if sub_type != 'TEXTURE':
                        self.asset_utility_section(lineEdit1, button1, button2, button4, lineEdit2, button5, button6, parent_layout, 107, False, False, True)
                    else:
                        self.asset_utility_section(lineEdit1, button1, button2, button4, lineEdit2, button5, button6, parent_layout, 107, False, False, False)

            if asset_type == '4_TEMPLATES':
                # self.dict_asset_file_utility_widgets[asset_type] is a sub-level dictionary
                for sub_type in self.dict_asset_file_utility_widgets[asset_type].keys():
                    # self.dict_asset_file_utility_widgets[asset_type][sub_type] should return a desired parent layout
                    parent_layout = self.dict_asset_file_utility_widgets[asset_type][sub_type] 
                    section_names = ['TEMPLATE']

                    treeView1   = sub_type + '_treeView1'
                    model1      = sub_type + '_model1'
                    treeView2   = sub_type + '_treeView2'
                    model2      = sub_type + '_model2'
                    treeView3   = sub_type + '_treeView3'
                    model3      = sub_type + '_model3'     
                    self.asset_file_section(treeView1, model1, treeView2, model2, treeView3, model3, parent_layout, section_names, 670)

                    lineEdit1   = '4_TEMPLATES_' + sub_type + '_line_edit'
                    button1     = '4_TEMPLATES_' + sub_type + '_button1' 
                    button2     = '4_TEMPLATES_' + sub_type + '_button2' 
                    button4     = '4_TEMPLATES_' + sub_type + '_button4'
                    lineEdit2   = '4_TEMPLATES_' + sub_type + '_lineEdit2'
                    button5     = '4_TEMPLATES_' + sub_type + '_button5'
                    button6     = '4_TEMPLATES_' + sub_type + '_button6'
                    self.asset_utility_section(lineEdit1, button1, button2, button4, lineEdit2, button5, button6, parent_layout, 107, True, False, True)    

        #pprint(self.create_asset_tab_widgets)

        self.create_asset_tab_widgets['1_MODEL_CHARACTER_button1']                  .clicked.connect    ( lambda: self.create_folder_button('1_MODEL_CHARACTER',      self.create_asset_tab_widgets))
        self.create_asset_tab_widgets['1_MODEL_PROPS_button1']                      .clicked.connect    ( lambda: self.create_folder_button('1_MODEL_PROPS',          self.create_asset_tab_widgets))
        self.create_asset_tab_widgets['1_MODEL_COMPONENT_button1']                  .clicked.connect    ( lambda: self.create_folder_button('1_MODEL_COMPONENT',      self.create_asset_tab_widgets))
        self.create_asset_tab_widgets['1_MODEL_ENVIRONMENT_button1']                .clicked.connect    ( lambda: self.create_folder_button('1_MODEL_ENVIRONMENT',    self.create_asset_tab_widgets))

        self.create_asset_tab_widgets['4_TEMPLATES_RENDERING_button1']              .clicked.connect    ( lambda: self.create_folder_button('4_TEMPLATES_RENDERING',    self.create_asset_tab_widgets))
        self.create_asset_tab_widgets['4_TEMPLATES_ENVIRONMENT_button1']            .clicked.connect    ( lambda: self.create_folder_button('4_TEMPLATES_ENVIRONMENT',    self.create_asset_tab_widgets))
        self.create_asset_tab_widgets['4_TEMPLATES_CHARACTER_button1']              .clicked.connect    ( lambda: self.create_folder_button('4_TEMPLATES_CHARACTER',    self.create_asset_tab_widgets))

        self.create_asset_tab_widgets['1_MODEL_CHARACTER_button2']                  .clicked.connect    ( lambda: self.create_new_variation(self.create_asset_tab_widgets, 'HIGH-RESOLUTION_CHARACTER',       'LOW-RESOLUTION_CHARACTER'))
        self.create_asset_tab_widgets['1_MODEL_PROPS_button2']                      .clicked.connect    ( lambda: self.create_new_variation(self.create_asset_tab_widgets, 'HIGH-RESOLUTION_PROPS',           'LOW-RESOLUTION_PROPS'))
        self.create_asset_tab_widgets['1_MODEL_COMPONENT_button2']                  .clicked.connect    ( lambda: self.create_new_variation(self.create_asset_tab_widgets, 'HIGH-RESOLUTION_COMPONENT',       'LOW-RESOLUTION_COMPONENT'))
        self.create_asset_tab_widgets['1_MODEL_ENVIRONMENT_button2']                .clicked.connect    ( lambda: self.create_new_variation(self.create_asset_tab_widgets, 'HIGH-RESOLUTION_ENVIRONMENT',     'LOW-RESOLUTION_ENVIRONMENT'))
        self.create_asset_tab_widgets['2_RIG_CHARACTER_button2']                    .clicked.connect    ( lambda: self.create_new_variation(self.create_asset_tab_widgets, 'RIGGED_CHARACTER',                'DEFORMED_CHARACTER'))
        self.create_asset_tab_widgets['2_RIG_PROPS_button2']                        .clicked.connect    ( lambda: self.create_new_variation(self.create_asset_tab_widgets, 'RIGGED_PROPS',                    'DEFORMED_PROPS'))
        self.create_asset_tab_widgets['3_SURFACING_SHADER_button2']                 .clicked.connect    ( lambda: self.create_new_variation(self.create_asset_tab_widgets, 'CHARACTER_SHADER',                'COMPONENT_SHADER',     'PROPS_SHADER'))
        self.create_asset_tab_widgets['4_TEMPLATES_CHARACTER_button2']              .clicked.connect    ( lambda: self.create_new_variation(self.create_asset_tab_widgets, 'TEMPLATE_CHARACTER'))
        self.create_asset_tab_widgets['4_TEMPLATES_ENVIRONMENT_button2']            .clicked.connect    ( lambda: self.create_new_variation(self.create_asset_tab_widgets, 'TEMPLATE_ENVIRONMENT'))

        self.create_asset_tab_widgets['1_MODEL_CHARACTER_button4']                  .clicked.connect    ( lambda: self.set_active(self.create_asset_tab_widgets, 'HIGH-RESOLUTION_CHARACTER',         'LOW-RESOLUTION_CHARACTER'))
        self.create_asset_tab_widgets['1_MODEL_PROPS_button4']                      .clicked.connect    ( lambda: self.set_active(self.create_asset_tab_widgets, 'HIGH-RESOLUTION_PROPS',             'LOW-RESOLUTION_PROPS'))
        self.create_asset_tab_widgets['1_MODEL_COMPONENT_button4']                  .clicked.connect    ( lambda: self.set_active(self.create_asset_tab_widgets, 'HIGH-RESOLUTION_COMPONENT',         'LOW-RESOLUTION_COMPONENT'))
        self.create_asset_tab_widgets['1_MODEL_ENVIRONMENT_button4']                .clicked.connect    ( lambda: self.set_active(self.create_asset_tab_widgets, 'HIGH-RESOLUTION_ENVIRONMENT',       'LOW-RESOLUTION_ENVIRONMENT'))
        self.create_asset_tab_widgets['2_RIG_CHARACTER_button4']                    .clicked.connect    ( lambda: self.set_active(self.create_asset_tab_widgets, 'RIGGED_CHARACTER',                  'DEFORMED_CHARACTER'))
        self.create_asset_tab_widgets['2_RIG_PROPS_button4']                        .clicked.connect    ( lambda: self.set_active(self.create_asset_tab_widgets, 'RIGGED_PROPS',                      'DEFORMED_PROPS'))
        self.create_asset_tab_widgets['3_SURFACING_SHADER_button4']                 .clicked.connect    ( lambda: self.set_active(self.create_asset_tab_widgets, 'CHARACTER_SHADER',                  'COMPONENT_SHADER',     'PROPS_SHADER'))
        self.create_asset_tab_widgets['4_TEMPLATES_CHARACTER_button4']              .clicked.connect    ( lambda: self.set_active(self.create_asset_tab_widgets, 'TEMPLATE_CHARACTER'))        
        self.create_asset_tab_widgets['4_TEMPLATES_ENVIRONMENT_button4']            .clicked.connect    ( lambda: self.set_active(self.create_asset_tab_widgets, 'TEMPLATE_ENVIRONMENT'))
        
        self.create_asset_tab_widgets['1_MODEL_CHARACTER_button5']                  .clicked.connect    ( lambda: self.reference_maya_file_button(self.create_asset_tab_widgets, 'HIGH-RESOLUTION_CHARACTER',         'LOW-RESOLUTION_CHARACTER'))
        self.create_asset_tab_widgets['1_MODEL_PROPS_button5']                      .clicked.connect    ( lambda: self.reference_maya_file_button(self.create_asset_tab_widgets, 'HIGH-RESOLUTION_PROPS',             'LOW-RESOLUTION_PROPS'))
        self.create_asset_tab_widgets['1_MODEL_COMPONENT_button5']                  .clicked.connect    ( lambda: self.reference_maya_file_button(self.create_asset_tab_widgets, 'HIGH-RESOLUTION_COMPONENT',         'LOW-RESOLUTION_COMPONENT'))
        self.create_asset_tab_widgets['1_MODEL_ENVIRONMENT_button5']                .clicked.connect    ( lambda: self.reference_maya_file_button(self.create_asset_tab_widgets, 'HIGH-RESOLUTION_ENVIRONMENT',       'LOW-RESOLUTION_ENVIRONMENT'))
        self.create_asset_tab_widgets['2_RIG_CHARACTER_button5']                    .clicked.connect    ( lambda: self.reference_maya_file_button(self.create_asset_tab_widgets, 'RIGGED_CHARACTER',                  'DEFORMED_CHARACTER'))
        self.create_asset_tab_widgets['2_RIG_PROPS_button5']                        .clicked.connect    ( lambda: self.reference_maya_file_button(self.create_asset_tab_widgets, 'RIGGED_PROPS',                      'DEFORMED_PROPS'))
        self.create_asset_tab_widgets['3_SURFACING_SHADER_button5']                 .clicked.connect    ( lambda: self.reference_maya_file_button(self.create_asset_tab_widgets, 'CHARACTER_SHADER',                  'COMPONENT_SHADER',     'PROPS_SHADER'))
        self.create_asset_tab_widgets['4_TEMPLATES_CHARACTER_button5']              .clicked.connect    ( lambda: self.reference_maya_file_button(self.create_asset_tab_widgets, 'TEMPLATE_CHARACTER'))        
        self.create_asset_tab_widgets['4_TEMPLATES_ENVIRONMENT_button5']            .clicked.connect    ( lambda: self.reference_maya_file_button(self.create_asset_tab_widgets, 'TEMPLATE_ENVIRONMENT'))

        self.create_asset_tab_widgets['1_MODEL_CHARACTER_button6']                  .clicked.connect    ( lambda: self.open_maya_file_button(self.create_asset_tab_widgets, 'HIGH-RESOLUTION_CHARACTER',         'LOW-RESOLUTION_CHARACTER'))
        self.create_asset_tab_widgets['1_MODEL_PROPS_button6']                      .clicked.connect    ( lambda: self.open_maya_file_button(self.create_asset_tab_widgets, 'HIGH-RESOLUTION_PROPS',             'LOW-RESOLUTION_PROPS'))
        self.create_asset_tab_widgets['1_MODEL_COMPONENT_button6']                  .clicked.connect    ( lambda: self.open_maya_file_button(self.create_asset_tab_widgets, 'HIGH-RESOLUTION_COMPONENT',         'LOW-RESOLUTION_COMPONENT'))
        self.create_asset_tab_widgets['1_MODEL_ENVIRONMENT_button6']                .clicked.connect    ( lambda: self.open_maya_file_button(self.create_asset_tab_widgets, 'HIGH-RESOLUTION_ENVIRONMENT',       'LOW-RESOLUTION_ENVIRONMENT'))
        self.create_asset_tab_widgets['2_RIG_CHARACTER_button6']                    .clicked.connect    ( lambda: self.open_maya_file_button(self.create_asset_tab_widgets, 'RIGGED_CHARACTER',                  'DEFORMED_CHARACTER'))
        self.create_asset_tab_widgets['2_RIG_PROPS_button6']                        .clicked.connect    ( lambda: self.open_maya_file_button(self.create_asset_tab_widgets, 'RIGGED_PROPS',                      'DEFORMED_PROPS'))
        self.create_asset_tab_widgets['3_SURFACING_SHADER_button6']                 .clicked.connect    ( lambda: self.open_maya_file_button(self.create_asset_tab_widgets, 'CHARACTER_SHADER',                  'COMPONENT_SHADER',     'PROPS_SHADER'))
        self.create_asset_tab_widgets['4_TEMPLATES_CHARACTER_button6']              .clicked.connect    ( lambda: self.open_maya_file_button(self.create_asset_tab_widgets, 'TEMPLATE_CHARACTER'))        
        self.create_asset_tab_widgets['4_TEMPLATES_ENVIRONMENT_button6']            .clicked.connect    ( lambda: self.open_maya_file_button(self.create_asset_tab_widgets, 'TEMPLATE_ENVIRONMENT'))

        self.create_asset_tab_widgets['CHARACTER_SHADER_treeView2']                 .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['3_SURFACING_SHADER_button2'],       True,   self.create_asset_tab_widgets['3_SURFACING_SHADER_button4'],        False))
        self.create_asset_tab_widgets['CHARACTER_SHADER_treeView3']                 .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['3_SURFACING_SHADER_button2'],       False,  self.create_asset_tab_widgets['3_SURFACING_SHADER_button4'],        True))
        self.create_asset_tab_widgets['CHARACTER_TEXTURE_treeView2']                .clicked.connect    ( lambda: self.sel_file_activate_button_fx( self.create_asset_tab_widgets['3_SURFACING_TEXTURE_button2'],     True,   self.create_asset_tab_widgets['3_SURFACING_TEXTURE_button4',        False]))
        self.create_asset_tab_widgets['CHARACTER_TEXTURE_treeView3']                .clicked.connect    ( lambda: self.sel_file_activate_button_fx( self.create_asset_tab_widgets['3_SURFACING_TEXTURE_button2'],     False,  self.create_asset_tab_widgets['3_SURFACING_TEXTURE_button4'],       True))
        self.create_asset_tab_widgets['DEFORMED_CHARACTER_treeView2']               .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['2_RIG_CHARACTER_button2'],          True,   self.create_asset_tab_widgets['2_RIG_CHARACTER_button4'],           False))
        self.create_asset_tab_widgets['DEFORMED_CHARACTER_treeView3']               .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['2_RIG_CHARACTER_button2'],          False,  self.create_asset_tab_widgets['2_RIG_CHARACTER_button4'],           True))
        self.create_asset_tab_widgets['HIGH-RESOLUTION_CHARACTER_treeView2']        .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['1_MODEL_CHARACTER_button2'],        True,   self.create_asset_tab_widgets['1_MODEL_CHARACTER_button4'],         False))
        self.create_asset_tab_widgets['HIGH-RESOLUTION_CHARACTER_treeView3']        .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['1_MODEL_CHARACTER_button2'],        False,  self.create_asset_tab_widgets['1_MODEL_CHARACTER_button4'],         True))
        self.create_asset_tab_widgets['HIGH-RESOLUTION_COMPONENT_treeView2']        .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['1_MODEL_COMPONENT_button2'],        True,   self.create_asset_tab_widgets['1_MODEL_COMPONENT_button4'],         False))
        self.create_asset_tab_widgets['HIGH-RESOLUTION_COMPONENT_treeView3']        .clicked.connect    ( lambda: self.sel_file_activate_button_fx( self.create_asset_tab_widgets['1_MODEL_COMPONENT_button2'],       False,  self.create_asset_tab_widgets['1_MODEL_COMPONENT_button4'],         True))
        self.create_asset_tab_widgets['HIGH-RESOLUTION_ENVIRONMENT_treeView2']      .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['1_MODEL_ENVIRONMENT_button2'],      True,   self.create_asset_tab_widgets['1_MODEL_ENVIRONMENT_button4'],       False))
        self.create_asset_tab_widgets['HIGH-RESOLUTION_ENVIRONMENT_treeView3']      .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['1_MODEL_ENVIRONMENT_button2'],      False,  self.create_asset_tab_widgets['1_MODEL_ENVIRONMENT_button4'],       True))
        self.create_asset_tab_widgets['HIGH-RESOLUTION_PROPS_treeView2']            .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['1_MODEL_PROPS_button2'],            True,   self.create_asset_tab_widgets['1_MODEL_PROPS_button4'],             False))
        self.create_asset_tab_widgets['HIGH-RESOLUTION_PROPS_treeView3']            .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['1_MODEL_PROPS_button2'],            False,  self.create_asset_tab_widgets['1_MODEL_PROPS_button4'],             True))
        self.create_asset_tab_widgets['LOW-RESOLUTION_CHARACTER_treeView2']         .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['1_MODEL_CHARACTER_button2'],        True,   self.create_asset_tab_widgets['1_MODEL_CHARACTER_button4'],         False))
        self.create_asset_tab_widgets['LOW-RESOLUTION_CHARACTER_treeView3']         .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['1_MODEL_CHARACTER_button2'],        False,  self.create_asset_tab_widgets['1_MODEL_CHARACTER_button4'],         True))
        self.create_asset_tab_widgets['LOW-RESOLUTION_COMPONENT_treeView2']         .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['1_MODEL_COMPONENT_button2'],        True,   self.create_asset_tab_widgets['1_MODEL_COMPONENT_button4'],         False))
        self.create_asset_tab_widgets['LOW-RESOLUTION_COMPONENT_treeView3']         .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['1_MODEL_COMPONENT_button2'],        False,  self.create_asset_tab_widgets['1_MODEL_COMPONENT_button4'],         True))
        self.create_asset_tab_widgets['LOW-RESOLUTION_ENVIRONMENT_treeView2']       .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['1_MODEL_ENVIRONMENT_button2'],      True,   self.create_asset_tab_widgets['1_MODEL_ENVIRONMENT_button4'],       False))
        self.create_asset_tab_widgets['LOW-RESOLUTION_ENVIRONMENT_treeView3']       .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['1_MODEL_ENVIRONMENT_button2'],      False,  self.create_asset_tab_widgets['1_MODEL_ENVIRONMENT_button4'],       True))
        self.create_asset_tab_widgets['LOW-RESOLUTION_PROPS_treeView2']             .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['1_MODEL_PROPS_button2'],            True,   self.create_asset_tab_widgets['1_MODEL_PROPS_button4'],             False))
        self.create_asset_tab_widgets['LOW-RESOLUTION_PROPS_treeView3']             .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['1_MODEL_PROPS_button2'],            False,  self.create_asset_tab_widgets['1_MODEL_PROPS_button4'],             True))
        self.create_asset_tab_widgets['PROPS_SHADER_treeView2']                     .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['3_SURFACING_SHADER_button2'],       True,   self.create_asset_tab_widgets['3_SURFACING_SHADER_button4'],        False))
        self.create_asset_tab_widgets['PROPS_SHADER_treeView3']                     .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['3_SURFACING_SHADER_button2'],       False,  self.create_asset_tab_widgets['3_SURFACING_SHADER_button4'],        True))
        self.create_asset_tab_widgets['RIGGED_CHARACTER_treeView2']                 .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['2_RIG_PROPS_button2'],              True,   self.create_asset_tab_widgets['2_RIG_PROPS_button4'],               False))
        self.create_asset_tab_widgets['RIGGED_CHARACTER_treeView3']                 .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['2_RIG_PROPS_button2'],              False,  self.create_asset_tab_widgets['2_RIG_PROPS_button4'],               True))
        self.create_asset_tab_widgets['TEMPLATE_CHARACTER_treeView2']               .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['4_TEMPLATES_CHARACTER_button2'],    True,   self.create_asset_tab_widgets['4_TEMPLATES_CHARACTER_button4'],     False))
        self.create_asset_tab_widgets['TEMPLATE_CHARACTER_treeView3']               .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['4_TEMPLATES_CHARACTER_button2'],    False,  self.create_asset_tab_widgets['4_TEMPLATES_CHARACTER_button4'],     True))
        self.create_asset_tab_widgets['TEMPLATE_ENVIRONMENT_treeView2']             .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['4_TEMPLATES_ENVIRONMENT_button2'],  True,   self.create_asset_tab_widgets['4_TEMPLATES_ENVIRONMENT_button4'],   False))
        self.create_asset_tab_widgets['TEMPLATE_ENVIRONMENT_treeView3']             .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_asset_tab_widgets['4_TEMPLATES_ENVIRONMENT_button2'],  False,  self.create_asset_tab_widgets['4_TEMPLATES_ENVIRONMENT_button4'],   True))

        self.create_asset_tab_widgets['CHARACTER_SHADER_treeView2']                 .clicked.connect    ( lambda: self.create_asset_tab_widgets['3_SURFACING_SHADER_button5'].setEnabled(True) )
        self.create_asset_tab_widgets['CHARACTER_SHADER_treeView3']                 .clicked.connect    ( lambda: self.create_asset_tab_widgets['3_SURFACING_SHADER_button5'].setEnabled(False))
        self.create_asset_tab_widgets['DEFORMED_CHARACTER_treeView2']               .clicked.connect    ( lambda: self.create_asset_tab_widgets['2_RIG_CHARACTER_button5'].setEnabled(True) )
        self.create_asset_tab_widgets['DEFORMED_CHARACTER_treeView3']               .clicked.connect    ( lambda: self.create_asset_tab_widgets['2_RIG_CHARACTER_button5'].setEnabled(False))
        self.create_asset_tab_widgets['HIGH-RESOLUTION_CHARACTER_treeView2']        .clicked.connect    ( lambda: self.create_asset_tab_widgets['1_MODEL_CHARACTER_button5'].setEnabled(True) )
        self.create_asset_tab_widgets['HIGH-RESOLUTION_CHARACTER_treeView3']        .clicked.connect    ( lambda: self.create_asset_tab_widgets['1_MODEL_CHARACTER_button5'].setEnabled(False))
        self.create_asset_tab_widgets['HIGH-RESOLUTION_COMPONENT_treeView2']        .clicked.connect    ( lambda: self.create_asset_tab_widgets['1_MODEL_COMPONENT_button5'].setEnabled(True) )
        self.create_asset_tab_widgets['HIGH-RESOLUTION_COMPONENT_treeView3']        .clicked.connect    ( lambda: self.create_asset_tab_widgets['1_MODEL_COMPONENT_button5'].setEnabled(False))
        self.create_asset_tab_widgets['HIGH-RESOLUTION_ENVIRONMENT_treeView2']      .clicked.connect    ( lambda: self.create_asset_tab_widgets['1_MODEL_ENVIRONMENT_button5'].setEnabled(True) )
        self.create_asset_tab_widgets['HIGH-RESOLUTION_ENVIRONMENT_treeView3']      .clicked.connect    ( lambda: self.create_asset_tab_widgets['1_MODEL_ENVIRONMENT_button5'].setEnabled(False))
        self.create_asset_tab_widgets['HIGH-RESOLUTION_PROPS_treeView2']            .clicked.connect    ( lambda: self.create_asset_tab_widgets['1_MODEL_PROPS_button5'].setEnabled(True) )
        self.create_asset_tab_widgets['HIGH-RESOLUTION_PROPS_treeView3']            .clicked.connect    ( lambda: self.create_asset_tab_widgets['1_MODEL_PROPS_button5'].setEnabled(False))
        self.create_asset_tab_widgets['LOW-RESOLUTION_CHARACTER_treeView2']         .clicked.connect    ( lambda: self.create_asset_tab_widgets['1_MODEL_CHARACTER_button5'].setEnabled(True) )
        self.create_asset_tab_widgets['LOW-RESOLUTION_CHARACTER_treeView3']         .clicked.connect    ( lambda: self.create_asset_tab_widgets['1_MODEL_CHARACTER_button5'].setEnabled(False))
        self.create_asset_tab_widgets['LOW-RESOLUTION_COMPONENT_treeView2']         .clicked.connect    ( lambda: self.create_asset_tab_widgets['1_MODEL_COMPONENT_button5'].setEnabled(True) )
        self.create_asset_tab_widgets['LOW-RESOLUTION_COMPONENT_treeView3']         .clicked.connect    ( lambda: self.create_asset_tab_widgets['1_MODEL_COMPONENT_button5'].setEnabled(False))
        self.create_asset_tab_widgets['LOW-RESOLUTION_ENVIRONMENT_treeView2']       .clicked.connect    ( lambda: self.create_asset_tab_widgets['1_MODEL_ENVIRONMENT_button5'].setEnabled(True) )
        self.create_asset_tab_widgets['LOW-RESOLUTION_ENVIRONMENT_treeView3']       .clicked.connect    ( lambda: self.create_asset_tab_widgets['1_MODEL_ENVIRONMENT_button5'].setEnabled(False))
        self.create_asset_tab_widgets['LOW-RESOLUTION_PROPS_treeView2']             .clicked.connect    ( lambda: self.create_asset_tab_widgets['1_MODEL_PROPS_button5'].setEnabled(True) )
        self.create_asset_tab_widgets['LOW-RESOLUTION_PROPS_treeView3']             .clicked.connect    ( lambda: self.create_asset_tab_widgets['1_MODEL_PROPS_button5'].setEnabled(False))
        self.create_asset_tab_widgets['PROPS_SHADER_treeView2']                     .clicked.connect    ( lambda: self.create_asset_tab_widgets['3_SURFACING_SHADER_button5'].setEnabled(True) )
        self.create_asset_tab_widgets['PROPS_SHADER_treeView3']                     .clicked.connect    ( lambda: self.create_asset_tab_widgets['3_SURFACING_SHADER_button5'].setEnabled(False))
        self.create_asset_tab_widgets['RIGGED_CHARACTER_treeView2']                 .clicked.connect    ( lambda: self.create_asset_tab_widgets['2_RIG_CHARACTER_button5'].setEnabled(True) )
        self.create_asset_tab_widgets['RIGGED_CHARACTER_treeView3']                 .clicked.connect    ( lambda: self.create_asset_tab_widgets['2_RIG_CHARACTER_button5'].setEnabled(False))
        self.create_asset_tab_widgets['TEMPLATE_CHARACTER_treeView2']               .clicked.connect    ( lambda: self.create_asset_tab_widgets['4_TEMPLATES_CHARACTER_button5'].setEnabled(True) )
        self.create_asset_tab_widgets['TEMPLATE_CHARACTER_treeView3']               .clicked.connect    ( lambda: self.create_asset_tab_widgets['4_TEMPLATES_CHARACTER_button5'].setEnabled(False))
        self.create_asset_tab_widgets['TEMPLATE_ENVIRONMENT_treeView2']             .clicked.connect    ( lambda: self.create_asset_tab_widgets['4_TEMPLATES_ENVIRONMENT_button5'].setEnabled(True) )
        self.create_asset_tab_widgets['TEMPLATE_ENVIRONMENT_treeView3']             .clicked.connect    ( lambda: self.create_asset_tab_widgets['4_TEMPLATES_ENVIRONMENT_button5'].setEnabled(False))


        # create elements for SHOT section
        self.shot_categories = ['Model', 'Layout', 'Layout_MOV', 'Animation', 'Animation_MOV', 'Anim_Cache', 'Lighting', 'VFX', 'VFX_Cache', 'Rendering']
        
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
            self.create_shot_tab(single_shot_tab, self.shot_widget, treeView1, model1, treeView2, model2, treeView3, model3, line_edit1, line_edit2, button1, button2, button3, button4, button5)            
        
        self.refresh_tabwidget(self.shot_widget)

        self.create_shot_tab_widgets['Animation_button2']           .clicked.connect    ( lambda: self.open_maya_file_button(self.create_shot_tab_widgets, 'Animation'))
        self.create_shot_tab_widgets['Layout_button2']              .clicked.connect    ( lambda: self.open_maya_file_button(self.create_shot_tab_widgets, 'Layout'))
        self.create_shot_tab_widgets['Lighting_button2']            .clicked.connect    ( lambda: self.open_maya_file_button(self.create_shot_tab_widgets, 'Lighting'))
        self.create_shot_tab_widgets['Model_button2']               .clicked.connect    ( lambda: self.open_maya_file_button(self.create_shot_tab_widgets, 'Model'))
        self.create_shot_tab_widgets['Rendering_button2']           .clicked.connect    ( lambda: self.open_maya_file_button(self.create_shot_tab_widgets, 'Rendering'))
        self.create_shot_tab_widgets['VFX_button2']                 .clicked.connect    ( lambda: self.open_maya_file_button(self.create_shot_tab_widgets, 'VFX'))

        self.create_shot_tab_widgets['Animation_button3']           .clicked.connect    ( lambda: self.reference_maya_file_button(self.create_shot_tab_widgets, 'Animation'))
        self.create_shot_tab_widgets['Layout_button3']              .clicked.connect    ( lambda: self.reference_maya_file_button(self.create_shot_tab_widgets, 'Layout'))
        self.create_shot_tab_widgets['Lighting_button3']            .clicked.connect    ( lambda: self.reference_maya_file_button(self.create_shot_tab_widgets, 'Lighting'))
        self.create_shot_tab_widgets['Model_button3']               .clicked.connect    ( lambda: self.reference_maya_file_button(self.create_shot_tab_widgets, 'Model'))
        self.create_shot_tab_widgets['Rendering_button3']           .clicked.connect    ( lambda: self.reference_maya_file_button(self.create_shot_tab_widgets, 'Rendering'))
        self.create_shot_tab_widgets['VFX_button3']                 .clicked.connect    ( lambda: self.reference_maya_file_button(self.create_shot_tab_widgets, 'VFX'))

        self.create_shot_tab_widgets['Animation_button4']           .clicked.connect    ( lambda: self.create_new_variation(self.create_shot_tab_widgets, 'Animation'))
        self.create_shot_tab_widgets['Layout_button4']              .clicked.connect    ( lambda: self.create_new_variation(self.create_shot_tab_widgets, 'Layout'))
        self.create_shot_tab_widgets['Lighting_button4']            .clicked.connect    ( lambda: self.create_new_variation(self.create_shot_tab_widgets, 'Lighting'))
        self.create_shot_tab_widgets['Model_button4']               .clicked.connect    ( lambda: self.create_new_variation(self.create_shot_tab_widgets, 'Model'))
        self.create_shot_tab_widgets['Rendering_button4']           .clicked.connect    ( lambda: self.create_new_variation(self.create_shot_tab_widgets, 'Rendering'))
        self.create_shot_tab_widgets['VFX_button4']                 .clicked.connect    ( lambda: self.create_new_variation(self.create_shot_tab_widgets, 'VFX'))

        self.create_shot_tab_widgets['Animation_button5']           .clicked.connect    ( lambda: self.set_active(self.create_shot_tab_widgets, 'Animation'))
        self.create_shot_tab_widgets['Layout_button5']              .clicked.connect    ( lambda: self.set_active(self.create_shot_tab_widgets, 'Layout'))
        self.create_shot_tab_widgets['Lighting_button5']            .clicked.connect    ( lambda: self.set_active(self.create_shot_tab_widgets, 'Lighting'))
        self.create_shot_tab_widgets['Model_button5']               .clicked.connect    ( lambda: self.set_active(self.create_shot_tab_widgets, 'Model'))
        self.create_shot_tab_widgets['Rendering_button5']           .clicked.connect    ( lambda: self.set_active(self.create_shot_tab_widgets, 'Rendering'))
        self.create_shot_tab_widgets['VFX_button5']                 .clicked.connect    ( lambda: self.set_active(self.create_shot_tab_widgets, 'VFX'))

        self.create_shot_tab_widgets['Animation_treeView2']         .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['Animation_button4'],         True,   self.create_shot_tab_widgets['Animation_button5'],      False))
        self.create_shot_tab_widgets['Animation_treeView3']         .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['Animation_button4'],         False,  self.create_shot_tab_widgets['Animation_button5'],      True))
        self.create_shot_tab_widgets['Layout_MOV_treeView2']        .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['Layout_MOV_button4'],        False,  self.create_shot_tab_widgets['Layout_MOV_button5'],     False))
        self.create_shot_tab_widgets['Layout_MOV_treeView3']        .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['Layout_MOV_button4'],        False,  self.create_shot_tab_widgets['Layout_MOV_button5'],     False))
        self.create_shot_tab_widgets['Animation_MOV_treeView2']     .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['Animation_MOV_button4'],     False,  self.create_shot_tab_widgets['Animation_MOV_button5'],  False))
        self.create_shot_tab_widgets['Animation_MOV_treeView3']     .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['Animation_MOV_button4'],     False,  self.create_shot_tab_widgets['Animation_MOV_button5'],  False))        
        self.create_shot_tab_widgets['Layout_treeView2']            .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['Layout_button4'],            True,   self.create_shot_tab_widgets['Layout_button5'],         False))
        self.create_shot_tab_widgets['Layout_treeView3']            .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['Layout_button4'],            False,  self.create_shot_tab_widgets['Layout_button5'],         True))
        self.create_shot_tab_widgets['Lighting_treeView2']          .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['Lighting_button4'],          True,   self.create_shot_tab_widgets['Lighting_button5'],       False))
        self.create_shot_tab_widgets['Lighting_treeView3']          .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['Lighting_button4'],          False,  self.create_shot_tab_widgets['Lighting_button5'],       True))
        self.create_shot_tab_widgets['Model_treeView2']             .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['Model_button4'],             True,   self.create_shot_tab_widgets['Model_button5'],          False))
        self.create_shot_tab_widgets['Model_treeView3']             .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['Model_button4'],             False,  self.create_shot_tab_widgets['Model_button5'],          True))
        self.create_shot_tab_widgets['Rendering_treeView2']         .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['Rendering_button4'],         True,   self.create_shot_tab_widgets['Rendering_button5'],      False))
        self.create_shot_tab_widgets['Rendering_treeView3']         .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['Rendering_button4'],         False,  self.create_shot_tab_widgets['Rendering_button5'],      True))
        self.create_shot_tab_widgets['VFX_treeView2']               .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['VFX_button4'],               True,   self.create_shot_tab_widgets['VFX_button5'],            False))
        self.create_shot_tab_widgets['VFX_treeView3']               .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['VFX_button4'],               False,  self.create_shot_tab_widgets['VFX_button5'],            True))

        self.create_shot_tab_widgets['Animation_treeView2']         .clicked.connect    ( lambda: self.create_shot_tab_widgets['Animation_button3'].setEnabled(True) )
        self.create_shot_tab_widgets['Animation_treeView3']         .clicked.connect    ( lambda: self.create_shot_tab_widgets['Animation_button3'].setEnabled(False) )
        self.create_shot_tab_widgets['Layout_treeView2']            .clicked.connect    ( lambda: self.create_shot_tab_widgets['Layout_button3'].setEnabled(True) )
        self.create_shot_tab_widgets['Layout_treeView3']            .clicked.connect    ( lambda: self.create_shot_tab_widgets['Layout_button3'].setEnabled(False) )
        self.create_shot_tab_widgets['Lighting_treeView2']          .clicked.connect    ( lambda: self.create_shot_tab_widgets['Lighting_button3'].setEnabled(True) )
        self.create_shot_tab_widgets['Lighting_treeView3']          .clicked.connect    ( lambda: self.create_shot_tab_widgets['Lighting_button3'].setEnabled(False) )
        self.create_shot_tab_widgets['Model_treeView2']             .clicked.connect    ( lambda: self.create_shot_tab_widgets['Model_button3'].setEnabled(True) )
        self.create_shot_tab_widgets['Model_treeView3']             .clicked.connect    ( lambda: self.create_shot_tab_widgets['Model_button3'].setEnabled(False) )
        self.create_shot_tab_widgets['Rendering_treeView2']         .clicked.connect    ( lambda: self.create_shot_tab_widgets['Rendering_button3'].setEnabled(True) )
        self.create_shot_tab_widgets['Rendering_treeView3']         .clicked.connect    ( lambda: self.create_shot_tab_widgets['Rendering_button3'].setEnabled(False) )
        self.create_shot_tab_widgets['VFX_treeView2']               .clicked.connect    ( lambda: self.create_shot_tab_widgets['VFX_button3'].setEnabled(True) )
        self.create_shot_tab_widgets['VFX_treeView3']               .clicked.connect    ( lambda: self.create_shot_tab_widgets['VFX_button3'].setEnabled(False) )
        
        self.create_shot_tab_widgets['Anim_Cache_treeView2']        .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['Anim_Cache_button4'],        False,  self.create_shot_tab_widgets['Anim_Cache_button5'],     False))
        self.create_shot_tab_widgets['Anim_Cache_treeView3']        .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['Anim_Cache_button4'],        False,  self.create_shot_tab_widgets['Anim_Cache_button5'],     False))
        self.create_shot_tab_widgets['VFX_Cache_treeView2']         .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['VFX_Cache_button4'],         False,  self.create_shot_tab_widgets['VFX_Cache_button5'],      False))
        self.create_shot_tab_widgets['VFX_Cache_treeView3']         .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['VFX_Cache_button4'],         False,  self.create_shot_tab_widgets['VFX_Cache_button5'],      False))

        self.create_shot_tab_widgets['Layout_MOV_treeView2']        .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['Layout_MOV_button1'],        False,  self.create_shot_tab_widgets['Layout_MOV_button3'],     False))
        self.create_shot_tab_widgets['Layout_MOV_treeView3']        .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['Layout_MOV_button1'],        False,  self.create_shot_tab_widgets['Layout_MOV_button3'],     False))
        self.create_shot_tab_widgets['Animation_MOV_treeView2']     .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['Animation_MOV_button1'],     False,  self.create_shot_tab_widgets['Animation_MOV_button3'],  False))
        self.create_shot_tab_widgets['Animation_MOV_treeView3']     .clicked.connect    ( lambda: self.sel_file_activate_button_fx(self.create_shot_tab_widgets['Animation_MOV_button1'],     False,  self.create_shot_tab_widgets['Animation_MOV_button3'],  False))        

        #pprint(self.create_shot_tab_widgets)

        # show the version information 
        self.about_app_widget = QWidget()
        self.about_app_widget.setFixedHeight(30*desktop_scaled)
        self.about_app_widget.setFixedWidth(1077*desktop_scaled)

        self.about_app_layout = QHBoxLayout(self.about_app_widget)
        self.about_app_layout.setAlignment(Qt.AlignCenter)
    
        self.ver_info_label = QLabel(ver_info)
        self.ver_info_label.setAlignment(Qt.AlignCenter)
        self.author_info_label = QLabel(author_info)
        self.author_info_label.setAlignment(Qt.AlignCenter)
        
        self.about_app_layout.addWidget(self.author_info_label)
        self.about_app_layout.addWidget(self.ver_info_label)        
        
        self.main_layout.addWidget(self.about_app_widget)
        
        # set the miscellaneous attributes
        self.setFixedHeight(1007*desktop_scaled)
        self.setFixedWidth(1077*desktop_scaled)

        self.setLayout(self.main_layout)

        self.setWindowFlags(Qt.Window)
        self.setWindowTitle('PROJECT FILE MANAGER')
        
        self.refresh_design_tabs_dict = { 0:        'self.populate_items_in_design_tab("Character_Design")', 
                                          1:        'self.populate_items_in_design_tab("Props_Design")',
                                          2:        'self.populate_items_in_design_tab("Environment_Design")',
                                          3:        'self.populate_items_in_design_tab("2D_Continuities")' }        

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
                                 1: 'self.refresh_asset_tabs_dict.get(self.get_asset_stacked_layout_current_index())',
                                 2: 'self.refresh_shot_tabs_dict.get(self.get_shots_tabs_current_index())' }        


        self.current_project = None

        self.track_project_directory = Track_Directory('p:/mov/')
        self.track_project_directory.start()
        

    def eval_get_current_project(self):        
        self.current_project = self.get_current_project()
        return self.current_project



    # ===============================================================
    # ======= implemment the 'template' of the 2D-Drawing Tab =======
    # ===============================================================

    def create_design_tab(self, design_type, parent_tab_widget, treeView1, model1, treeView2, model2, lineEdit, button1, button2):    
        self.design_type_tab = QWidget()
        self.design_type_tab.setFixedHeight(770*desktop_scaled)
        self.design_type_tab_layout = QHBoxLayout(self.design_type_tab )
        parent_tab_widget.addTab(self.design_type_tab, design_type.upper())
                       
        self.design_type_utilities_widget = QWidget()
        self.design_type_utilities_layout = QFormLayout(self.design_type_utilities_widget)                   
        
        self.design_type_folder_widget = QTreeWidget()
        self.design_type_folder_widget.setFixedHeight(730*desktop_scaled)
        self.design_type_folder_widget.setFixedWidth(407*desktop_scaled)    
        self.create_design_tab_widgets[treeView1] = QTreeView(self.design_type_folder_widget)
        self.create_design_tab_widgets[treeView1].setFixedHeight(730*desktop_scaled)
        self.create_design_tab_widgets[treeView1].setFixedWidth(407*desktop_scaled)   
        self.create_design_tab_widgets[treeView1].setSelectionBehavior(QAbstractItemView.SelectRows)
        self.create_design_tab_widgets[treeView1].setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.create_design_tab_widgets[model1] = QStandardItemModel()
        self.create_design_tab_widgets[model1].setHorizontalHeaderLabels(['>>> {} <<<'.format(design_type).upper()])  
        self.create_design_tab_widgets[treeView1].setModel(self.create_design_tab_widgets[model1])    
        #self.create_design_tab_widgets[treeView1].doubleClicked.connect(lambda: self.refresh_current_ui())
        #self.create_design_tab_widgets[treeView1].doubleClicked.connect(lambda: self.populate_items_in_design_tabs())
        
        self.design_type_file_widget = QTreeWidget()
        self.design_type_file_widget.setFixedHeight(730*desktop_scaled)
        self.design_type_file_widget.setFixedWidth(407*desktop_scaled)    
        self.create_design_tab_widgets[treeView2] = QTreeView(self.design_type_file_widget)
        self.create_design_tab_widgets[treeView2].setFixedHeight(730*desktop_scaled)
        self.create_design_tab_widgets[treeView2].setFixedWidth(407*desktop_scaled)   
        self.create_design_tab_widgets[treeView2].setSelectionBehavior(QAbstractItemView.SelectRows)
        self.create_design_tab_widgets[treeView2].setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.create_design_tab_widgets[model2] = QStandardItemModel()
        self.create_design_tab_widgets[model2].setHorizontalHeaderLabels(['>>> FILE <<<'.upper()])   
        self.create_design_tab_widgets[treeView2].setModel(self.create_design_tab_widgets[model2])            
        
        self.create_design_tab_widgets[lineEdit] = QLineEdit()
        self.create_design_tab_widgets[lineEdit].setMinimumWidth(177*desktop_scaled)
        self.create_design_tab_widgets[lineEdit].setMaximumWidth(177*desktop_scaled)   
        self.create_design_tab_widgets[lineEdit].setPlaceholderText('Type a new name here...')            
        self.create_design_tab_widgets[lineEdit].returnPressed.connect(lambda: self.select_texts(self.create_design_tab_widgets[lineEdit]))
        self.create_design_tab_widgets[lineEdit].returnPressed.connect(lambda: self.create_design_tab_widgets[button1].setEnabled(True))
        
        self.create_design_tab_widgets[button1] = QPushButton('Create {0} Folder'.format(design_type))
        self.create_design_tab_widgets[button1].setMinimumWidth(177*desktop_scaled)
        self.create_design_tab_widgets[button1].setMaximumWidth(177*desktop_scaled)  
        self.create_design_tab_widgets[button1].setEnabled(False)        
        #self.create_design_tab_widgets[button1].clicked.connect(lambda: self.create_design_tab_widgets[button1].setDown(True) )

        self.create_design_tab_widgets[button2] = QPushButton('Open in File Explorer')
        self.create_design_tab_widgets[button2].setMinimumWidth(177*desktop_scaled)
        self.create_design_tab_widgets[button2].setMaximumWidth(177*desktop_scaled)       
        
        self.design_type_tab_layout.addWidget(self.design_type_folder_widget )
        self.design_type_tab_layout.addWidget(self.design_type_file_widget )
        
        #self.design_splitter = QSplitter()
        
        self.design_type_utilities_layout.addWidget(self.create_design_tab_widgets[lineEdit])
        self.design_type_utilities_layout.addWidget(self.create_design_tab_widgets[button1])
        self.design_type_utilities_layout.addWidget(self.create_design_tab_widgets[button2])   

        self.design_type_tab_layout.addWidget(self.design_type_utilities_widget )  


    # ===============================================================
    # ======= implemment the 'template' of the 3D-Asset Tab =========
    # ===============================================================

    def asset_buttons_widgets(self, asset_types, parent_widget_layout, type_layout):
    
        # create layout for top butotns
        self.asset_type_buttons_widget = QWidget()
        self.asset_type_buttons_widget.setFixedHeight(34*desktop_scaled)
        self.asset_type_buttons_layout = QHBoxLayout(self.asset_type_buttons_widget)
        
        # create root level  stack layout  
        self.asset_stacked_widget = QWidget()
        self.asset_stacked_widget.setFixedHeight(800*desktop_scaled) 
        self.asset_stacked_layout = QStackedLayout(self.asset_stacked_widget)
        
        if 'Widget' in str(parent_widget_layout):
            # root level layout that holds eventhing inside the asset section
            self.asset_main_layout = QVBoxLayout(parent_widget_layout)     
            self.asset_main_layout.addWidget(self.asset_type_buttons_widget)
            self.asset_main_layout.addWidget(self.asset_stacked_widget)
        
        if 'Layout' in str(parent_widget_layout):
            # attach top buttons and stack layout into the root level layout 
            parent_widget_layout.addWidget(self.asset_type_buttons_widget)
            parent_widget_layout.addWidget(self.asset_stacked_widget)       

        self.map_buttons_widgets = {}  
        self.buttons = []
        
        if asset_types != []:
            asset_types.sort()
            for type in asset_types:

                index = asset_types.index(type)

                self.type_button = QPushButton(type)
                self.type_button.setFixedHeight(30*desktop_scaled)

                self.asset_type_buttons_layout.addWidget(self.type_button) 

                self.type_widget = QWidget()
                
                if type_layout == 'v':
                    self.type_layout = QVBoxLayout(self.type_widget)
                    self.type_widget.setFixedHeight(800*desktop_scaled)

                if type_layout == 'h':
                    self.type_layout = QHBoxLayout(self.type_widget)
                    self.type_widget.setFixedHeight(700*desktop_scaled)

                i = self.asset_stacked_layout.insertWidget(index, self.type_widget)       

                self.type_button.clicked.connect(partial(self.asset_stacked_layout.setCurrentIndex, i))   
                self.type_button.clicked.connect(lambda: self.refresh_current_ui())   
                            
                self.map_buttons_widgets[self.type_button.text()] =  self.type_layout
                self.buttons.append(self.type_button)
        
        else:
            pass
         
        for button in self.buttons:
            button.clicked.connect(partial(self.button_text_fx, button, self.buttons))
            button.clicked.connect(partial(self.button_down_fx, button, self.buttons))    
                
        self.buttons[0].setFlat(True)
        self.buttons[0].setText('[ ' + self.buttons[0].text() + ' ]')  
        
        return self.map_buttons_widgets    
             

    def create_asset_buttons_widgets(self, parent_widget, dict_type_subTypes):
       
        top_parts = self.asset_buttons_widgets(dict_type_subTypes.keys(), parent_widget, 'v')

        self.map_sub_buttons_widgets = {}
        
        for type in dict_type_subTypes.keys():
            sub_types = dict_type_subTypes[type]
            parent_layout = top_parts[type]

            if sub_types != []:
                self.map_sub_buttons_widgets[type] = self.asset_buttons_widgets(sub_types, parent_layout, 'h')
                
            else:
                pass
        
        return self.map_sub_buttons_widgets
        

    def asset_file_section(self, treeView1, model1, treeView2, model2, treeView3, model3, parent_layout, section_names, high_value):
    
        self.asset_file_widget = QWidget()
        self.asset_file_widget.setFixedHeight(high_value*desktop_scaled)
        self.asset_file_layout = QVBoxLayout(self.asset_file_widget)

        for section in section_names:
            self.sub_file_widget = QWidget()
            self.sub_file_widget.setFixedHeight(high_value/len(section_names)*desktop_scaled)
            self.sub_file_layout = QHBoxLayout(self.sub_file_widget)
      
            self.folder_widget = QTreeWidget()
            self.folder_widget.setFixedHeight((high_value-30)/len(section_names)*desktop_scaled)
            self.folder_widget.setFixedWidth(277*desktop_scaled)        
            self.create_asset_tab_widgets[section+'_'+treeView1] = QTreeView(self.folder_widget)
            self.create_asset_tab_widgets[section+'_'+treeView1].setFixedHeight((high_value-30)/len(section_names)*desktop_scaled)
            self.create_asset_tab_widgets[section+'_'+treeView1].setFixedWidth(277*desktop_scaled)        
            self.create_asset_tab_widgets[section+'_'+treeView1].setSelectionBehavior(QAbstractItemView.SelectRows)
            self.create_asset_tab_widgets[section+'_'+model1] = QStandardItemModel()
            self.create_asset_tab_widgets[section+'_'+model1].setHorizontalHeaderLabels(['>>> {} <<<'.format(section).upper()])
            self.create_asset_tab_widgets[section+'_'+treeView1].setModel(self.create_asset_tab_widgets[section+'_'+model1])
            
            self.file_widget = QTreeWidget()
            self.file_widget.setFixedHeight((high_value-30)/len(section_names)*desktop_scaled)
            self.file_widget.setFixedWidth(277*desktop_scaled)    
            self.create_asset_tab_widgets[section+'_'+treeView2] = QTreeView(self.file_widget)
            self.create_asset_tab_widgets[section+'_'+treeView2].setFixedHeight((high_value-30)/len(section_names)*desktop_scaled)
            self.create_asset_tab_widgets[section+'_'+treeView2].setFixedWidth(277*desktop_scaled)   
            self.create_asset_tab_widgets[section+'_'+treeView2].setSelectionBehavior(QAbstractItemView.SelectRows)
            self.create_asset_tab_widgets[section+'_'+model2] = QStandardItemModel()
            self.create_asset_tab_widgets[section+'_'+model2].setHorizontalHeaderLabels(['>>> File <<<'.upper()])
            self.create_asset_tab_widgets[section+'_'+treeView2].setModel(self.create_asset_tab_widgets[section+'_'+model2])             

            self.history_widget = QTreeWidget()
            self.history_widget.setFixedHeight((high_value-30)/len(section_names)*desktop_scaled)
            self.history_widget.setFixedWidth(277*desktop_scaled)    
            self.create_asset_tab_widgets[section+'_'+treeView3] = QTreeView(self.history_widget)
            self.create_asset_tab_widgets[section+'_'+treeView3].setFixedHeight((high_value-30)/len(section_names)*desktop_scaled)
            self.create_asset_tab_widgets[section+'_'+treeView3].setFixedWidth(277*desktop_scaled)   
            self.create_asset_tab_widgets[section+'_'+treeView3].setSelectionBehavior(QAbstractItemView.SelectRows)
            self.create_asset_tab_widgets[section+'_'+model3] = QStandardItemModel()
            self.create_asset_tab_widgets[section+'_'+model3].setHorizontalHeaderLabels(['>>> History <<<'.upper()])
            self.create_asset_tab_widgets[section+'_'+treeView3].setModel(self.create_asset_tab_widgets[section+'_'+model3])                           
            
            self.sub_file_layout.addWidget(self.folder_widget)
            self.sub_file_layout.addWidget(self.file_widget)
            self.sub_file_layout.addWidget(self.history_widget)

            self.asset_file_layout.addWidget(self.sub_file_widget)

        parent_layout.addWidget(self.asset_file_widget)    


            
    def asset_utility_section(self, lineEdit1, button1, button2, button4, lineEdit2, button5, button6, parent_layout, width_value , *extra_buttons):
        self.asset_utility_widget = QWidget()
        self.asset_utility_layout = QFormLayout(self.asset_utility_widget)

        if extra_buttons[0]: # create asset folder button
            self.create_asset_tab_widgets[lineEdit1] = QLineEdit()
            self.create_asset_tab_widgets[lineEdit1].setMinimumWidth(width_value*desktop_scaled)
            self.create_asset_tab_widgets[lineEdit1].setMaximumWidth(width_value*desktop_scaled)             
            self.create_asset_tab_widgets[lineEdit1].setPlaceholderText('Type a new name...')   
            self.create_asset_tab_widgets[lineEdit1].returnPressed.connect(lambda: self.select_texts(self.create_asset_tab_widgets[lineEdit1]))
            self.create_asset_tab_widgets[lineEdit1].returnPressed.connect(lambda: self.create_asset_tab_widgets[button1].setEnabled(True))         
            
            self.create_asset_tab_widgets[button1] = QPushButton('Create Folder')
            self.create_asset_tab_widgets[button1].setMinimumWidth(width_value*desktop_scaled)
            self.create_asset_tab_widgets[button1].setMaximumWidth(width_value*desktop_scaled) 
            self.create_asset_tab_widgets[button1].setEnabled(False)      

            self.asset_utility_layout.addWidget(self.create_asset_tab_widgets[lineEdit1])
            self.asset_utility_layout.addWidget(self.create_asset_tab_widgets[button1])                  
        
        self.create_asset_tab_widgets[button2] = QPushButton('Create New Variation')
        self.create_asset_tab_widgets[button2].setMinimumWidth(width_value*desktop_scaled)
        self.create_asset_tab_widgets[button2].setMaximumWidth(width_value*desktop_scaled)
        self.create_asset_tab_widgets[button2].setEnabled(False)       

        #self.create_asset_tab_widgets[button3] = QPushButton('Open in File Explorer')
        #self.create_asset_tab_widgets[button3].setMinimumWidth(width_value)
        #self.create_asset_tab_widgets[button3].setMaximumWidth(width_value) 

        self.create_asset_tab_widgets[button4] = QPushButton('Set Active')
        self.create_asset_tab_widgets[button4].setMinimumWidth(width_value*desktop_scaled)
        self.create_asset_tab_widgets[button4].setMaximumWidth(width_value*desktop_scaled)  
        self.create_asset_tab_widgets[button4].setEnabled(False)                 
        
        self.asset_utility_layout.addWidget(self.create_asset_tab_widgets[button2])
        self.asset_utility_layout.addWidget(self.create_asset_tab_widgets[button4])
        #self.asset_utility_layout.addWidget(self.create_asset_tab_widgets[button3])
  
        if extra_buttons[1]:
            self.create_asset_tab_widgets[lineEdit2] = QLineEdit()
            self.create_asset_tab_widgets[lineEdit2].setMinimumWidth(width_value*desktop_scaled)
            self.create_asset_tab_widgets[lineEdit2].setMaximumWidth(width_value*desktop_scaled)             
            self.create_asset_tab_widgets[lineEdit2].setPlaceholderText('Type an amount...')  
            self.create_asset_tab_widgets[lineEdit2].returnPressed.connect(lambda: self.select_texts(self.create_asset_tab_widgets[lineEdit2]))            

            self.asset_utility_layout.addWidget(self.create_asset_tab_widgets[lineEdit2])

        if extra_buttons[2]: # create reference and open buttons            
            self.create_asset_tab_widgets[button5] = QPushButton('Reference')        
            self.create_asset_tab_widgets[button5].setMinimumWidth(width_value*desktop_scaled)
            self.create_asset_tab_widgets[button5].setMaximumWidth(width_value)           
            
            self.create_asset_tab_widgets[button6] = QPushButton('Open')
            self.create_asset_tab_widgets[button6].setMinimumWidth(width_value*desktop_scaled)
            self.create_asset_tab_widgets[button6].setMaximumWidth(width_value*desktop_scaled)   
                        
            self.asset_utility_layout.addWidget(self.create_asset_tab_widgets[button5])
            self.asset_utility_layout.addWidget(self.create_asset_tab_widgets[button6])

        parent_layout.addWidget(self.asset_utility_widget)
            

    # ==========================================================
    # ======= implemment the 'template' of the Shots Tab =======    
    # ==========================================================

    def create_shot_tab(self, shot_type, parent_tab_widget, treeView1, model1, treeView2, model2, treeView3, model3, line_edit1, line_edit2, button1, button2, button3, button4, button5):    
        self.shot_type_tab = QWidget()
        self.shot_type_tab.setFixedHeight(770*desktop_scaled)
        self.shot_type_tab_layout = QHBoxLayout(self.shot_type_tab )
        parent_tab_widget.addTab(self.shot_type_tab, shot_type.upper())
                       
        self.shot_type_utilities_widget = QWidget()
        self.shot_type_utilities_layout = QFormLayout(self.shot_type_utilities_widget)

        self.shot_type_folder_widget = QTreeWidget()
        self.shot_type_folder_widget.setFixedHeight(730*desktop_scaled)
        self.shot_type_folder_widget.setFixedWidth(277*desktop_scaled)    
        self.create_shot_tab_widgets[treeView1] = QTreeView(self.shot_type_folder_widget)
        self.create_shot_tab_widgets[treeView1].setFixedHeight(730*desktop_scaled)
        self.create_shot_tab_widgets[treeView1].setFixedWidth(277*desktop_scaled)   
        self.create_shot_tab_widgets[treeView1].setSelectionBehavior(QAbstractItemView.SelectRows)
        self.create_shot_tab_widgets[treeView1].setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.create_shot_tab_widgets[model1] = QStandardItemModel()
        self.create_shot_tab_widgets[model1].setHorizontalHeaderLabels(['>>> {} <<<'.format(shot_type).upper()])   
        self.create_shot_tab_widgets[treeView1].setModel(self.create_shot_tab_widgets[model1])  
        #self.create_shot_tab_widgets[treeView1].doubleClicked.connect(lambda: self.refresh_current_ui())         
        #self.create_shot_tab_widgets[treeView1].doubleClicked.connect(lambda: self.populate_items_in_shot_tabs())

        self.shot_type_file_widget = QTreeWidget()
        self.shot_type_file_widget.setFixedHeight(730*desktop_scaled)
        self.shot_type_file_widget.setFixedWidth(277*desktop_scaled)    
        self.create_shot_tab_widgets[treeView2] = QTreeView(self.shot_type_file_widget)
        self.create_shot_tab_widgets[treeView2].setFixedHeight(730*desktop_scaled)
        self.create_shot_tab_widgets[treeView2].setFixedWidth(277*desktop_scaled)   
        self.create_shot_tab_widgets[treeView2].setSelectionBehavior(QAbstractItemView.SelectRows)
        self.create_shot_tab_widgets[treeView2].setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.create_shot_tab_widgets[model2] = QStandardItemModel()
        self.create_shot_tab_widgets[model2].setHorizontalHeaderLabels(['>>> File <<<'.upper()])   
        self.create_shot_tab_widgets[treeView2].setModel(self.create_shot_tab_widgets[model2])   

        self.shot_type_history_file_widget = QTreeWidget()
        self.shot_type_history_file_widget.setFixedHeight(730*desktop_scaled)
        self.shot_type_history_file_widget.setFixedWidth(277*desktop_scaled)    
        self.create_shot_tab_widgets[treeView3] = QTreeView(self.shot_type_history_file_widget)
        self.create_shot_tab_widgets[treeView3].setFixedHeight(730*desktop_scaled)
        self.create_shot_tab_widgets[treeView3].setFixedWidth(277*desktop_scaled)   
        self.create_shot_tab_widgets[treeView3].setSelectionBehavior(QAbstractItemView.SelectRows)
        self.create_shot_tab_widgets[treeView3].setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.create_shot_tab_widgets[model3] = QStandardItemModel()
        self.create_shot_tab_widgets[model3].setHorizontalHeaderLabels(['>>> HISTORY <<<'.upper()])   
        self.create_shot_tab_widgets[treeView3].setModel(self.create_shot_tab_widgets[model3])

        self.create_shot_tab_widgets[line_edit1] = QLineEdit()
        self.create_shot_tab_widgets[line_edit1].setFixedWidth(170*desktop_scaled) 
        self.create_shot_tab_widgets[line_edit1].setPlaceholderText('Scene numbers....')  
        self.create_shot_tab_widgets[line_edit1].returnPressed.connect(lambda: self.select_texts(self.create_shot_tab_widgets[line_edit1] ))

        self.create_shot_tab_widgets[line_edit2] = QLineEdit()
        self.create_shot_tab_widgets[line_edit2].setFixedWidth(170*desktop_scaled)
        self.create_shot_tab_widgets[line_edit2].setPlaceholderText('Shot amounts...')   
        self.create_shot_tab_widgets[line_edit2].returnPressed.connect(lambda: self.select_texts(self.create_shot_tab_widgets[line_edit2] ))
        
        self.create_shot_tab_widgets[button1] = QPushButton('Generate Scene-Shot Folders')
        self.create_shot_tab_widgets[button1].setFixedWidth(170*desktop_scaled)    
        self.create_shot_tab_widgets[button1].clicked.connect(lambda: self.generate_new_scene_shot_folders())
        self.create_shot_tab_widgets[button1].clicked.connect(lambda: self.refresh_current_ui())
        self.create_shot_tab_widgets[button1].clicked.connect(lambda: self.create_shot_tab_widgets[line_edit1].clear())
        self.create_shot_tab_widgets[button1].clicked.connect(lambda: self.create_shot_tab_widgets[line_edit2].clear())
        
        self.create_shot_tab_widgets[button2] = QPushButton('Open')
        self.create_shot_tab_widgets[button2].setFixedWidth(170*desktop_scaled)
             
        self.create_shot_tab_widgets[button3] = QPushButton('Reference')
        self.create_shot_tab_widgets[button3].setFixedWidth(170*desktop_scaled)

        self.create_shot_tab_widgets[button4] = QPushButton('Create New Variation')
        self.create_shot_tab_widgets[button4].setFixedWidth(170*desktop_scaled)
        self.create_shot_tab_widgets[button4].setEnabled(False)
             
        self.create_shot_tab_widgets[button5] = QPushButton('Set Active')
        self.create_shot_tab_widgets[button5].setFixedWidth(170*desktop_scaled)   
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
            dict_scene_shot = initial_shot_dict()
            if dict_scene_shot == None:
                dict_scene_shot = {1:1}
            project = CG_Project(project_name, dict_scene_shot)
            return project


    def list_available_projects(self):
        
        self.list_to_verify = configuration.Departments.keys()
        self.list_to_verify.sort()

        self.drive = self.select_drive_combo_box.currentText() 
        try:
            self.candidate_list = os.listdir(self.drive)
        except WindowsError:
            return
            
        self.projects = []
        
        for folder in self.candidate_list:
            try:
                dir = self.drive + folder
            except UnicodeEncodeError:
                pass 
                
            if os.path.isdir(dir):
                try:
                    sub_folders = os.listdir(dir)
                    if len(sub_folders) == 10:                        
                        sub_folders.sort()
                        if self.list_to_verify == sub_folders:
                            self.projects.append(folder)
                except WindowsError :
                    pass
        
        return self.projects           


    def update_combo_box_list(self):
        
        self.current_project_combo_box.clear()
        
        projects = self.list_available_projects()
        
        try:
            
            self.current_project_combo_box.addItems(projects)
            
        except TypeError:
            pass


    def set_to_newly_created_project(self):
        self.update_combo_box_list()
        latest_index = self.current_project_combo_box.count() - 1

        self.current_project_combo_box.setCurrentIndex(latest_index)


    def get_current_project(self):
        self.current_project = None
        drive = self.select_drive_combo_box.currentText() 
        project_name = self.current_project_combo_box.currentText()
        
        if project_name != '':
            return CG_Project_Edit(drive, project_name)     
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


    def populate_items_in_design_tab(self, design_type):

        #current_project = self.get_current_project()
        get_design_folders_dict = {}

        if self.current_project != None:

            try:
                parent_folder = self.folder_type_directories_dict.get(design_type)
                self.populate_folders_into_qtreeview(design_type, self.create_design_tab_widgets, eval(parent_folder))

            except AttributeError, WindowsError:
                pass  

        else:
            return           


    def populate_items_in_design_tabs(self):
        self.populate_items_in_design_tab('Character_Design')
        self.populate_items_in_design_tab('Props_Design')
        self.populate_items_in_design_tab('Environment_Design')
        self.populate_items_in_design_tab('2D_Continuities')


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

        design_categories_dict = {  'Character_Design': self.open_file_in_design_tab,
                                    'Props_Design': self.open_file_in_design_tab,
                                    'Environment_Design': self.open_file_in_design_tab,
                                    '2D_Continuities': self.open_file_in_design_tab }

        
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

        design_categories_dict = {  'Character_Design':     'self.open_file_in_explorer_design_tab',
                                    'Props_Design':         'self.open_file_in_explorer_design_tab',
                                    'Environment_Design':   'self.open_file_in_explorer_design_tab',
                                    '2D_Continuities':      'self.open_file_in_explorer_design_tab' }

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


    def get_shots_tabs_current_index(self):
 
        return int(self.shot_widget.currentIndex())

    
    def get_asset_stacked_layout_current_index(self):
        asset_type_buttons_stacked_layout = self.asset_widget.findChild(QStackedLayout)
        asset_type_index = asset_type_buttons_stacked_layout.currentIndex()
        asset_sub_type_index = asset_type_buttons_stacked_layout.currentWidget().findChild(QStackedLayout).currentIndex()
   
        return (asset_type_index, asset_sub_type_index)

        
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
        make_folders_dict = { 'Character_Design':           'self.current_project.make_char_design_folder',
                              'Props_Design':               'self.current_project.make_props_design_folder',
                              'Environment_Design':         'self.current_project.make_environment_design_folder',
                              '2D_Continuities':            'self.current_project.make_continuities_folder',
                              '1_MODEL_CHARACTER':          'self.current_project.make_char_dirs',
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



#========================================================
#======= implement the watching directory feature =======
#========================================================

ACTIONS = {     1 : "Created",
                2 : "Deleted",
                3 : "Updated",
                4 : "Renamed to something",
                5 : "Renamed from something" }




class Track_Directory(QThread):
    
    def __init__(self, path_to_watch):
        super(Track_Directory, self).__init__()
        self.path_to_watch = path_to_watch
        self.FILE_LIST_DIRECTORY = 0x0001
        self.include_subdirectories = True


    def run(self):
   
        for result in self.watch_path():
            print result


    def watch_path(self):
        
        hDir = win32file.CreateFile (   self.path_to_watch,
                                        self.FILE_LIST_DIRECTORY,
                                        win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                                        None,
                                        win32con.OPEN_EXISTING,
                                        win32con.FILE_FLAG_BACKUP_SEMANTICS,
                                        None )

        while 1:
            
            results = win32file.ReadDirectoryChangesW ( hDir,
                                                        1024,
                                                        self.include_subdirectories,
                                                        win32con.FILE_NOTIFY_CHANGE_FILE_NAME | 
                                                        win32con.FILE_NOTIFY_CHANGE_DIR_NAME |
                                                        win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES |
                                                        win32con.FILE_NOTIFY_CHANGE_SIZE |
                                                        win32con.FILE_NOTIFY_CHANGE_LAST_WRITE |
                                                        win32con.FILE_NOTIFY_CHANGE_SECURITY,
                                                        None,
                                                        None )

            for action, file in results:
                full_filename = os.path.join(self.path_to_watch, file)
                if not os.path.exists(full_filename):
                    file_type = "<deleted>"
                elif os.path.isdir(full_filename):
                    file_type = 'folder'
                else:
                    file_type = 'file'
                yield (file_type, full_filename, ACTIONS.get (action, "Unknown"))            



# ======================================
# ======= some backend functions =======
# ======================================

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


def get_drives_letters():

    if 'win' in sys.platform:
        #drivelist = subprocess.Popen('wmic logicaldisk get name,description', shell=True, stdout=subprocess.PIPE)
        #drivelisto, err = drivelist.communicate()
        #driveLines = drivelisto.split('\n')
        drives = win32api.GetLogicalDriveStrings()
        drives = drives.split('\000')[:-1]
        
        # filter out those optical drives
        physical_drives = []

        for drive in drives:
            not_optical = win32file.GetDriveType(unix_format(drive)[:-1])
            if not_optical == win32file.DRIVE_FIXED or not_optical == win32file.DRIVE_REMOTE:
                physical_drives.append(unix_format(drive))

        return physical_drives
        
    elif 'linux' in sys.platform:
         listdrives=subprocess.Popen('mount', shell=True, stdout=subprocess.PIPE)
         listdrivesout, err=listdrives.communicate()
         for idx,drive in enumerate(filter(None,listdrivesout)):
             listdrivesout[idx]=drive.split()[2]         


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


project_manager_app = QApplication(sys.argv)         
project_manager_gui = main_gui()   

project_manager_app.setStyle('cleanlooks')
project_manager_gui.show()          
project_manager_app.exec_()