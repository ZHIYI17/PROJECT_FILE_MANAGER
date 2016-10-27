miscellaneous       =   {'___backup':[], '___script': []}

geo                 =   {'High_Resolution':miscellaneous, 'Low_Resolution':miscellaneous}
geo_folders         =   {'GEOMETRY': geo}
setup               =   {'Deformed': miscellaneous, 'Rigged': miscellaneous}
setup_folders       =   {'SETUP': setup}
surfacing           =   {'Shader': miscellaneous, 'Texture': miscellaneous}
surfacing_folders   =   {'SURFACING': surfacing}
template            =   {'Lighting': miscellaneous, 'Rendering': miscellaneous}
template_folders    =   {'TEMPLATE': template}

character           =   {'__char_name_place_holder':[geo_folders, setup_folders, surfacing_folders, 'GPU']}
props               =   {'__props_name_place_holder':[geo_folders, setup_folders, surfacing_folders, 'GPU']}
component           =   {'__com_name_place_holder':[geo_folders, surfacing_folders, 'GPU']}
environment         =   {'__env_name_place_holder':['SHOTS']}

Playblasts          =   {'Animation_MOV':[],'Layouts_MOV':[],}

assets              =   {   'CHARACTER':    [character],
                            'PROPS':        [props],
                            'COMPONENT':    [component],
                            'ENVIRONMENT':  [environment]   }

