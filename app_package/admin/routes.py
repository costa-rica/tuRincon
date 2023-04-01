
from flask import Blueprint
from flask import render_template, url_for, redirect, flash, request, \
    abort, session, Response, current_app, send_from_directory, make_response
import bcrypt
from flask_login import login_required, login_user, logout_user, current_user
import logging
from logging.handlers import RotatingFileHandler
import os
import json
from tr01_models import sess, engine, text, Base, \
    Users, Rincons, RinconsPosts, RinconsPostsLikes, \
    RinconsPostsComments, RinconsPostsCommentsLikes, UsersToRincons

from app_package.users.utils import send_reset_email, send_confirm_email
import pandas as pd
import shutil

#Setting up Logger
formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

#initialize a logger
logger_admin = logging.getLogger(__name__)
logger_admin.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(os.path.join(os.environ.get('WEB_ROOT'),'logs','admin_routes.log'), mode='a', maxBytes=5*1024*1024,backupCount=2)
file_handler.setFormatter(formatter)

#where the stream_handler will print
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

# logger_sched.handlers.clear() #<--- This was useful somewhere for duplicate logs
logger_admin.addHandler(file_handler)
logger_admin.addHandler(stream_handler)


salt = bcrypt.gensalt()


admin = Blueprint('admin', __name__)


@admin.route('/admin_page', methods = ['GET', 'POST'])
@login_required
def admin_page():
    print('- in admin_db -')
    print("current_user.admin: ", current_user.admin)

    if not current_user.admin:
        return redirect(url_for('main.rincons'))

    return render_template('admin/admin.html')

@admin.route('/admin_db_download', methods = ['GET', 'POST'])
@login_required
def admin_db_download():
    print('- in admin_db_download -')
    print("current_user.admin: ", current_user.admin)

    if not current_user.admin:
        return redirect(url_for('main.rincons'))

    metadata = Base.metadata
    db_table_list = [table for table in metadata.tables.keys()]

    csv_dir_path = os.path.join(current_app.config.get('DB_ROOT'), 'db_backup')

    if request.method == "POST":
        formDict = request.form.to_dict()
        print(f"- search_rincons POST -")
        print("formDict: ", formDict)

        # craete folder to save
        if not os.path.exists(os.path.join(os.environ.get('DB_ROOT'),"db_backup")):
            os.makedirs(os.path.join(os.environ.get('DB_ROOT'),"db_backup"))


        db_table_list = []
        for key, value in formDict.items():
            if value == "db_table":
                db_table_list.append(key)
      
        db_tables_dict = {}
        for table in db_table_list:
            base_query = sess.query(metadata.tables[table])
        #     df = pd.read_sql(text(str(base_query)), engine.connect())
            db_tables_dict[table] = pd.read_sql(text(str(base_query)), engine.connect())
            db_tables_dict[table].to_csv(os.path.join(csv_dir_path, f"{table}.csv"))
        
        shutil.make_archive(csv_dir_path, 'zip', csv_dir_path)

        return redirect(url_for('admin.download_db_tables_as_csv'))
    
    return render_template('admin/admin_db_download.html', db_table_list=db_table_list, )

@admin.route("/download_db_tables_as_csv", methods=["GET","POST"])
@login_required
def download_db_tables_as_csv():
    return send_from_directory(os.path.join(current_app.config['DB_ROOT']),'db_backup.zip', as_attachment=True)



@admin.route('/admin_db_upload', methods = ['GET', 'POST'])
@login_required
def admin_db_upload():
    print('- in admin_db_download -')
    print("current_user.admin: ", current_user.admin)

    if not current_user.admin:
        return redirect(url_for('main.rincons'))

    metadata = Base.metadata
    db_table_list = [table for table in metadata.tables.keys()]
    csv_dir_path_upload = os.path.join(current_app.config.get('DB_ROOT'), 'db_upload')

    if request.method == "POST":
        formDict = request.form.to_dict()
        print(f"- search_rincons POST -")
        print("formDict: ", formDict)

        requestFiles = request.files

        print("requestFiles: ", requestFiles)

        # craete folder to store upload files
        if not os.path.exists(os.path.join(os.environ.get('DB_ROOT'),"db_upload")):
            os.makedirs(os.path.join(os.environ.get('DB_ROOT'),"db_upload"))
        

        csv_file_for_table = request.files.get('csv_table_upload')
        csv_file_for_table_filename = csv_file_for_table.filename

        logger_admin.info(f"-- Get CSV file name --")
        logger_admin.info(f"--  {csv_file_for_table_filename} --")

        ## rename image
        # new_image_name = f"post_image_{new_post.id}{file_extension}"

        ## save to static rincon directory
        # this_rincon_dir_name = f"{rincon_id}_{rincon.name_no_spaces}"
        path_to_uploaded_csv = os.path.join(csv_dir_path_upload,csv_file_for_table_filename)
        csv_file_for_table.save(path_to_uploaded_csv)

        print(f"-- table to go to: { formDict.get('existing_db_table_to_update')}")

        return redirect(url_for('admin.upload_table', table_name = formDict.get('existing_db_table_to_update'),
            path_to_uploaded_csv=path_to_uploaded_csv))


    return render_template('admin/admin_db_upload.html', db_table_list=db_table_list)


@admin.route('/upload_table/<table_name>', methods = ['GET', 'POST'])
@login_required
def upload_table(table_name):
    print('- in admin_db_download -')
    print("current_user.admin: ", current_user.admin)
    path_to_uploaded_csv = request.args.get('path_to_uploaded_csv')

    if not current_user.admin:
        return redirect(url_for('main.rincons'))

    metadata = Base.metadata
    # db_table_list = [table for table in metadata.tables.keys()]
    existing_table_column_names = metadata.tables[table_name].columns.keys()

    df = pd.read_csv(path_to_uploaded_csv)

    cols = list(df.columns)[1:]
    for col in cols:
        if col[:len(table_name)] == table_name:
            df = df.rename(columns=({col: col[len(table_name)+1:]}))

    replacement_data_col_names = df.columns[1:]


    if request.method == "POST":
        formDict = request.form.to_dict()
        print(f"- search_rincons POST -")
        print("formDict: ", formDict)

        # TODO: upload data to existing database
        ### formDict (key) is existing databaes column name
        ### value is the new data (aka the uploaded csv file column)

    
    return render_template('admin/upload_table.html', existing_table_column_names=existing_table_column_names,
        replacement_data_col_names = replacement_data_col_names)


