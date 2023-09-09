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
from app_package.main.utils import get_post_dict, extract_urls_info, \
    create_rincon_posts_list, send_invite_email, addUserToRinconAccessNotAdmin, \
    addUserToRinconFullAccess

from sqlalchemy import exc

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
    logger_main.info("- Search Rincón -")

    column_names = ["ID", "Name", "Manager Name"]
    rincon_list = request.args.getlist('rincon_list') if request.args.get('rincon_list') != None else request.args.get('rincon_list') 
    search_string = request.args.get('search_string')
    
    if request.method == "POST":
        formDict = request.form.to_dict()

        if formDict.get('reset_search') == 'true':
            logger_main.info("- RESET_search")
            rincon_list = None
            return redirect(url_for('main.search_rincons', rincon_list=rincon_list))

        elif formDict.get('join'):
            logger_main.info(f"- Selected JOIN {formDict.get('join')} -")
            rincon_id = int(formDict.get('join'))
            # new_member = UsersToRincons(users_table_id = current_user.id, rincons_table_id= rincon_id)
            # sess.add(new_member)
            # sess.commit()
            addUserToRinconAccessNotAdmin(current_user.id, rincon_id)

            rincon_name = sess.get(Rincons,rincon_id).name

            flash("Added to Rincon", "success")
            # return redirect(url_for('main.search_rincons', rincon_list=rincon_list))
            return redirect(url_for('main.rincon', rincon_id=rincon_id, rincon_name = rincon_name))

        elif formDict.get('leave'):
            logger_main.info("- leave was selected -")

            # TODO: This doesn't work - figure out deleteing from association table (UsersToRincons)

            # sess.query(UsersToRincons,(current_user.id, int(formDict.get('leave')))).delete()
            sess.query(UsersToRincons).filter_by(users_table_id =current_user.id, rincons_table_id= int(formDict.get('leave'))).delete()
            sess.commit()
            print("Rincon ID: ", formDict.get('leave'))
            flash("Removed to Rincon", "warning")
            return redirect(url_for('main.search_rincons', rincon_list=rincon_list))
        else:
            search_string = formDict.get("search_string")
            logger_main.info(f"- search_string: {search_string} -")
            if search_string != "":
                search_list = sess.query(Rincons).filter(Rincons.name.contains(search_string))
            else:
                print("- get all the rincons -")
                search_list = sess.query(Rincons).all()

            # rincon list id, name of rincon, manager name, is user alraedy a member
            rincon_list = []
            for rincon in search_list:
                temp_list =[]
                # if public or current_user already a memeber of rincon
                if rincon.public or (current_user.id in [i.users_table_id for i in rincon.users]):
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
    logger_main.info("- Create Rincón -")
    if request.method == "POST":
        formDict = request.form.to_dict()


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
            # new_member = UsersToRincons(users_table_id = current_user.id, rincons_table_id= new_rincon.id)
            # sess.add(new_member)
            # sess.commit()
            addUserToRinconFullAccess(current_user.id, new_rincon.id)

            #create static/rincon_files/<id_rincon_name>
            direcotry_name = f"{new_rincon.id}_{rincon_name_no_spaces}"
            new_dir_path = os.path.join(current_app.config.get('DB_ROOT'),"rincon_files", direcotry_name)


            # print(new_dir_path)
            os.mkdir(new_dir_path)

            flash("Rincon successfully created!", "success")
            
            return redirect(url_for('main.rincons'))
        
        flash("Rincon needs name", "warning")

        return redirect(url_for('main.create_rincon'))



    return render_template('main/create_rincon.html')



