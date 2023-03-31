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

    return render_template('home.html')


@main.route("/rincons", methods=["GET", "POST"])
def rincons():
        
    users_rincons_list = [(i.rincons_table_id, i.rincon.name) for i in current_user.rincons]

    return render_template('main/rincons.html',users_rincons_list=users_rincons_list )


@main.route("/search_rincons", methods=["GET", "POST"])
def search_rincons():

    print(f"- search_rincons -")

    rincon_list = request.args.get('rincon_list')
    print(f"rincon_list: {rincon_list}")
    print(type(rincon_list))
    if rincon_list == "reset" or rincon_list==None:
        rincon_list = "no_rincons"
    else:

        rincon_list = request.args.getlist('rincon_list')
        print("- converted rincon_list back to list - ")
        print(type(rincon_list))
        print(list(rincon_list[0])[0])
    column_names = ["ID", "Name", "Manager Name"]

    if request.method == "POST":
        formDict = request.form.to_dict()
        print(f"- search_rincons POST -")
        print("formDict: ", formDict)

        # print(f"reset_serach: {formDict.get('reset_search') }")
        

        if formDict.get('reset_search') == 'true':
            print("- RESET_search")
            rincon_list = "reset"
            return redirect(url_for('main.search_rincons', rincon_list=rincon_list))

        elif formDict.get('join'):
            print("- JOIN was selected -")
            new_member = UsersToRincons(users_table_id = current_user.id, rincons_table_id= int(formDict.get('join')))
            sess.add(new_member)
            sess.commit()
            print("Rincon ID: ", formDict.get('join'))
            flash("Added to Rincon", "success")
            return redirect(url_for('main.search_rincons', rincon_list=rincon_list))

        elif formDict.get('leave'):
            print("- leave was selected -")

            # TODO: This doesn't work - figure out deleteing from association table (UsersToRincons)

            sess.query(UsersToRincons,(current_user.id, int(formDict.get('leave')))).delete()
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
                temp_list.append(rincon.id)
                temp_list.append(rincon.name)
                temp_list.append(sess.get(Users, rincon.manager_id).username)
                members_id_list = [i.users_table_id for i in rincon.users]
                member = True if current_user.id in members_id_list else False
                temp_list.append(member)
                rincon_list.append(temp_list)

            
            print(f"rincon_list: {rincon_list }")
            print(f"rincon_list: {type(rincon_list) }")
            # return redirect(url_for('main.search_rincons', rincon_list=rincon_list, column_names=column_names))


    return render_template('main/rincons_search.html', rincon_list=rincon_list, column_names=column_names  )


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
            
            #create_rincon
            new_rincon = Rincons(name= formDict.get('rincon_name'), manager_id=current_user.id, public=public)
            sess.add(new_rincon)
            sess.commit()

            #add current_user as member
            new_member = UsersToRincons(users_table_id = current_user.id, rincons_table_id= new_rincon.id)
            sess.add(new_member)
            sess.commit()

            #create static/rincon_files/<id_rincon_name>
            direcotry_name = f"{new_rincon.id}_{new_rincon.name}"
            new_dir_path = os.path.join(current_app.static_folder,"rincon_files", direcotry_name)
            print(new_dir_path)
            os.mkdir(new_dir_path)

            flash("Rincon successfully created!", "success")
            
            return redirect(url_for('main.rincons'))
        
        flash("Rincon needs name", "warning")

        return redirect(url_for('main.create_rincon'))



    return render_template('main/create_rincon.html')


@main.route("/rincon/<rincon_name>", methods=["GET","POST"])
@login_required
def rincon(rincon_name):
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
        temp_dict['text'] = i.text
        temp_dict['image_name_and_path'] = f"rincon_files/{rincon_id}_{rincon.name}/{i.image}"
        temp_dict['date'] = i.time_stamp_utc.strftime("%m/%d/%y %H:%M")
        temp_dict['delete_post_permission'] = False if i.user_id != current_user.id else True
        # temp_dict['comments'] = {}
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
            # temp_list = []
            # temp_list.append(comment.time_stamp_utc.strftime("%m/%d/%y %H:%M"))
            # temp_list.append(sess.get(Users,comment.user_id).username)
            # temp_list.append(comment.text)
            # temp_dict['comments']=temp_list

        rincon_posts.append(temp_dict)

    # print("- rincon_posts -")
    # print(rincon_posts)
    # print(len(rincon_posts))

    # print("-- is this a dict? --")
    # print(type(rincon_posts[1]['comments']))
    # print(rincon_posts[1]['comments'])
    # print(rincon_posts[1]['comments']['text'])
    # print(rincon_posts)
    rincon_posts = sorted(rincon_posts, key=lambda d: d['date_for_sorting'], reverse=True)



    if request.method == "POST":
        formDict = request.form.to_dict()
        print(f"- search_rincons POST -")
        print("formDict: ", formDict)

        requestFiles = request.files

        if formDict.get('btn_delete') and formDict.get('text_delete')==rincon.name:
            print("- ENTERED in if for btn_delete -")

            return redirect(url_for('main.delete_rincon', rincon_id=rincon_id))
        elif formDict.get('btn_post'):

            # get text save a new_post entry
            post_text = formDict.get('post_text')
            new_post = RinconsPosts(text=post_text,user_id=current_user.id, rincon_id=rincon.id)
            sess.add(new_post)
            sess.commit()

            # get image
            post_image = request.files.get('add_photo_file')
            post_image_filename = post_image.filename
            _, file_extension = os.path.splitext(post_image_filename)

            ## rename image
            new_image_name = f"post_image_{new_post.id}.{file_extension}"

            ## save to static rincon directory
            this_rincon_dir_name = f"{rincon_id}_{rincon.name}"
            path_to_rincon_files = os.path.join(current_app.static_folder, "rincon_files",this_rincon_dir_name)
            post_image.save(os.path.join(path_to_rincon_files, new_image_name))

            # save new image name in post entry
            new_post.image = new_image_name
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
            


    return render_template('main/rincon_template.html', rincon_name=rincon_name, rincon_posts=rincon_posts)


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
    sess.commit()

    return redirect(url_for('main.rincons'))
