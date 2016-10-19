destination_char = {'__char_name':[]}
destination_props = {'__props_name':[]}
destination_env = {'__env_name':[]}
destination_obj = {'__obj_name':[]}
destination_render = {'__render_template':[]}


Playblasts = {'Playblasts':['Finals_MOV','Layouts_MOV']}

Templates = {'Characters':destination_char,'Environments':destination_env, 'Rendering':destination_render}
Templates = {'Templates':Templates}

geo_chars = {'High_Resolution':destination_char, 'Low_Resolution':destination_char}
geo_Characters = {'Characters':geo_chars}

Assembled_Scenes = {'Assembled_Scenes':[destination_env]}
Components = {'Components':destination_obj}
geo_env = {'High_Resolution':[Assembled_Scenes,Components],'Low_Resolution':[Assembled_Scenes,Components]}
geo_Environments = {'Environments':geo_env}

geo_prop = {'High_Resolution':destination_props,'Low_Resolution':destination_props} 
geo_Props = {'Props':geo_prop}

shading_grp = {'Characters':destination_char,'Components':destination_env,'Props':destination_props}
shaders = {'Shaders': shading_grp}
texture_grp = {'Characters':destination_char,'Components':destination_env,'Props':destination_props}
textures = {'Textures': texture_grp}

deformed_char = {'Deformed':destination_char}
rigged_char = {'Rigged':destination_char}
deformed_props = {'Deformed':destination_props}
rigged_props = {'Rigged':destination_props}
character_setup = {'Characters':[deformed_char,rigged_char]}
props_setup = {'Props':[deformed_props,rigged_props]}

Departments = {'ANIMATION':['Cached','Finals','Layouts',Playblasts],
               'LIGHTING':[Templates,'SHOTS'],
               'MODEL':[geo_Characters, geo_Environments, geo_Props,'SHOTS'],
               'RENDERING':[],
               'SETUP':[character_setup,props_setup],
               'SURFACING':[shaders,textures],
               'VFX':['Cached','SHOTS']}

no_shot_folders = ['Textures']
asset_folders = ['MODEL','SETUP','SURFACING','LIGHTING']