design = {'CHARACTER':[], 'ENVIRONMENT':[], 'COMPONENT':[], 'PROPS':[], 'CONTINUITY':[]}

miscellaneous       =   {'___backup':[], '___script': []}

geo                 =   {'HIGH_RESOLUTION':miscellaneous, 'MIDDLE_RESOLUTION': miscellaneous, 'LOW_RESOLUTION':miscellaneous}
geo_folders         =   {'GEOMETRY': geo}

setup               =   {'DEFORMED': miscellaneous, 'RIGGED': miscellaneous}
setup_folders       =   {'SETUP': setup}

surfacing           =   {'SHADER': miscellaneous, 'TEXTURE': miscellaneous}
surfacing_folders   =   {'SURFACING': surfacing}

template            =   {'LIGHTING': miscellaneous, 'RENDERING': miscellaneous}

character           =   {'__char_name_place_holder':[geo_folders, setup_folders, surfacing_folders, 'GPU']}
props               =   {'__props_name_place_holder':[geo_folders, setup_folders, surfacing_folders, 'GPU']}
component           =   {'__com_name_place_holder':[geo_folders, surfacing_folders, 'GPU']}
environment         =   {'__env_name_place_holder':[]}

Playblasts          =   {'ANIMATION':[],'LAYOUT':[],}

assets              =   {   'CHARACTER':    [character],
                            'PROPS':        [props],
                            'COMPONENT':    [component],
                            'ENVIRONMENT':  [environment],
                            'TEMPLATE':     [template],
                            '2D_DESIGN':    [design]      }                            