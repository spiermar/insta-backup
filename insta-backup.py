#!/usr/bin/python
import json

import sys

import ConfigParser
import urlparse
from instagram.client import InstagramAPI
from instagram.helper import datetime_to_timestamp

config = ConfigParser.ConfigParser()
config.read('insta-backup.cfg')

access_token = config.get('insta-backup', 'access_token')
api = InstagramAPI(access_token=access_token)


def get_basic_info():

    return api.user()


def get_likes(media_id):
    likes = []

    response = api.media_likes(media_id)

    for like_item in response:
        likes.append(like_item)

    return likes


def get_comments(media_id):
    comments = []

    response = api.media_comments(media_id)

    for comment_item in response:
        comments.append(comment_item)

    return comments


def get_requested_by():

    return api.user_incoming_requests()


def get_media(media=None, max_id=None):

    if media is None:
        media = []

    response, next = api.user_recent_media(max_id=max_id)

    for media_item in response:
        # if media_item.like_count > 3:
        #     likes = get_likes(media_item.id)
        #     setattr(media_item, 'likes', likes)

        if media_item.comment_count > 3:
            comments = get_comments(media_item.id)
            setattr(media_item, 'comments', comments)

        media.append(media_item)

    if next is not None:
        parsednext = urlparse.urlparse(next)
        max_id = urlparse.parse_qs(parsednext.query)['max_id'][0]
        media = get_media(media, max_id)

    return media


def user_to_dict(user):
    user_dict = {
        'id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'profile_picture': user.profile_picture
    }

    if hasattr(user, 'counts'):
        user_dict["counts"] = user.counts

    if hasattr(user, 'bio'):
        user_dict['bio'] = user.bio

    if hasattr(user, 'website'):
        user_dict['website'] = user.website

    return user_dict


def image_to_dict(image):
    image_dict = {
        'url': image.url,
        'height': image.height,
        'width': image.width
    }

    return image_dict


def comment_to_dict(comment):
    comment_dict = {
        'id': comment.id,
        'text': comment.text,
        'created_time': datetime_to_timestamp(comment.created_at),
        'from': user_to_dict(comment.user)
    }

    return comment_dict


def point_to_dict(point):
    point_dict = {
        'latitude': point.latitude,
        'longitude': point.longitude
    }

    return point_dict


def location_to_dict(location):
    location_dict = {
        'id': location.id,
        'name': location.name
    }

    point_dict = None

    if location.point is not None:
        point_dict = point_to_dict(location.point)

    location_dict['point'] = point_dict

    return location_dict


def tag_to_dict(tag):
    tag_dict = {
        'name': tag.name
    }

    return tag_dict


def position_to_dict(position):
    position_dict = {
        'x': position.x,
        'y': position.y
    }

    return position_dict


def user_in_photo_to_dict(user_in_photo):
    user_in_photo_dict = {
        'user': user_to_dict(user_in_photo.user),
        'position': position_to_dict(user_in_photo.position)
    }

    return user_in_photo_dict


def media_to_dict(media):
    media_dict = {
        'id': media.id,
        'user': user_to_dict(media.user),
        'images': {},
        'videos': {},
        'user_has_liked': media.user_has_liked,
        'like_count': media.like_count,
        'likes': [],
        'comment_count': media.comment_count,
        'comments': [],
        'created_time': datetime_to_timestamp(media.created_time),
        'location': None,
        'caption': None,
        'tags': [],
        'users_in_photo': [],
        'link': media.link,
        'filter': media.filter
    }

    if hasattr(media, 'images'):
        for version, image in media.images.iteritems():
            media_dict['images'][version] = image_to_dict(image)

    if hasattr(media, 'videos'):
        for version, video in media.videos.iteritems():
            media_dict['videos'][version] = image_to_dict(video)

    if hasattr(media, 'likes'):
        for like in media.likes:
            media_dict['likes'].append(user_to_dict(like))

    if hasattr(media, 'comments'):
        for comment in media.comments:
            media_dict['comments'].append(comment_to_dict(comment))

    if hasattr(media, 'location'):
        media_dict['location'] = location_to_dict(media.location)

    if hasattr(media, 'caption'):
        if media.caption is not None:
            media_dict['caption'] = comment_to_dict(media.caption)

    if hasattr(media, 'tags'):
        for tag in media.tags:
            media_dict['tags'].append(tag_to_dict(tag))

    if hasattr(media, 'users_in_photo'):
        for user_in_photo in media.users_in_photo:
            media_dict['users_in_photo'].append(user_in_photo_to_dict(user_in_photo))

    return media_dict


