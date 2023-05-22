from flask import Blueprint
from flask import render_template, current_app, request
# from app_package.utils import logs_dir
import os
import logging
from logging.handlers import RotatingFileHandler

#Setting up Logger
formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

#initialize a logger
logger_error = logging.getLogger(__name__)
logger_error.setLevel(logging.DEBUG)


#where do we store logging information
file_handler = RotatingFileHandler(os.path.join(os.environ.get('WEB_ROOT'),"logs",'error_routes.log'), mode='a', maxBytes=5*1024*1024,backupCount=2)
file_handler.setFormatter(formatter)

#where the stream_handler will print
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

# logger_sched.handlers.clear() #<--- This was useful somewhere for duplicate logs
logger_error.addHandler(file_handler)
logger_error.addHandler(stream_handler)


eh = Blueprint('errors', __name__)

@eh.app_errorhandler(400)
def handle_400(err):
    logger_error.info(f'@eh.app_errorhandler(400), err: {err}')
    error_message = "Something went wrong. Maybe you entered something I wasn't expecting?"
    return render_template('error_template.html', error_number="400", error_message=error_message)
#messaged copied from: https://www.pingdom.com/blog/the-5-most-common-http-errors-according-to-google/

@eh.app_errorhandler(401)
def handle_401(err):
    logger_error.info(f'@eh.app_errorhandler(401), err: {err}')
    error_message = "This error happens when a website visitor tries to access a restricted web page but isn’t authorized to do so, usually because of a failed login attempt."
    return render_template('error_template.html', error_number="401", error_message=error_message)
#message copied form: https://www.pingdom.com/blog/the-5-most-common-http-errors-according-to-google/

@eh.app_errorhandler(404)
def handle_404(err):
    print('* --> In Error404 route: ',request.referrer)
    logger_error.info(f'@eh.app_errorhandler(404), err: {err}')
    error_message = "This page doesn't exist. Check what was typed in the address bar."
    return render_template('error_template.html', error_number="404", error_message=error_message, description = err.description)
#404 occurs if address isnt' right

@eh.app_errorhandler(500)
def handle_500(err):
    logger_error.info(f'@eh.app_errorhandler(500), err: {err}')
    error_message = f"Could be anything... ¯\_(ツ)_/¯  ... try again or send email to {current_app.config['EMAIL_DASH_AND_DATA']}."
    return render_template('error_template.html', error_number="500", error_message=error_message)


#####################
# These not working #
#####################
if os.environ.get('CONFIG_TYPE')=='prod':
    @eh.app_errorhandler(AttributeError)
    def error_attribute(AttributeError):
        error_message = f"Could be anything... ¯\_(ツ)_/¯  ... try again or send email to {current_app.config['EMAIL_DASH_AND_DATA']}."
        return render_template('error_template.html', error_number="Did you login?", error_message=error_message, 
        error_message_2 = AttributeError)

    @eh.app_errorhandler(KeyError)
    def error_key(KeyError):
        error_message = f"Could be anything... ¯\_(ツ)_/¯  ... try again or send email to {current_app.config['EMAIL_DASH_AND_DATA']}."
        return render_template('error_template.html', error_number="Did you login?", error_message=error_message,
        error_message_2 = KeyError)

    @eh.app_errorhandler(TypeError)
    def error_key(KeyError):
        error_message = f"Could be anything... ¯\_(ツ)_/¯  ... try again or send email to {current_app.config['EMAIL_DASH_AND_DATA']}."
        return render_template('error_template.html', error_number="Did you login?", error_message=error_message,
        error_message_2 = TypeError)
