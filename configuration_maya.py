design = {'CHARACTER':[], 'ENVIRONMENT':[], 'COMPONENT':[], 'PROPS':[], 'CONTINUITY':[]}

miscellaneous       =   {'___backup':[], '___script': []}

geo                 =   {'__HIGH_RESOLUTION':miscellaneous, '__MIDDLE_RESOLUTION': miscellaneous, '__LOW_RESOLUTION':miscellaneous}
geo_folders         =   {'GEOMETRY': geo}

setup               =   {'__DEFORMED': miscellaneous, '__RIGGED': miscellaneous}
setup_folders       =   {'SETUP': setup}

surfacing           =   {'__SHADER': miscellaneous, '__TEXTURE': miscellaneous}
surfacing_folders   =   {'SURFACING': surfacing}

template            =   {'__LIGHTING': miscellaneous, '__RENDERING': miscellaneous}

character           =   {'char_name_place_holder':[geo_folders, setup_folders, surfacing_folders, 'GPU']}
props               =   {'props_name_place_holder':[geo_folders, setup_folders, surfacing_folders, 'GPU']}
component           =   {'com_name_place_holder':[geo_folders, surfacing_folders, 'GPU']}
environment         =   {'env_name_place_holder':[]}

Playblasts          =   {'ANIMATION':[],'LAYOUT':[],}

assets              =   {   'CHARACTER':    [character],
                            'PROPS':        [props],
                            'COMPONENT':    [component],
                            'ENVIRONMENT':  [environment],
                            'TEMPLATE':     [template],
                            '2D_DESIGN':    [design]      }                            