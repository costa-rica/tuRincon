from flask import Blueprint
from flask import render_template, url_for, redirect, flash, request, \
    abort, session, Response, current_app, send_from_directory, make_response
# import bcrypt
from flask_login import login_required, login_user, logout_user, current_user
import os
import logging
from logging.handlers import RotatingFileHandler
from tr01_models import sess, Users, Rincons, RinconsPosts, UsersToRincons, \
    RinconsPostsComments, RinconsPostsLikes, RinconsPostsCommentsLikes
import shutil
from werkzeug.utils import secure_filename
import json
from app_package.main.utils import get_post_dict, extract_urls_info


main = Blueprint('main', __name__)

formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

logger_main = logging.getLogger(__name__)
logger_main.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(os.path.join(os.environ.get('WEB_ROOT'),'logs','main_routes.log'), mode='a', maxBytes=5*1024*1024,backupCount=2)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

logger_main.addHandler(file_handler)
logger_main.addHandler(stream_handler)


@main.route("/", methods=["GET","POST"])
def home():
    logger_main.info(f"-- in home page route --")
    if current_user.is_authenticated:
        return redirect(url_for('main.rincons'))



    if request.method == "POST":
        formDict = request.form.to_dict()

    return render_template('main/home.html')


@main.route("/rincons", methods=["GET", "POST"])
def rincons():
        
    users_rincons_list = [(i.rincons_table_id, i.rincon.name) for i in current_user.rincons]

    return render_template('main/rincons.html',users_rincons_list=users_rincons_list )


@main.route("/search_rincons", methods=["GET", "POST"])
def search_rincons():

    print(f"- search_rincons -")
    column_names = ["ID", "Name", "Manager Name"]
    rincon_list = request.args.getlist('rincon_list') if request.args.get('rincon_list') != None else request.args.get('rincon_list') 
    search_string = request.args.get('search_string')
    
    if request.method == "POST":
        formDict = request.form.to_dict()
        print(f"- search_rincons POST -")
        print("formDict: ", formDict)      

        if formDict.get('reset_search') == 'true':
            print("- RESET_search")
            rincon_list = None
            return redirect(url_for('main.search_rincons', rincon_list=rincon_list))

        elif formDict.get('join'):
            print("- JOIN was selected -")
            new_member = UsersToRincons(users_table_id = current_user.id, rincons_table_id= int(formDict.get('join')))
            sess.add(new_member)
            sess.commit()
            print("Rincon ID: ", formDict.get('join'))
            rincon_name = sess.get(Rincons,int(formDict.get('join'))).name

            flash("Added to Rincon", "success")
            # return redirect(url_for('main.search_rincons', rincon_list=rincon_list))
            return redirect(url_for('main.rincon', rincon_name=rincon_name, rincon_id=int(formDict.get('join')) ) )

        elif formDict.get('leave'):
            print("- leave was selected -")

            # TODO: This doesn't work - figure out deleteing from association table (UsersToRincons)

            # sess.query(UsersToRincons,(current_user.id, int(formDict.get('leave')))).delete()
            sess.query(UsersToRincons).filter_by(users_table_id =current_user.id, rincons_table_id= int(formDict.get('leave'))).delete()
            sess.commit()
            print("Rincon ID: ", formDict.get('leave'))
            flash("Removed to Rincon", "warning")
            return redirect(url_for('main.search_rincons', rincon_list=rincon_list))
        else:
            search_string = formDict.get("search_string")
            print(f"- search_string: {search_string} -")
            if search_string != "":
                search_list = sess.query(Rincons).filter(Rincons.name.contains(search_string))
            else:
                print("- get all the rincons -")
                search_list = sess.query(Rincons).all()

            # rincon list id, name of rincon, manager name, is user alraedy a member
            rincon_list = []
            for rincon in search_list:
                temp_list =[]
                print('** rincon.public: ', rincon.public)
                if rincon.public:
                    temp_list.append(rincon.id)
                    temp_list.append(rincon.name)
                    temp_list.append(sess.get(Users, rincon.manager_id).username)
                    members_id_list = [i.users_table_id for i in rincon.users]
                    member = True if current_user.id in members_id_list else False
                    temp_list.append(member)
                    rincon_list.append(temp_list)

    return render_template('main/rincons_search.html', rincon_list=rincon_list, column_names=column_names, search_string=search_string )


@main.route("/create_rincon", methods=["GET", "POST"])
@login_required
def create_rincon():

    print(f"current_user: {current_user.username}")
    if request.method == "POST":
        formDict = request.form.to_dict()

        print(f"formDict: {formDict}")

        public = False
        if formDict.get('public_checkbox') == 'true':
            public = True
        if formDict.get('rincon_name') != "":
            
            rincon_name_no_spaces = formDict.get('rincon_name').replace(" ","_")

            #create_rincon
            new_rincon = Rincons(name= formDict.get('rincon_name'), manager_id=current_user.id, 
                public=public, name_no_spaces = rincon_name_no_spaces)
            sess.add(new_rincon)
            sess.commit()

            #add current_user as member
            new_member = UsersToRincons(users_table_id = current_user.id, rincons_table_id= new_rincon.id)
            sess.add(new_member)
            sess.commit()

            #create static/rincon_files/<id_rincon_name>
            direcotry_name = f"{new_rincon.id}_{rincon_name_no_spaces}"
            new_dir_path = os.path.join(current_app.static_folder,"rincon_files", direcotry_name)
            # print(new_dir_path)
            os.mkdir(new_dir_path)

            flash("Rincon successfully created!", "success")
            
            return redirect(url_for('main.rincons'))
        
        flash("Rincon needs name", "warning")

        return redirect(url_for('main.create_rincon'))



    return render_template('main/create_rincon.html')


