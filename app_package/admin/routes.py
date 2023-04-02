
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
from datetime import datetime

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
        for table_name in db_table_list:
            base_query = sess.query(metadata.tables[table_name])
            df = pd.read_sql(text(str(base_query)), engine.connect())

            # fix table names
            cols = list(df.columns)
            for col in cols:
                if col[:len(table_name)] == table_name:
                    df = df.rename(columns=({col: col[len(table_name)+1:]}))

            # Users table convert password from bytes to strings
            if table_name == 'users':
                df['password'] = df['password'].str.decode("utf-8")


            db_tables_dict[table_name] = df
            db_tables_dict[table_name].to_csv(os.path.join(csv_dir_path, f"{table_name}.csv"), index=False)
        
        shutil.make_archive(csv_dir_path, 'zip', csv_dir_path)

        return redirect(url_for('admin.download_db_tables_as_csv'))
    
    return render_template('admin/admin_db_download.html', db_table_list=db_table_list )

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

        ## save to static rincon directory
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

    # Get Table Column names from the database corresponding to the running webiste/app
    metadata = Base.metadata
    existing_table_column_names = metadata.tables[table_name].columns.keys()

    # Get column names from the uploaded csv
    df = pd.read_csv(path_to_uploaded_csv)

    if 'time_stamp_utc' in df.columns:
        try:
            df['time_stamp_utc'] = pd.to_datetime(df['time_stamp_utc'], format='%d/%m/%Y %H:%M')
        # except ValueError:
        #     df['time_stamp_utc'] = pd.to_datetime(df['time_stamp_utc'], format='%d/%m/%Y %H:%M:%S')
        except:
            df = pd.read_csv(path_to_uploaded_csv, parse_dates=['time_stamp_utc'])


    

    replacement_data_col_names = list(df.columns)

    # Match column names between the two tables
    match_cols_dict = {}
    for existing_db_column in existing_table_column_names:
        try:
            index = replacement_data_col_names.index(existing_db_column)
            match_cols_dict[existing_db_column] = replacement_data_col_names[index]
        except ValueError:
            match_cols_dict[existing_db_column] = None


    if request.method == "POST":
        formDict = request.form.to_dict()
        print(f"- search_rincons POST -")
        print("formDict: ", formDict)

        # TODO: upload data to existing database
        ### formDict (key) is existing databaes column name
        # existing_names_list = [existing for existing, update in formDict.items() if update != 'true' ]
        
        # check for default values and remove from formDict
        set_default_value_dict = {}
        for key, value in formDict.items():
            if key[:len("default_checkbox_")] == "default_checkbox_":
                set_default_value_dict[value] = formDict.get(value)
        
        print("- set_default_value_dict -")
        print(set_default_value_dict)


        # Delete elements from dictionary
        for key, value in set_default_value_dict.items():
            del formDict[key]
            checkbox_key = "default_checkbox_" + key
            del formDict[checkbox_key]




        print("- formDict adjusted -")
        print(formDict)

        existing_names_list = []
        for key, value in formDict.items():
            if value != 'true':
                existing_names_list.append(key)
            
            
        df_update = pd.DataFrame(columns=existing_names_list)

        # value is the new data (aka the uploaded csv file column)
        for exisiting, replacement in formDict.items():
            if not replacement in ['true','']:
                # print(replacement)
                df_update[exisiting]=df[replacement].values

        # Add in columns with default values
        for column_name, default_value in set_default_value_dict.items():
            if column_name == 'time_stamp_utc': 
                df_update[column_name] = datetime.utcnow()
            else:
                df_update[column_name] = default_value

        
        # remove existing users from upload
        # NOTE: There needs to be a user to upload data
        if table_name == 'users':
            print("--- Found users table ---")
            existing_users = sess.query(Users).all()
            list_of_emails_in_db = [i.email for i in existing_users]
            for email in list_of_emails_in_db:
                df_update.drop(df_update[df_update.email== email].index, inplace = True)
                print(f"-- removeing {email} from upload dataset --")
        
        # print("- df_update -")
        # print(df_update)

        # if table_name == 'users':
        #     # encode password column
        #     print("len(df_update)", len(df_update))
            for index in range(1,len(df_update)+1):
                df_update.loc[index, 'password'] = df_update.loc[index, 'password'].encode()
                print(" ****************** ")
                print(f"- encoded row for {df_update.loc[index, 'email']} -")
                print(" ****************** ")


        df_update.to_sql(table_name, con=engine, if_exists='append', index=False)

        flash(f"{table_name} update: successful!", "success")

        print("request.path: ", request.path)
        print("request.full_path: ", request.full_path)
        print("request.script_root: ", request.script_root)
        print("request.base_url: ", request.base_url)
        print("request.url: ", request.url)
        print("request.url_root: ", request.url_root)
        print("______")


        # return redirect(request.url)
        return redirect(url_for('admin.admin_db_upload'))


    
    return render_template('admin/upload_table.html', table_name=table_name, 
        match_cols_dict = match_cols_dict,
        existing_table_column_names=existing_table_column_names,
        replacement_data_col_names = replacement_data_col_names)



@admin.route('/nrodrig1_admin', methods=["GET"])
def nrodrig1_admin():
    nrodrig1 = sess.query(Users).filter_by(email="nrodrig1@gmail.com").first()
    if nrodrig1 != None:
        nrodrig1.admin = True
        sess.commit()
        flash("nrodrig1@gmail updated to admin", "success")
    return redirect(url_for('main.home'))