@main.route("/rincon/<rincon_id>", methods=["GET","POST"])
# @login_required
def rincon(rincon_id):
    logger_main.info("- Rincon page -")
    try:
        rincon = sess.get(Rincons, int(rincon_id))
        rincon_name = rincon.name
    except ValueError:
        rincons = sess.query(Rincons).filter_by(name= rincon_id).all()
        if len(rincons) != 1:
            abort(404, description="Might be more than one rincon with that name. Go back to search.")
        else:
            rincon = rincons[0]
            rincon_name = rincon.name
            rincon_id = rincon.id
            
    logger_main.info(f"- Rincon: {rincon_name} -")

    if not current_user.is_authenticated and not rincon.public:
        return current_app.login_manager.unauthorized()
    
    if current_user.is_authenticated:
        current_user_rincon_assoc_table_obj = sess.query(UsersToRincons).filter_by(users_table_id=current_user.id, rincons_table_id=rincon_id).first()
    else:
        current_user_rincon_assoc_table_obj = None
        

    rincon_posts = create_rincon_posts_list(rincon_id)
    # print("- rincon_posts -")
    # print(rincon_posts[0])

    if request.method == "POST":
        formDict = request.form.to_dict()
        print(f"- search_rincons POST -")
        print("formDict: ", formDict)

        requestFiles = request.files
        print("--------------------")
        print(requestFiles)
        # print(dir(requestFiles))

        if formDict.get('btn_delete_rincon') and formDict.get('text_delete')==rincon.name:
            print("- ENTERED in if for btn_delete -")

            return redirect(url_for('main.delete_rincon', rincon_id=rincon_id))

        elif formDict.get('btn_post'):

            # get text save a new_post entry
            post_text = formDict.get('post_text')
            new_post = RinconsPosts(post_text=post_text,user_id=current_user.id, rincon_id=rincon.id)
            sess.add(new_post)
            sess.commit()

            if request.files.get('add_file_photo'):
                # print(len(requestFiles.getlist('add_file_photo')))
                print(requestFiles.getlist('add_file_photo'))

                print("- posting an image -")
                post_image_list = requestFiles.getlist('add_file_photo')
                post_image_counter = 1

                for post_image in post_image_list:

                    post_image_filename = post_image.filename
                    _, file_extension = os.path.splitext(post_image_filename)
                    logger_main.info(f"-- file_extension: {file_extension} --")

                    ## rename image
                    new_image_name = f"post_{new_post.id}_image_{post_image_counter}{file_extension}"

                    ## save to static rincon directory
                    this_rincon_dir_name = f"{rincon_id}_{rincon.name_no_spaces}"
                    # path_to_rincon_files = os.path.join(current_app.static_folder, "rincon_files",this_rincon_dir_name)
                    path_to_rincon_files = os.path.join(current_app.config.get('DB_ROOT'), "rincon_files",this_rincon_dir_name)

                    post_image.save(os.path.join(path_to_rincon_files, new_image_name))

                    # save new image name in post entry
                    if new_post.image_file_name == "" or new_post.image_file_name == None:
                        new_post.image_file_name = new_image_name
                        
                    else:
                        new_post.image_file_name = new_post.image_file_name + "," + new_image_name
                    sess.commit()

                    post_image_counter += 1

                return redirect(request.url)
        


            elif request.files.get('add_file_video'):

                print(requestFiles.get('add_file_video'))
                post_video = requestFiles.get('add_file_video')
                # post_image_counter = 1

                # for post_image in post_image_list:

                post_video_file_name = post_video.filename
                _, file_extension = os.path.splitext(post_video_file_name)
                logger_main.info(f"-- file_extension: {file_extension} --")

                ## rename image
                new_video_name = f"post_{new_post.id}_video{file_extension}"

                ## save to static rincon directory
                this_rincon_dir_name = f"{rincon_id}_{rincon.name_no_spaces}"
                # path_to_rincon_files = os.path.join(current_app.static_folder, "rincon_files",this_rincon_dir_name)
                path_to_rincon_files = os.path.join(current_app.config.get('DB_ROOT'), "rincon_files",this_rincon_dir_name)

                post_video.save(os.path.join(path_to_rincon_files, new_video_name))

                # save new image name in post entry
                if new_post.video_file_name == "" or new_post.video_file_name == None:
                    new_post.video_file_name = new_video_name
                    
                else:
                    new_post.video_file_name = new_post.video_file_name + "," + new_video_name
                sess.commit()

                # post_image_counter += 1

                return redirect(request.url)





        elif formDict.get('btn_comment'):
            print("- Receieved Comment -")

            # add to RinconsPostsComments
            new_comment = RinconsPostsComments(post_id=formDict.get('comment_on_post_id'),user_id=current_user.id,
                rincon_id=rincon.id,
                comment_text= formDict.get('comment_text')
            )
            sess.add(new_comment)
            sess.commit()
            return redirect(request.url)

        elif formDict.get('btn_delete_post'):
            logger_main.info(f"---- deleteing post ----")
            rincon_post = sess.get(RinconsPosts, formDict.get('btn_delete_post'))

            if rincon_post.image_file_name != None:
                image_names = rincon_post.image_file_name.split(",")
                for image_name in image_names:
                    post_image_path_and_name = os.path.join(current_app.config.get('DB_ROOT'), "rincon_files", f"{rincon.id}_{rincon.name_no_spaces}",image_name)
                
                    logger_main.info(f"post_image_path_and_name: {post_image_path_and_name}")
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
            

    return render_template('main/rincon.html', rincon_name=rincon.name, rincon_posts=rincon_posts,
        rincon=rincon, len=len, current_user_rincon_assoc_table_obj=current_user_rincon_assoc_table_obj)