@main.route("/rincon/<rincon_name>", methods=["GET","POST"])
def rincon(rincon_name):
    
    rincon_id = request.args.get('rincon_id')
    # if user signed in redirect
    print(dir(current_user))
    print("current_user: ", current_user.is_authenticated)
    
    if current_user.is_authenticated:

        return redirect(url_for('main.rincon_signed_in', rincon_id=rincon_id, rincon_name=rincon_name))
    
    # rincon = sess.get(Rincons, int(rincon_id))
    rincon = sess.query(Rincons).filter_by(name_no_spaces=rincon_name).first()

    if not rincon.public:
        flash("Register and search for a rincoón.", "warning")
        return redirect(url_for('users.register', rincon_id=rincon_id))




    rincon_posts = []
    for i in rincon.posts:
        temp_dict = {}

        temp_dict['post_id'] = i.id
        temp_dict['date_for_sorting'] = i.time_stamp_utc
        temp_dict['username'] = sess.get(Users,i.user_id).username

        #search for http in i.text


        # temp_dict['text'] = i.text
        temp_dict['text'] = extract_urls_info(i.text)
        # print(temp_dict['text'])



        print("-- what is image ---")
        print(i.image_file_name)
        temp_dict['image_exists'] = False if i.image_file_name == None else True
        temp_dict['image_name_and_path'] = f"rincon_files/{rincon_id}_{rincon.name_no_spaces}/{i.image_file_name}"
        temp_dict['date'] = i.time_stamp_utc.strftime("%m/%d/%y %H:%M")
        temp_dict['delete_post_permission'] = False

        comments_list = []
        for comment in i.comments:
            temp_sub_dict = {}
            temp_sub_dict['date'] = comment.time_stamp_utc.strftime("%m/%d/%y %H:%M")
            temp_sub_dict['username'] = sess.get(Users,comment.user_id).username
            temp_sub_dict['text'] = comment.text
            temp_sub_dict['delete_comment_permission'] = False
            temp_sub_dict['comment_id'] = comment.id
            comments_list.append(temp_sub_dict)
        temp_dict['comments'] = comments_list
        rincon_posts.append(temp_dict)

    rincon_posts = sorted(rincon_posts, key=lambda d: d['date_for_sorting'], reverse=True)


    return render_template('main/rincon_template.html', rincon_name=rincon_name, rincon_posts=rincon_posts, rincon=rincon)

