# import os
# import json
# from dotenv import load_dotenv

# load_dotenv()


# with open(os.path.join(os.environ.get('CONFIG_PATH'), os.environ.get('CONFIG_FILE_NAME'))) as config_file:
#     config = json.load(config_file)


# class ConfigBase:

#     def __init__(self):

#         self.SECRET_KEY = config.get('SECRET_KEY')
#         self.PROJ_ROOT_PATH = os.environ.get('PROJ_ROOT_PATH')
#         self.PROJ_DB_PATH = os.environ.get('PROJ_DB_PATH')
#         self.DESTINATION_PASSWORD = config.get('DESTINATION_PASSWORD')


# class ConfigLocal(ConfigBase):

#     def __init__(self):
#         super().__init__()

#     DEBUG = True
            

# class ConfigDev(ConfigBase):

#     def __init__(self):
#         super().__init__()

#     DEBUG = True
            

# class ConfigProd(ConfigBase):

#     def __init__(self):
#         super().__init__()

#     DEBUG = False

import os
from tr01_config import ConfigLocal, ConfigDev, ConfigProd

if os.environ.get('CONFIG_TYPE')=='local':
    config = ConfigLocal()
    print('- whatSticks09web/app_pacakge/config: Local')
elif os.environ.get('CONFIG_TYPE')=='dev':
    config = ConfigDev()
    print('- whatSticks09web/app_pacakge/config: Development')
elif os.environ.get('CONFIG_TYPE')=='prod':
    config = ConfigProd()
    print('- whatSticks09web/app_pacakge/config: Production')

print(f"webpackage location: {os.environ.get('WEB_ROOT')}")
print(f"config location: {os.path.join(os.environ.get('CONFIG_PATH'),os.environ.get('CONFIG_FILE_NAME')) }")