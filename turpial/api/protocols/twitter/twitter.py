# -*- coding: utf-8 -*-

"""Implementación del protocolo Twitter para Turpial"""
#
# Author: Wil Alvarez (aka Satanas)
# May 25, 2010

from turpial.api.interfaces.protocol import Protocol
from turpial.api.protocols.twitter.twitterhttp import TwitterHTTP
from turpial.api.interfaces.post import Status, Response, Profile, RateLimit


class Twitter(Protocol):
    def __init__(self):
        Protocol.__init__(self, 'Twitter', 'http://twitter.com', 
            'http://search.twitter.com')
        
        self.http = TwitterHTTP()
        
    #def __validate_args(self, args, names):
    def __get_real_tweet(self, tweet):
        '''Get the tweet retweeted'''
        retweet_by = None
        if tweet.has_key('retweeted_status'):
            retweet_by = tweet['user']['screen_name']
            tweet = tweet['retweeted_status']
        
        return tweet, retweet_by
        
    def __create_status(self, resp):
        tweet, retweet_by = self.__get_real_tweet(resp)
        
        if tweet.has_key('user'):
            username = tweet['user']['screen_name']
            avatar = tweet['user']['profile_image_url']
        elif tweet.has_key('sender'):
            username = tweet['sender']['screen_name']
            avatar = tweet['sender']['profile_image_url']
        elif tweet.has_key('from_user'):
            username = tweet['from_user']
            avatar = tweet['profile_image_url']
        
        in_reply_to_id = None
        in_reply_to_user = None
        if tweet.has_key('in_reply_to_status_id') and \
           tweet['in_reply_to_status_id']:
            in_reply_to_id = tweet['in_reply_to_status_id']
            in_reply_to_user = tweet['in_reply_to_screen_name']
            
        fav = False
        if tweet.has_key('favorited'):
            fav = tweet['favorited']
        source = None
        if tweet.has_key('source'):
            source = tweet['source']
        
        status = Status()
        status.id = tweet['id']
        status.username = username
        status.avatar = avatar
        status.source = source
        status.text = tweet['text']
        status.in_reply_to_id = in_reply_to_id
        status.in_reply_to_user = in_reply_to_user
        status.is_favorite = fav
        status.retweet_by = retweet_by
        status.datetime = tweet['created_at']
        return status
        
    def __create_profile(self, pf):
        profile = Profile()
        profile.id = pf['id']
        profile.fullname = pf['name']
        profile.username = pf['screen_name']
        profile.avatar = pf['profile_image_url']
        profile.location = pf['location']
        profile.url = pf['url']
        profile.bio = pf['description']
        profile.following = pf['following']
        profile.followers_count = pf['followers_count']
        profile.friends_count = pf['friends_count']
        profile.statuses_count = pf['statuses_count']
        profile.profile_link_color = pf['profile_link_color']
        return profile
        
    def __create_rate(self, rl):
        rate = RateLimit()
        rate.hourly_limit = rl['hourly_limit']
        rate.remaining_hits = rl['remaining_hits']
        rate.reset_time = rl['reset_time']
        rate.reset_time_in_seconds = rl['reset_time_in_seconds']
        return rate
        
    def response_to_statuses(self, response, mute=False):
        statuses = []
        for resp in response:
            statuses.append(self.__create_status(resp))
        return statuses
        
    def response_to_profiles(self, response):
        profiles = []
        for pf in response:
            profiles.append(self.__create_profile(pf))
        return Response(profiles, 'profile')
            
    def auth(self, args):
        ''' Inicio de autenticacion basica '''
        self.log.debug('Iniciando autenticacion basica')
        username = args['username']
        password = args['password']
        
        try:
            self.http.set_credentials(username, password)
            rtn = self.http.request('%s/account/verify_credentials' % 
                self.apiurl)
            self.profile = self.__create_profile(rtn)
            self.profile.password = password
            return Response(self.profile, 'profile')
        except Exception, exc:
            return Response(None, 'error', exc.msg)
        
    def get_timeline(self, args):
        '''Actualizando linea de tiempo'''
        self.log.debug('Descargando timeline')
        count = args['count']
        
        try:
            rtn = self.http.request('%s/statuses/home_timeline' % 
                self.apiurl, {'count': count})
            self.timeline = self.response_to_statuses(rtn)
            return Response(self.get_muted_timeline(), 'status')
        except Exception, exc:
            return Response(None, 'error', exc.msg)
        
    def get_replies(self, args):
        '''Actualizando menciones'''
        self.log.debug('Descargando menciones')
        count = args['count']
        
        try:
            rtn = self.http.request('%s/statuses/mentions' % 
                self.apiurl, {'count': count})
            self.replies = self.response_to_statuses(rtn)
            return Response(self.replies, 'status')
        except Exception, exc:
            return Response(None, 'error', exc.msg)
        
    def get_directs(self, args):
        '''Actualizando mensajes directos'''
        self.log.debug('Descargando directos')
        count = args['count']
        
        try:
            rtn = self.http.request('%s/direct_messages' % self.apiurl, 
                {'count': count})
            self.directs = self.response_to_statuses(rtn)
            return Response(self.directs, 'status')
        except Exception, exc:
            return Response(None, 'error', exc.msg)
        
    def get_favorites(self):
        '''Actualizando favoritos'''
        self.log.debug('Descargando favoritos')
        
        try:
            rtn = self.http.request('%s/favorites' % self.apiurl)
            self.favorites = self.response_to_statuses(rtn)
            return Response(self.favorites, 'status')
        except Exception, exc:
            return Response(None, 'error', exc.msg)
        
    def get_rate_limits(self):
        '''Actualizando llamdas restantes a la api'''
        try:
            rtn = self.http.request('%s/account/rate_limit_status' % 
                self.apiurl)
            return Response(self.__create_rate(rtn), 'rate')
        except Exception, exc:
            return Response(None, 'error', exc.msg)
        
    def get_conversation(self, args):
        '''Obteniendo conversacion'''
        id = args['id']
        conversation = []
        
        self.log.debug(u'Obteniendo conversación:')
        
        while 1:
            try:
                rtn = self.http.request('%s/statuses/show' % self.apiurl, 
                    {'id': id})
            except Exception, exc:
                return Response(None, 'error', exc.msg)
                
            self.log.debug('--Descargado Tweet: %s' % id)
            conversation.append(rtn)
            
            if rtn['in_reply_to_status_id']:
                id = str(rtn['in_reply_to_status_id'])
            else:
                break
        
        return Response(self.response_to_statuses(conversation), 'profile')
        
    def get_friends_list(self):
        '''Descargando lista de amigos'''
        tries = 0
        count = 0
        cursor = -1
        friends = []
        
        self.log.debug('Descargando Lista de Amigos')
        while 1:
            try:
                rtn = self.http.request('%s/statuses/friends' % self.apiurl, 
                    {'cursor': cursor})
            except Exception, exc:
                tries += 1
                if tries < 6:
                    continue
                else:
                    return Response(None, 'error', exc.msg)
                
            for user in rtn['users']:
                friends.append(self.__create_profile(user))
                count += 1
            if rtn['next_cursor'] > 0:
                cursor = rtn['next_cursor']
                continue
            else:
                break
        
        self.friends = friends
        self.log.debug('--Descargados %i amigos' % count)
        self.friendsloaded = True
        
        return self.friends
        
    def update_profile(self, name, url, bio, location):
        '''Actualizando perfil'''
        self.log.debug('Actualizando perfil')
        
        try:
            rtn = self.http.request('%s/account/update_profile' % self.apiurl, 
                {'name': name, 'url': url, 'location': location, 
                'description': bio})
            return Response(rtn, 'profile')
        except Exception, exc:
            return Response(None, 'error', exc.msg)
        
    def update_status(self, in_reply_to_id):
        '''Actualizando estado'''
        if in_reply_id:
            args = {'status': text, 'in_reply_to_status_id': in_reply_id}
        else:
            args = {'status': text}
        self.log.debug(u'Nuevo tweet: %s' % text)
        
        try:
            rtn = self.http.request('%s/statuses/update' % self.apiurl, args)
            self._add_status(self.timeline, rtn)
            return Response(self.timeline, 'status')
        except Exception, exc:
            return Response(None, 'error', exc.msg)
        
    def destroy_status(self, id):
        '''Destruyendo tweet'''
        self.to_del.append(id)
        self.log.debug('Destruyendo tweet: %s' % id)
        
        try:
            rtn = self.http.request('%s/statuses/destroy' % self.apiurl,
                {'id': id})
            self._destroy_status(rtn['id'])
            return Response(self.timeline, 'status'), 
            Response(self.favorites, 'status')
        except Exception, exc:
            return Response(None, 'error', exc.msg), Response(None, 'error', exc.msg)
        
    def repeat(self, id):
        '''Haciendo retweet'''
        self.log.debug('Retweet: %s' % id)
        
        try:
            rtn = self.http.request('%s/statuses/retweet' % self.apiurl, 
                {'id': id})
            # FIXME: Insertarlo en el timeline
            return Response(self.timeline, 'status')
        except Exception, exc:
            return Response(None, 'error', exc.msg)
        
    def mark_favorite(self, args):
        '''Marcando tweet como favorito'''
        id = args['id']
        self.to_fav.append(id)
        self.log.debug('Marcando tweet como favorito: %s' % id)
        
        try:
            rtn = self.http.request('%s/favorites/create' % self.apiurl, 
                {'id': id})
            self._set_status_favorite(rtn['id'])
            return (Response(self.timeline, 'status'), 
                Response(self.replies, 'status'),
                Response(self.favorites, 'status'))
        except Exception, exc:
            return (Response(None, 'error', exc.msg), 
                Response(None, 'error', exc.msg), 
                Response(None, 'error', exc.msg))
        
    def unmark_favorite(self, args):
        '''Desmarcando tweet como favorito'''
        id = args['id']
        self.to_fav.append(id)
        self.log.debug('Desmarcando tweet como favorito: %s' % id)
        
        try:
            rtn = self.http.request('%s/favorites/destroy' % self.apiurl, 
                {'id': id})
            self._unset_status_favorite(rtn['id'])
            return (Response(self.timeline, 'status'), 
                Response(self.replies, 'status'),
                Response(self.favorites, 'status'))
        except Exception, exc:
            return (Response(None, 'error', exc.msg), 
                Response(None, 'error', exc.msg), 
                Response(None, 'error', exc.msg))
        
    def follow(self, user):
        '''Siguiendo a un amigo'''
        self.log.debug('Siguiendo a: %s' % user)
        
        try:
            rtn = self.http.request('%s/friendships/create' % self.apiurl,
                {'screen_name': user})
            user = self.__create_profile(rtn)
            self._add_friend(user)
            return Response([self._get_single_friends_list(), self.profile, 
                user, True], 'mixed')
        except Exception, exc:
            return Response(None, 'error', exc.msg)
        
    def unfollow(self, user):
        '''Dejando de seguir a un amigo'''
        self.log.debug('Dejando de seguir a: %s' % user)
        
        try:
            rtn = self.http.request('%s/friendships/destroy' % self.apiurl,
                {'screen_name': user})
            user = self.__create_profile(rtn)
            self._del_friend(user)
            return Response([self._get_single_friends_list(), self.profile, 
                user, False], 'mixed')
        except Exception, exc:
            return Response(None, 'error', exc.msg)
        
    def send_direct(self, user, text):
        pass
        
    def destroy_direct(self, id):
        '''Destruyendo tweet directo'''
        self.to_del.append(id)
        self.log.debug('Destruyendo directo: %s' % id)
        
        try:
            rtn = self.http.request('%s/direct_messages/destroy' % self.apiurl,
                {'id': id})
            self._destroy_status(id)
            return Response(self.directs, 'status')
        except Exception, exc:
            return Response(None, 'error', exc.msg)
        
    def search(self, query, count=100):
        ''' Buscando en Twitter '''
        self.log.debug('Buscando tweets: %s' % query)
        
        try:
            rtn = self.http.request('%s/search' % self.apiurl2, 
                {'q': query, 'rpp': count})
            return Response(rtn, 'status')
        except Exception, exc:
            return Response(None, 'error', exc.msg)
        