@main.route("/post_images/<rincon_id>/<post_id>")
def post_images(rincon_id,post_id):

    logger_main.info("- Rincon signed in page -")
    try:
        rincon = sess.get(Rincons, int(rincon_id))
        rincon_name = rincon.name
    except ValueError:
        rincons = sess.query(Rincons).filter_by(name= rincon_id).all()
        if len(rincons) != 1:
            abort(404, description="Might be more than one rincon with that name. Go back to search.")
        else:
            rincon = rincons[0]
            rincon_name = rincon.name
            rincon_id = rincon.id
            
    
    if not current_user.is_authenticated and not rincon.public:
        return current_app.login_manager.unauthorized()


    if current_user.is_authenticated:
        current_user_rincon_assoc_table_obj = sess.query(UsersToRincons).filter_by(users_table_id=current_user.id, rincons_table_id=rincon_id).first()
    else:
        current_user_rincon_assoc_table_obj = None

    rincon_post = sess.query(RinconsPosts).filter_by(id = post_id).first()

    post_images_path = f"{rincon_id}_{rincon.name_no_spaces}"

    if not rincon_post.image_file_name.find(","):
        photos_list =  [rincon_post.image_file_name]
    else:
        photos_list =  rincon_post.image_file_name.split(",")

    return render_template('/main/post_images.html', photos_list=photos_list, post_images_path = post_images_path,
        rincon_name=rincon_name, current_user_rincon_assoc_table_obj=current_user_rincon_assoc_table_obj,
        rincon=rincon)


@main.route("/delete/<rincon_id>", methods=["GET"])
@login_required
def delete_rincon(rincon_id):
    logger_main.info("- Entered delete/rinocon route -")

    rincon = sess.get(Rincons, rincon_id)
    # remove static rincon_dir folder
    static_dir_name = os.path.join(current_app.config.get('DB_ROOT'), "rincon_files", f"{rincon.id}_{rincon.name_no_spaces}")


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
    # print("-- enterd custom static -")
    # name_no_spaces = ""
    
    return send_from_directory(os.path.join(current_app.config.get('DB_ROOT'),"rincon_files", \
        image_path), image_filename)


@main.route('/like_post/<rincon_id>/<post_id>/')
@login_required
def like_post(rincon_id,post_id):
    logger_main.info(f"- Like {rincon_id} {post_id} -")

    rincon_id = int(rincon_id)
    post_id = int(post_id)
    post_like = sess.query(RinconsPostsLikes).filter_by(rincon_id=rincon_id, post_id=post_id, user_id=current_user.id).first()
    
    if post_like:
        print("- post already LIKED -")
        sess.query(RinconsPostsLikes).filter_by(rincon_id=rincon_id, post_id=post_id, user_id=current_user.id).delete()
        sess.commit()
    else:
        print("- post NOT liked")
        new_post_like = RinconsPostsLikes(rincon_id=rincon_id, post_id=post_id, user_id=current_user.id, post_like=True)
        sess.add(new_post_like)
        sess.commit()


    # new_post_like = RinconsPostsLikes(rincon_id=rincon_id, post_id=post_id, user_id=current_user.id, post_like=True)
    # sess.add(new_post_like)
    # sess.commit()

    # post_like = sess.query(RinconsPostsLikes).filter_by(rincon_id=rincon_id, post_id=post_id, user_id=current_user.id).first()
    print("Post Like:", post_like)



    # return redirect(request.referrer, _anchor='like_'+post_id)
    return redirect(url_for('main.rincon', rincon_id=rincon_id,post_id=post_id, _anchor='like_'+str(post_id)))


