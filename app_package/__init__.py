from flask import Flask
# from flask import session
from app_package.config import config
import os
import logging
from logging.handlers import RotatingFileHandler
from pytz import timezone
from datetime import datetime, timedelta

## AFTER rebuild ##
from tr01_models import login_manager
from flask_mail import Mail

# if os.environ.get('FLASK_CONFIG_TYPE')=='local':
#     config = ConfigLocal()
#     print('- Personalwebsite/__init__: Development - Local')
# elif os.environ.get('FLASK_CONFIG_TYPE')=='dev':
#     config = ConfigDev()
#     print('- Personalwebsite/__init__: Development')
# elif os.environ.get('FLASK_CONFIG_TYPE')=='prod':
#     config = ConfigProd()
#     print('- Personalwebsite/__init__: Configured for Production')


if not os.path.exists(os.path.join(os.environ.get('WEB_ROOT'),'logs')):
    os.makedirs(os.path.join(os.environ.get('WEB_ROOT'), 'logs'))

# timezone 
def timetz(*args):
    return datetime.now(timezone('Europe/Paris') ).timetuple()

logging.Formatter.converter = timetz

formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

logger_init = logging.getLogger('__init__')
logger_init.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(os.path.join(os.environ.get('WEB_ROOT'),'logs','__init__.log'), mode='a', maxBytes=5*1024*1024,backupCount=2)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

stream_handler_tz = logging.StreamHandler()

logger_init.addHandler(file_handler)
logger_init.addHandler(stream_handler)

logging.getLogger('werkzeug').setLevel(logging.DEBUG)
logging.getLogger('werkzeug').addHandler(file_handler)

logger_init.info(f'--- Starting Tu Rincón ---')
# logger_init.info(f'--- secrete key: {os.environ.get("SECRET_KEY")} ---')
# logger_init.info(f'--- WEB_ROOT: {os.environ.get("WEB_ROOT")} ---')




# Create rincon_files folder
if not os.path.exists(os.path.join(os.environ.get('DB_ROOT'),'rincon_files')):
    os.makedirs(os.path.join(os.environ.get('DB_ROOT'),'rincon_files'))
    print(f"- created {os.path.join(os.environ.get('DB_ROOT'),'rincon_files')} -")
# Create auxilary folder
if not os.path.exists(os.path.join(os.environ.get('DB_ROOT'),'auxilary')):
    os.makedirs(os.path.join(os.environ.get('DB_ROOT'),'auxilary'))
    print(f"- created {os.path.join(os.environ.get('DB_ROOT'),'auxilary')} -")

mail = Mail()

def create_app(config_for_flask = config):
    app = Flask(__name__)   
    app.config.from_object(config_for_flask)
    # app.permanent_session_lifetime = timedelta(seconds= 10)
    login_manager.init_app(app)
    mail.init_app(app)

    # logger_init.info(f'--- secrete key: in create_app ---')
    # logger_init.info(f'--- secrete key: {app.config.get("SECRET_KEY")} ---')

    from app_package.main.routes import main
    from app_package.users.routes import users
    from app_package.admin.routes import admin
    from app_package.error_handlers.routes import eh

    app.register_blueprint(main)
    app.register_blueprint(users)
    app.register_blueprint(admin)
    app.register_blueprint(eh)

    return app