@main.route("/rincon_signed_in/<rincon_name>", methods=["GET","POST"])
@login_required
def rincon_signed_in(rincon_name):
    rincon_id = request.args.get('rincon_id')
    print("- rincon page -")

    # print("rincon_id: ", rincon_id)
    rincon = sess.get(Rincons, int(rincon_id))
    # print(f"rincon: {rincon}")
    # print(f"rincon posts: {rincon.posts}")
    rincon_posts = []
    for i in rincon.posts:
        temp_dict = {}

        temp_dict['post_id'] = i.id
        temp_dict['date_for_sorting'] = i.time_stamp_utc
        temp_dict['username'] = sess.get(Users,i.user_id).username

        #search for http in i.text


        # temp_dict['text'] = i.text
        temp_dict['text'] = extract_urls_info(i.text)
        # print(temp_dict['text'])



        print("-- what is image ---")
        print(i.image_file_name)
        temp_dict['image_exists'] = False if i.image_file_name == None else True
        temp_dict['image_path'] = f"{rincon_id}_{rincon.name_no_spaces}"
        temp_dict['image_filename'] = f"{i.image_file_name}"

        temp_dict['date'] = i.time_stamp_utc.strftime("%m/%d/%y %H:%M")
        temp_dict['delete_post_permission'] = False if i.user_id != current_user.id else True

        comments_list = []
        for comment in i.comments:
            temp_sub_dict = {}
            temp_sub_dict['date'] = comment.time_stamp_utc.strftime("%m/%d/%y %H:%M")
            temp_sub_dict['username'] = sess.get(Users,comment.user_id).username
            temp_sub_dict['text'] = comment.text
            temp_sub_dict['delete_comment_permission'] = False if comment.user_id != current_user.id else True
            temp_sub_dict['comment_id'] = comment.id
            comments_list.append(temp_sub_dict)
        temp_dict['comments'] = comments_list
        rincon_posts.append(temp_dict)

    rincon_posts = sorted(rincon_posts, key=lambda d: d['date_for_sorting'], reverse=True)



    if request.method == "POST":
        formDict = request.form.to_dict()
        print(f"- search_rincons POST -")
        print("formDict: ", formDict)

        requestFiles = request.files

        if formDict.get('btn_delete_rincon') and formDict.get('text_delete')==rincon.name:
            print("- ENTERED in if for btn_delete -")

            return redirect(url_for('main.delete_rincon', rincon_id=rincon_id))
        elif formDict.get('btn_post'):

            # get text save a new_post entry
            post_text = formDict.get('post_text')
            new_post = RinconsPosts(text=post_text,user_id=current_user.id, rincon_id=rincon.id)
            sess.add(new_post)
            sess.commit()

            if request.files.get('add_photo_file'):
                print("*********")
                print("- posting an image -")
                # get image
                post_image = request.files.get('add_photo_file')
                post_image_filename = post_image.filename
                _, file_extension = os.path.splitext(post_image_filename)
                logger_main.info(f"-- Get image file name --")
                logger_main.info(f"-- file_extension: {file_extension} --")



                ## rename image
                new_image_name = f"post_image_{new_post.id}{file_extension}"

                ## save to static rincon directory
                this_rincon_dir_name = f"{rincon_id}_{rincon.name_no_spaces}"
                # path_to_rincon_files = os.path.join(current_app.static_folder, "rincon_files",this_rincon_dir_name)
                path_to_rincon_files = os.path.join(current_app.config.get('DB_ROOT'), "rincon_files",this_rincon_dir_name)

                post_image.save(os.path.join(path_to_rincon_files, new_image_name))

                # save new image name in post entry
                new_post.image_file_name = new_image_name
                sess.commit()

            return redirect(request.url)
        
        elif formDict.get('btn_comment'):
            print("- Receieved Comment -")

            # add to RinconsPostsComments
            new_comment = RinconsPostsComments(post_id=formDict.get('post_id'),user_id=current_user.id,
                rincon_id=rincon.id,
                text= formDict.get('comment_text')
            )
            sess.add(new_comment)
            sess.commit()
            return redirect(request.url)

        elif formDict.get('btn_delete_post'):

            # TODO: delete photo
            rincon_post = sess.get(RinconsPosts, formDict.get('btn_delete_post'))


            if rincon_post.image_file_name != None:
                post_image_path_and_name = os.path.join(current_app.static_folder, "rincon_files", f"{rincon.id}_{rincon.name_no_spaces}",rincon_post.image_file_name)
            
                print("post_image_path_and_name: ", post_image_path_and_name)
                if os.path.exists(post_image_path_and_name):
                    os.remove(post_image_path_and_name)
            sess.query(RinconsPosts).filter_by(id = formDict.get('btn_delete_post')).delete()
            sess.query(RinconsPostsLikes).filter_by(post_id = formDict.get('btn_delete_post')).delete()
            sess.query(RinconsPostsComments).filter_by(post_id = formDict.get('btn_delete_post')).delete()
            sess.query(RinconsPostsCommentsLikes).filter_by(post_id = formDict.get('btn_delete_post')).delete()
            sess.commit()

            

            return redirect(request.url)

        elif formDict.get('btn_delete_comment'):
            sess.query(RinconsPostsComments).filter_by(id = formDict.get('btn_delete_comment')).delete()
            sess.query(RinconsPostsCommentsLikes).filter_by(comment_id = formDict.get('btn_delete_comment')).delete()
            sess.commit()
            return redirect(request.url)
            


    return render_template('main/rincon_template.html', rincon_name=rincon_name, rincon_posts=rincon_posts, rincon=rincon)


@main.route("/delete/<rincon_id>", methods=["GET"])
@login_required
def delete_rincon(rincon_id):
    print("- Entered delete/rinocon route -")

    rincon = sess.get(Rincons, rincon_id)
    # remove static rincon_dir folder
    static_dir_name = os.path.join(current_app.static_folder, "rincon_files", f"{rincon.id}_{rincon.name}")


    if os.path.isdir(static_dir_name):
        # os.remove(static_dir_name)
        shutil.rmtree(static_dir_name)

    # last thing: Delete rincon from rincons table
    sess.query(Rincons).filter_by(id=rincon_id).delete()
                
    # delete Association Table link
    sess.query(UsersToRincons).filter_by(users_table_id=current_user.id ,rincons_table_id=rincon_id ).delete()

    sess.query(RinconsPosts).filter_by(rincon_id = rincon_id).delete()
    sess.query(RinconsPostsLikes).filter_by(rincon_id = rincon_id).delete()
    sess.query(RinconsPostsComments).filter_by(rincon_id = rincon_id).delete()
    sess.query(RinconsPostsCommentsLikes).filter_by(rincon_id = rincon_id).delete()


    sess.commit()

    return redirect(url_for('main.rincons'))



# Custom static data
@main.route('/<image_path>/<image_filename>')
def custom_static(image_path, image_filename):
    print("-- enterd custom static -")
    # name_no_spaces = ""
    
    return send_from_directory(os.path.join(current_app.config.get('DB_ROOT'),"rincon_files", \
        image_path), image_filename)

