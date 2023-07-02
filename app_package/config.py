import os
from tr01_config import ConfigLocal, ConfigDev, ConfigProd

if os.environ.get('FLASK_ENV')=='local':
    config = ConfigLocal()
    print('- TuRincon01/app_pacakge/config: Local')
elif os.environ.get('FLASK_ENV')=='dev':
    config = ConfigDev()
    print('- TuRincon01/app_pacakge/config: Development')
elif os.environ.get('FLASK_ENV')=='prod':
    config = ConfigProd()
    print('- TuRincon01/app_pacakge/config: Production')

print(f"webpackage location: {os.environ.get('WEB_ROOT')}")
print(f"config location: {os.path.join(os.environ.get('CONFIG_PATH'),os.environ.get('CONFIG_FILE_NAME')) }")