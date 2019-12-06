def get_app_urls():
    app_urls = ['https://raw.githubusercontent.com/Aceinna/python-openimu/bugfix/app_config/Compass/openimu.json',
	        'https://raw.githubusercontent.com/Aceinna/python-openimu/bugfix/app_config/IMU/openimu.json',
	        'https://raw.githubusercontent.com/Aceinna/python-openimu/bugfix/app_config/INS/openimu.json',
	        'https://raw.githubusercontent.com/Aceinna/python-openimu/bugfix/app_config/Leveler/openimu.json',
	        'https://raw.githubusercontent.com/Aceinna/python-openimu/bugfix/app_config/OpenIMU/openimu.json',
	        'https://raw.githubusercontent.com/Aceinna/python-openimu/bugfix/app_config/VG_AHRS/openimu.json'
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

app_url_base = 'https://raw.githubusercontent.com/Aceinna/python-openimu/bugfix/app_config'
app_str = ['INS','VG_AHRS','IMU','Compass','Leveler']