def get_following(following=None, cursor=None):
    if following is None:
        following = []

    response, next = api.user_follows(cursor=cursor)

    for following_item in response:
        following.append(following_item)

    if next is not None:
        parsednext = urlparse.urlparse(next)
        cursor = urlparse.parse_qs(parsednext.query)['cursor'][0]
        following = get_following(following, cursor)

    return following


def get_followed(followed=None, cursor=None):
    if followed is None:
        followed = []

    response, next = api.user_followed_by(cursor=cursor)

    for followed_item in response:
        followed.append(followed_item)

    if next is not None:
        parsednext = urlparse.urlparse(next)
        cursor = urlparse.parse_qs(parsednext.query)['cursor'][0]
        followed = get_followed(followed, cursor)

    return followed


def get_liked(liked=None, max_like_id=None):
    if liked is None:
        liked = []

    response, next = api.user_liked_media(max_like_id=max_like_id)

    for liked_item in response:
        liked.append(liked_item)

    if next is not None:
        parsednext = urlparse.urlparse(next)
        max_like_id = urlparse.parse_qs(parsednext.query)['max_like_id'][0]
        liked = get_liked(liked, max_like_id)

    return liked


def main(argv):
    backup = {
        'media': [],
        'following': [],
        'followed': [],
        'liked': [],
        'requested': []
    }

    media_files = []
    liked_media_files = []
    profile_pics = {}

    user = get_basic_info()
    backup['user'] = user_to_dict(user)

    media = get_media()
    print 'Media: ' + str(len(media))
    for media_item in media:
        backup['media'].append(media_to_dict(media_item))
        media_files.append(media_item.images.get('standard_resolution').url)
        if hasattr(media_item, 'videos'):
            media_files.append(media_item.videos.get('standard_resolution').url)

    following = get_following()
    print 'Following: ' + str(len(following))
    for following_user in following:
        backup['following'].append(user_to_dict(following_user))
        profile_pics[following_user.username] = following_user.profile_picture

    followed = get_followed()
    print 'Followed: ' + str(len(followed))
    for followed_user in followed:
        backup['followed'].append(user_to_dict(followed_user))
        profile_pics[followed_user.username] = followed_user.profile_picture

    liked = get_liked()
    print 'Liked: ' + str(len(liked))
    for liked_media in liked:
        backup['liked'].append(media_to_dict(liked_media))
        liked_media_files.append(liked_media.images.get('standard_resolution').url)
        if hasattr(liked_media, 'videos'):
            liked_media_files.append(liked_media.videos.get('standard_resolution').url)

    requested = get_requested_by()
    print 'Requested: ' + str(len(requested))
    for requested_user in requested:
        backup['requested'].append(user_to_dict(requested_user))

    f = open('/Users/mspier/Desktop/backup.json', 'wb')
    f.write(json.dumps(backup, indent=4))
    f.close()

    f = open('/Users/mspier/Desktop/media.txt', 'wb')
    for media_file in media_files:
        f.write(media_file + '\n')
    f.close()

    f = open('/Users/mspier/Desktop/liked_media.txt', 'wb')
    for liked_media_file in liked_media_files:
        f.write(liked_media_file + '\n')
    f.close()

    f = open('/Users/mspier/Desktop/profile_pics.json', 'wb')
    f.write(json.dumps(profile_pics, indent=4))
    f.close()


if __name__ == "__main__":
   main(sys.argv[1:])