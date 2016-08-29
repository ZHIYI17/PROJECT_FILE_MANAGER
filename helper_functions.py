import os,sys
import configuration

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

def make_folders(parent_dir,base_name):    
    '''
    parent_dir is a string type, make sure to be end with '/'
    base_name is the name of folder
    '''
    dir = unix_format(parent_dir)
    folder = dir + base_name
    os.mkdir(folder)

def update_shot_dict(dict_amount,scene_num,shot_amount):
    '''
    - this function returns an updated dict_amount, which based on the given scene_num and shot_amount
    - dict_amount is a dictionary type, this function accepts empty/non-empty dictionary, it looks like: {<scn_num>:<amount_of_shots>}, for example: {1:10,2:7,...}
    - scene_num and shot_amount are int type, which indicates the scene number and its corresponding amount of shots
    '''
    dict_amount.keys().append(scene_num)
    dict_amount[scene_num] = shot_amount
    return dict_amount
   