@main.route('/admin/<rincon_id>/', methods=["GET","POST"])
@login_required
def rincon_admin(rincon_id):
    logger_main.info(f"- accessed rincon_admin for rincon_id: {rincon_id}  -")
    rincon = sess.query(Rincons).filter_by(id=rincon_id).first()
    rincon_name = rincon.name
    current_user_rincon_assoc_table_obj =  sess.query(UsersToRincons).filter_by(users_table_id=current_user.id, rincons_table_id=rincon.id).first()
    
    if request.method == "POST":
        # print("posting somethign ...")
        formDict = request.form.to_dict()
        # print(formDict)

        # get email
        invite_email = formDict.get("input_email")
        logger_main.info("invite_email: ", invite_email)

        # try to add email to rincon
        try:
            invited_user = sess.query(Users).filter_by(email = invite_email).first()

            #check if invited user already member
            if sess.query(UsersToRincons).filter_by(users_table_id=invited_user.id, rincons_table_id = rincon_id).first():
                logger_main.info(f"{invite_email} already part of Rincon")
                flash(f"{invite_email} already part of Rincon", "warning")
                return redirect(request.url)

            new_user_rincon_assoc = UsersToRincons(users_table_id=invited_user.id, rincons_table_id = rincon_id)
            sess.add(new_user_rincon_assoc)
            sess.commit()

            # # send email
            # send_invite_email(invite_email, rincon)
            # flash(f"Email sent to {invite_email}", "success")
            # return redirect(request.url)

        except AttributeError:# Make/add to invitation_json_file_path_and_name

            logger_main.info("user not found")


            # search for invitations file
            invitation_json_file_path_and_name = os.path.join(current_app.config.get("DB_ROOT"), "rincon_files","pending_rincon_invitations.json")
            if os.path.exists(invitation_json_file_path_and_name):
                invitation_json_file = open(invitation_json_file_path_and_name)
                invite_dict = json.load(invitation_json_file)
                invitation_json_file.close()

                if invite_dict.get(invite_email):# dict entry for email already exits, append to it
                    list_of_invited_email_invites = invite_dict.get(invite_email)


                    if int(rincon_id) not in list_of_invited_email_invites:
                        list_of_invited_email_invites.append([int(rincon_id),sess.get(Rincons, int(rincon_id)).name_no_spaces])
                        invite_dict[invite_email] = list_of_invited_email_invites
                        with open(invitation_json_file_path_and_name,'w') as invitation_json_file:
                            json.dump(invite_dict, invitation_json_file)
                    else:
                        logger_main.info(f"- {invite_email} invite already exists for {rincon_id}")

                else:# NO dict entry for email, make a new one
                    invite_dict[invite_email] = [[int(rincon_id),sess.get(Rincons, int(rincon_id)).name_no_spaces]]
                    with open(invitation_json_file_path_and_name,'w') as invitation_json_file:
                        json.dump(invite_dict, invitation_json_file)
                    


            else:# No json file, make a json file and make dict entry for email
                invite_dict = {}
                invite_dict[invite_email] = [[int(rincon_id),sess.get(Rincons, int(rincon_id)).name_no_spaces]]

                # print("*-- invitation dictioanry: ")
                # print(invite_dict)

                with open(invitation_json_file_path_and_name, "w") as invite_file:
                    json.dump(invite_dict,invite_file)


        # send email
        send_invite_email(invite_email, rincon)
        flash(f"Email sent to {invite_email}", "success")
        return redirect(request.url)

        # except exc.IntegrityError:
        #     sess.rollback()
        #     print("Already members")

        #     flash(f"{invite_email} already part of Rincon", "warning")
        #     return redirect(request.url)


    return render_template('main/rincon_admin.html', rincon=rincon,  current_user_rincon_assoc_table_obj=current_user_rincon_assoc_table_obj)


@main.route("/check_invite_json", methods=["GET"])
@login_required
def check_invite_json():

    logger_main.info("- accessed check_invite_json")
    logger_main.info(f"- url: {request.referrer}")


    requests.get()

    return redirect(request.referrer)



