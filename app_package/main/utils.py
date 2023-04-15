import logging
from logging.handlers import RotatingFileHandler
from tr01_models import sess, Users, Rincons, RinconsPosts, UsersToRincons, \
    RinconsPostsComments, RinconsPostsLikes, RinconsPostsCommentsLikes
import os
import re
import urlextract


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
    # # case no http found
    # if len(http_start_pos) == 0:
    #     post_dict['text'+str(counter)] = post_string
    # # case where only http is found: 1 
    # elif len(http_start_pos)==1:
    # # else:
    #     ## http start start of post_string
    #     if len(spaces_start_pos) == 0:
    #         post_dict['link'+str(counter)] = post_string
    #     else:
    #         index=0
    #         print(f"http: {http_start_pos[0]}; spaces: {spaces_start_pos[index]}")
    #         for link_loc in http_start_pos:
    #             while spaces_start_pos[index] < link_loc:
    #                 index += 1
    #             if http_start_pos[0] != 0:
    #                 post_dict['text'+str(counter)] = post_string[:link_loc]
    #             post_dict['link'+str(counter)] = post_string[link_loc:spaces_start_pos[index]]
            
    #         post_dict['text'+str(counter+1)] = post_string[spaces_start_pos[index]:]
    post_dict = {"text":post_string}

    return post_dict



# def extract_url_info(text):
#     extractor = urlextract.URLExtract()
#     urls = extractor.find_urls(text)
    
#     if len(urls) != 1:
#         # raise ValueError("Input string must contain exactly one URL")
#         return {"text":text}
    
#     url = urls[0]
#     split_text = text.split(url)
    
#     return {
#         "text01": split_text[0],
#         "url01": url,
#         "text02": split_text[1]
#     }

# def extract_urls_info(text):
#     extractor = urlextract.URLExtract()
#     urls = extractor.find_urls(text)
#     original_text = text
#     if len(urls) == 0:
#         return {"text": text}
    
#     url_dict = {}
    
#     for i, url in enumerate(urls):
#         split_text = text.split(url)
#         url_dict[f"text{i+1:02d}"] = split_text[0]
#         url_dict[f"url{i+1:02d}"] = url
#         # try:
#         text = split_text[1]
#         # except:
#         #     print("*** Error parsing:", original_text)
#         #     return {"text": text}
#     url_dict[f"text{len(urls)+1:02d}"] = text
    
#     return url_dict

def extract_urls_info(text):
    extractor = urlextract.URLExtract()
    urls = extractor.find_urls(text)
    
    if len(urls) == 0:
        return {"text":text}


    url_dict = {}
    
    # Handle the case where the first character(s) is a URL
    if text.startswith(urls[0]):
        url_dict[f"url01"] = urls[0]
        text = text[len(urls[0]):]
    
    # Handle the case where the last character(s) is a URL
    if text.endswith(urls[-1]):
        url_dict[f"url{len(urls):02d}"] = urls[-1]
        text = text[:-len(urls[-1])]
    
    # Handle all other URLs
    for i, url in enumerate(urls):
        if i == 0 and "url01" in url_dict:
            continue
        if i == len(urls) - 1 and f"url{len(urls):02d}" in url_dict:
            continue
        split_text = text.split(url)
        url_dict[f"text{i+1:02d}"] = split_text[0]
        url_dict[f"url{i+1:02d}"] = url
        text = split_text[1]
    
    # Handle any remaining text after the last URL
    if text:
        url_dict[f"text{len(urls)+1:02d}"] = text
    
    return url_dict