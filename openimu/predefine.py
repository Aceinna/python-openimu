def get_app_urls():
    app_urls = ['https://raw.githubusercontent.com/Aceinna/python-openimu/master/app_config/Compass/openimu.json',
                'https://raw.githubusercontent.com/Aceinna/python-openimu/master/app_config/IMU/openimu.json',
                'https://raw.githubusercontent.com/Aceinna/python-openimu/master/app_config/INS/openimu.json',
                'https://raw.githubusercontent.com/Aceinna/python-openimu/master/app_config/Leveler/openimu.json',
                'https://raw.githubusercontent.com/Aceinna/python-openimu/master/app_config/OpenIMU/openimu.json',
                'https://raw.githubusercontent.com/Aceinna/python-openimu/master/app_config/VG_AHRS/openimu.json'
                ]
    return app_urls


def get_app_names():
    app_names = ['Compass',
                 'IMU',
                 'INS',
                 'Leveler',
                 'OpenIMU',
                 'VG_AHRS'
                 ]
    return app_names


app_str = ['INS', 'VG_AHRS', 'IMU', 'Compass', 'Leveler']

string_folder_path = 'app_config/APP_TYP/openimu.json'
