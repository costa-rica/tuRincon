import logging
from logging.handlers import RotatingFileHandler
from tr01_models import sess, Users, Rincons, RinconsPosts, UsersToRincons, \
    RinconsPostsComments, RinconsPostsLikes, RinconsPostsCommentsLikes
import os
import re
import urlextract
from flask_login import current_user


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



def get_post_dict(post_string):
    spaces_start_pos = [spaces.start() for spaces in re.finditer(" ", post_string)]
    http_start_pos = [spaces.start() for spaces in re.finditer("https://", post_string)]
    post_dict = {}
    counter = 1

    post_dict = {"text":post_string}

    return post_dict


def extract_urls_info(feed_obj_text):
    extractor = urlextract.URLExtract()
    urls = extractor.find_urls(feed_obj_text)
    
    if len(urls) == 0:
        return {"text":feed_obj_text}


    url_dict = {}
    
    # Handle the case where the first character(s) is a URL
    if feed_obj_text.startswith(urls[0]):
        url_dict[f"url01"] = urls[0]
        feed_obj_text = feed_obj_text[len(urls[0]):]
    
    # # Handle the case where the last character(s) is a URL
    # if feed_obj_text.endswith(urls[-1]):
    #     url_dict[f"url{len(urls):02d}"] = urls[-1]
    #     feed_obj_text = feed_obj_text[:-len(urls[-1])]
    
    # Handle all other URLs
    for i, url in enumerate(urls):
        if i == 0 and "url01" in url_dict:
            continue
        if i == len(urls) - 1 and f"url{len(urls):02d}" in url_dict:
            continue
        split_text = feed_obj_text.split(url)
        url_dict[f"text{i+1:02d}"] = split_text[0]
        url_dict[f"url{i+1:02d}"] = url
        feed_obj_text = split_text[1]
    
    # Handle any remaining text after the last URL
    if feed_obj_text:
        url_dict[f"text{len(urls)+1:02d}"] = feed_obj_text
    
    # url_dict_list =[{i,j} for i,j in url_dict.items()]
    # url_tup_list =[(i,j) for i,j in url_dict.items()]


    return url_dict


def create_rincon_posts_list(rincon_id):

    rincon = sess.get(Rincons,rincon_id)

    rincon_posts = []
    if current_user.is_authenticated:
        user_likes = current_user.post_like
        user_likes_this_rincon = [like.post_id  for like in user_likes if like.rincon_id == rincon.id]


    for i in rincon.posts:
        temp_dict = {}

        temp_dict['post_id'] = i.id
        temp_dict['date_for_sorting'] = i.time_stamp_utc
        temp_dict['username'] = sess.get(Users,i.user_id).username

        temp_dict['post_text'] = extract_urls_info(i.post_text)

        temp_dict['image_exists'] = False if i.image_file_name == None else True
        temp_dict['image_path'] = f"{rincon_id}_{rincon.name_no_spaces}"
        temp_dict['image_filename'] = f"{i.image_file_name}"
        temp_dict['date'] = i.time_stamp_utc.strftime("%m/%d/%y %H:%M")
        
        if current_user.is_authenticated:
            temp_dict['liked'] = False if i.id not in user_likes_this_rincon else True
        
        temp_dict['like_count'] = len(i.post_like)

        if current_user.is_authenticated:
            temp_dict['delete_post_permission'] = False if i.user_id != current_user.id else True
        else:
            temp_dict['delete_post_permission'] = False

        comments_list = []
        for comment in i.comments:
            temp_sub_dict = {}
            temp_sub_dict['date'] = comment.time_stamp_utc.strftime("%m/%d/%y %H:%M")
            temp_sub_dict['username'] = sess.get(Users,comment.user_id).username
            temp_sub_dict['comment_text'] = comment.comment_text
            if current_user.is_authenticated:
                temp_sub_dict['delete_comment_permission'] = False if comment.user_id != current_user.id else True
            else:
                temp_sub_dict['delete_comment_permission'] = False

            temp_sub_dict['comment_id'] = comment.id
            comments_list.append(temp_sub_dict)
        temp_dict['comments'] = comments_list
        rincon_posts.append(temp_dict)

    rincon_posts = sorted(rincon_posts, key=lambda d: d['date_for_sorting'], reverse=True)

    return rincon_posts


