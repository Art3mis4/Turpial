# -*- coding: utf-8 -*-

'''Modelo base basado en hilos para el Turpial'''
#
# Author: Wil Alvarez (aka Satanas)
# Dic 22, 2009

import sys
import time
import Queue
import urllib2
import logging
import threading
import traceback

from base64 import b64encode
from urllib import urlencode

from turpial.api import oauth
from turpial.api.oauth_client import TurpialAuthClient
from turpial.api.twitter_globals import POST_ACTIONS, \
                                        CONSUMER_KEY, \
                                        CONSUMER_SECRET

def _py26_or_greater():
    return sys.hexversion > 0x20600f0

if _py26_or_greater():
    import json
else:
    import simplejson as json
    
class TurpialAPI(threading.Thread):
    '''API basica de turpial basada en hilos'''
    def __init__(self):
        threading.Thread.__init__(self)
        
        self.setDaemon(False)
        self.log = logging.getLogger('API')
        self.queue = Queue.Queue()
        self.exit = False
        
        # OAuth stuffs
        self.client = None
        self.consumer = None
        self.is_oauth = False
        self.token = None
        self.signature_method_hmac_sha1 = None
        
        self.format = 'json'
        self.username = None
        self.password = None
        self.profile = None
        self.tweets = []
        self.replies = []
        self.directs = []
        self.favorites = []
        self.muted_users = []
        self.friends = []
        self.friendsloaded = False
        self.conversation = []
        self.apiurl = 'http://api.twitter.com/1'
        
        self.to_fav = []
        self.to_unfav = []
        self.to_del = []
        self.log.debug('Iniciado')
        
    def __register(self, args, callback):
        self.queue.put((args, callback))
    
    def __del_tweet_from(self, tweets, id):
        item = None
        for twt in tweets:
            if id == twt['id']:
                item = twt
                break
        if item:
            tweets.remove(item)
        return tweets
        
    def __change_tweet_from(self, tweets, id, key, value):
        index = None
        for twt in tweets:
            if id == twt['id']:
                index = tweets.index(twt)
                break
        if index:
            tweets[index][key] = value
        return tweets
        
    def __handle_oauth(self, args, callback):
        if args['cmd'] == 'start':
            if self.has_oauth_support():
                self.client = TurpialAuthClient()
            else:
                self.client = TurpialAuthClient(api_url=self.apiurl)
            self.consumer = oauth.OAuthConsumer(CONSUMER_KEY, CONSUMER_SECRET)
            self.signature_method_hmac_sha1 = oauth.OAuthSignatureMethod_HMAC_SHA1()
            auth = args['auth']
            
            if auth['oauth-key'] != '' and auth['oauth-secret'] != '' and \
            auth['oauth-verifier'] != '':
                self.token = oauth.OAuthToken(auth['oauth-key'],
                                              auth['oauth-secret'])
                self.token.set_verifier(auth['oauth-verifier'])
                self.is_oauth = True
                args['done'](self.token.key, self.token.secret,
                             self.token.verifier)
            else:
                self.log.debug('Obtain a request token')
                oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer,
                                                                           http_url=self.client.request_token_url)
                oauth_request.sign_request(self.signature_method_hmac_sha1,
                                           self.consumer, None)
                
                self.log.debug('REQUEST (via headers)')
                self.log.debug('parameters: %s' % str(oauth_request.parameters))
                try:
                    self.token = self.client.fetch_request_token(oauth_request)
                except Exception, error:
                    print "Error: %s\n%s" % (error, traceback.print_exc())
                    raise Exception
                
                self.log.debug('GOT')
                self.log.debug('key: %s' % str(self.token.key))
                self.log.debug('secret: %s' % str(self.token.secret))
                self.log.debug('callback confirmed? %s' % str(self.token.callback_confirmed))
                
                self.log.debug('Authorize the request token')
                oauth_request = oauth.OAuthRequest.from_token_and_callback(token=self.token,
                                                                           http_url=self.client.authorization_url)
                self.log.debug('REQUEST (via url query string)')
                self.log.debug('parameters: %s' % str(oauth_request.parameters))
                callback(oauth_request.to_url())
        elif args['cmd'] == 'authorize':
            pin = args['pin']
            self.log.debug('Obtain an access token')
            oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer,
                                                                       token=self.token,
                                                                       verifier=pin,
                                                                       http_url=self.client.access_token_url)
            oauth_request.sign_request(self.signature_method_hmac_sha1,
                                       self.consumer, self.token)
            self.log.debug('REQUEST (via headers)')
            self.log.debug('parameters: %s' % str(oauth_request.parameters))
            self.token = self.client.fetch_access_token(oauth_request)
            self.log.debug('GOT')
            self.log.debug('key: %s' % str(self.token.key))
            self.log.debug('secret: %s' % str(self.token.secret))
            self.is_oauth = True
            callback(self.token.key, self.token.secret, pin)
            
    def __handle_tweets(self, tweet, args):
        if tweet is None or tweet == []:
            return False
        
        if args.has_key('add'):
            exist = False
            for twt in self.tweets:
                try:
                    if tweet['id'] == twt['id']:
                        exist = True
                except Exception, error:
                    print 'Ha ocurrido un error:'
                    print error
                    print twt
                    print '---'
                    print tweet
                    continue
                    
            
            if not exist:
                self.tweets.insert(0, tweet)
        elif args.has_key('del'):
            if str(tweet['id']) in self.to_del:
                self.to_del.remove(str(tweet['id']))
            self.tweets = self.__del_tweet_from(self.tweets, tweet['id'])
            self.favorites = self.__del_tweet_from(self.favorites, tweet['id'])
            self.directs = self.__del_tweet_from(self.directs, tweet['id'])
            #print self.directs
        return True
        
    def __handle_retweets(self, tweet):
        '''Manejo de retweet'''
        if tweet is None or tweet == []:
            return False
        self.tweets = self.__change_tweet_from(self.tweets, tweet['id'],
            'retweeted_status', tweet['retweeted_status'])
        self.replies = self.__change_tweet_from(self.replies, tweet['id'],
            'retweeted_status', tweet['retweeted_status'])
        self.favorites = self.__change_tweet_from(self.favorites, tweet['id'],
            'retweeted_status', tweet['retweeted_status'])
        
        return True
        
    def __handle_muted(self):
        '''Manejo de amigos silenciados'''
        if len(self.muted_users) == 0:
            return self.tweets
        
        tweets = []
        for twt in self.tweets:
            if twt['user']['screen_name'] not in self.muted_users:
                tweets.append(twt)
                
        return tweets
        
    def __handle_favorites(self, tweet, fav):
        '''Manejo de tweet favorito'''
        if tweet is None or tweet == []:
            return False
        
        if fav:
            tweet['favorited'] = True
            self.favorites.insert(0, tweet)
            self.to_fav.remove(str(tweet['id']))
        else:
            self.favorites = self.__del_tweet_from(self.favorites, tweet['id'])
            self.to_unfav.remove(str(tweet['id']))
            
        self.tweets = self.__change_tweet_from(self.tweets, tweet['id'],
                                               'favorited', fav)
        self.replies = self.__change_tweet_from(self.replies, tweet['id'],
                                                'favorited', fav)
        
        return True
        
    def __handle_friends(self, rtn, done_callback, cursor):
        '''Manejo de amigos'''
        #FIXME: Problema con el valor devuelto
        if (rtn is None) or (not 'users' in rtn) or (not isinstance(rtn, dict)):
            print rtn
            self.log.debug('Error descargando amigos, intentando de nuevo')
            self.get_friends(done_callback, cursor)
        else:
            for p in rtn['users']:
                self.friends.append(p)
            
            if rtn['next_cursor'] > 0:
                self.get_friends(done_callback, rtn['next_cursor'])
            else:
                self.friendsloaded = True
                done_callback(self.friends)
                
    def __handle_conversation(self, rtn, done_callback):
        '''Manejo de conversaciones'''
        if rtn is None or rtn == []:
            self.log.debug(u'Error descargando conversación')
            done_callback(rtn)
        else:
            self.conversation.append(rtn)
            
            if rtn['in_reply_to_status_id']:
                self.get_conversation(str(rtn['in_reply_to_status_id']),
                                      done_callback, False)
            else:
                done_callback(self.conversation)
        
    def __handle_follow(self, user, follow):
        if follow:
            exist = False
            for u in self.friends:
                if user['id'] == u['id']:
                    exist = True
            
            if not exist: 
                self.friends.insert(0, user)
                self.profile['friends_count'] += 1
        else:
            item = None
            for u in self.friends:
                if user['id'] == u['id']:
                    item = u
                    break
            if item: 
                self.friends.remove(item)
                self.profile['friends_count'] -= 1
            
    def has_oauth_support(self):
        if self.apiurl != 'http://api.twitter.com/1':
            return False
        return True
        
    def change_api_url(self, new_url):
        if new_url == '': return
        self.log.debug('Cambiada la API URL a %s' % new_url)
        self.apiurl = new_url
        
    def is_friend(self, user):
        for f in self.friends:
            if user == f['screen_name']:
                return True
        return False
        
    def is_fav(self, tweet_id):
        for twt in self.tweets:
            if tweet_id == str(twt['id']):
                return twt['favorited']
        for twt in self.replies:
            if tweet_id == str(twt['id']):
                return twt['favorited']
        for twt in self.favorites:
            if tweet_id == str(twt['id']):
                return twt['favorited']

        
    def auth(self, username, password, callback):
        '''Inicio de autenticacion basica'''
        self.log.debug('Iniciando autenticacion basica')
        self.username = username
        self.password = password
        self.__register({'uri': '%s/account/verify_credentials' % self.apiurl,
                         'login':True}, callback)
        
    def start_oauth(self, auth, show_pin_callback, done_callback):
        '''Inicio de OAuth'''
        self.log.debug('Iniciando OAuth')
        self.__register({'cmd': 'start', 'oauth':True, 'auth': auth,
                         'done':done_callback}, show_pin_callback)
        
    def authorize_oauth_token(self, pin, callback):
        '''Solicitud de autenticacion del token'''
        self.log.debug('Solicitando autenticacion del token')
        self.__register({'cmd': 'authorize', 'oauth':True, 'pin': pin},
                        callback)
        
    def update_rate_limits(self, callback):
        self.__register({'uri': '%s/account/rate_limit_status' % self.apiurl},
                        callback)
        
    def update_timeline(self, callback, count=20):
        '''Actualizando linea de tiempo'''
        self.log.debug('Descargando Timeline')
        args = {'count': count}
        self.__register({'uri': '%s/statuses/home_timeline' % self.apiurl,
                         'args': args, 'timeline': True}, callback)
        
    def update_replies(self, callback, count=20):
        '''Actualizando respuestas'''
        self.log.debug('Descargando Replies')
        args = {'count': count}
        self.__register({'uri': '%s/statuses/mentions' % self.apiurl,
                         'args': args, 'replies': True}, callback)
        
    def update_directs(self, callback, count=20):
        '''Actualizando mensajes directos'''
        self.log.debug('Descargando Directs')
        args = {'count': count}
        self.__register({'uri': '%s/direct_messages' % self.apiurl,
                         'args': args, 'directs': True}, callback)
        
    def update_favorites(self, callback):
        '''Actualizando favoritos'''
        self.log.debug('Descargando Favorites')
        self.__register({'uri': '%s/favorites' % self.apiurl,
                         'favorites': True}, callback)
        
    def update_status(self, text, in_reply_id, callback):
        '''Actualizando estado'''
        if in_reply_id:
            args = {'status': text, 'in_reply_to_status_id': in_reply_id}
        else:
            args = {'status': text}
        self.log.debug(u'Nuevo tweet: %s' % text)
        self.__register({'uri': '%s/statuses/update' % self.apiurl,
                         'args': args, 'tweet':True, 'add': True}, callback)
        
    def destroy_status(self, tweet_id, callback):
        self.to_del.append(tweet_id)
        self.log.debug('Destruyendo tweet: %s' % tweet_id)
        self.__register({'uri': '%s/statuses/destroy' % self.apiurl,
                         'id': tweet_id, 'args': '', 'tweet':True,
                         'del': True}, callback)
        
    def retweet(self, tweet_id, callback):
        '''Haciendo retweet'''
        self.log.debug('Retweet: %s' % tweet_id)
        self.__register({'uri': '%s/statuses/retweet' % self.apiurl,
                         'id':tweet_id, 'rt':True, 'args': ''}, callback)
        
    def set_favorite(self, tweet_id, callback):
        '''Estableciendo tweet favorito'''
        self.to_fav.append(tweet_id)
        self.log.debug('Marcando como favorito tweet: %s' % tweet_id)
        self.__register({'uri': '%s/favorites/create' % self.apiurl,
                         'id':tweet_id, 'fav': True, 'args': ''}, callback)
        
    def unset_favorite(self, tweet_id, callback):
        '''Desmarcando tweet como favorito'''
        self.to_unfav.append(tweet_id)
        self.log.debug('Desmarcando como favorito tweet: %s' % tweet_id)
        self.__register({'uri': '%s/favorites/destroy' % self.apiurl,
                         'id':tweet_id, 'fav': False, 'args': ''}, callback)
    
    def search_topic(self, query, callback):
        '''Buscando tweet'''
        args = {'q': query, 'rpp': 50}
        self.log.debug('Buscando tweets: %s' % query)
        self.__register({'uri': 'http://search.twitter.com/search',
                         'args': args}, callback)
        
    def update_profile(self, name, url, bio, location, callback):
        '''Actualizando perfil'''
        args = {'name': name, 'url': url, 'location': location,
                'description': bio}
        self.log.debug('Actualizando perfil')
        self.__register({'uri': '%s/account/update_profile' % self.apiurl,
                         'args': args}, callback)
        
    def get_friends(self, callback, cursor= -1):
        '''Descargando lista de amigos'''
        args = {'cursor': cursor}
        self.log.debug('Descargando Lista de Amigos')
        self.__register({'uri': '%s/statuses/friends' % self.apiurl,
                         'args': args, 'done': callback, 'friends': True},
                         self.__handle_friends)
        
    def get_muted_list(self):
        if self.friendsloaded:
            friends = []
            for f in self.friends:
                friends.append(f['screen_name'])
            
            return friends, self.muted_users
        else:
            return None, None
            
    def follow(self, user, callback):
        '''Siguiendo a un amigo'''
        args = {'screen_name': user}
        self.log.debug('Siguiendo a: %s' % user)
        self.__register({'uri': '%s/friendships/create' % self.apiurl,
                         'args': args, 'follow': True}, callback)
        
    def unfollow(self, user, callback):
        '''Dejando de seguir a un amigo'''
        args = {'screen_name': user}
        self.log.debug('Dejando de seguir a: %s' % user)
        self.__register({'uri': '%s/friendships/destroy' % self.apiurl,
                         'args': args, 'follow': False}, callback)
        
    def mute(self, arg, callback):
        '''Actualizando usuarios silenciados'''
        if type(arg).__name__ == 'list':
            self.log.debug('Actualizando usuarios silenciados')
            self.muted_users = arg
        else:
            friends, _ = self.get_muted_list()
            if arg not in friends:
                self.log.debug('No se silencia a %s porque no es tu amigo' % arg)
            elif arg not in self.muted_users: 
                self.log.debug('Silenciando a %s' % arg)
                self.muted_users.append(arg)
        self.__register({'mute': True}, callback)
        
    def in_reply_to(self, tweet_id, callback):
        '''Buscando tweet en respuesta a'''
        self.log.debug('Buscando respuesta: %s' % tweet_id)
        self.__register({'uri': '%s/statuses/show' % self.apiurl,
                         'id': tweet_id}, callback)
        
    def get_conversation(self, tweet_id, callback, first=True):
        '''Obteniendo conversacion'''
        if first: 
            self.conversation = []
            self.log.debug(u'Obteniendo conversación:')
        self.log.debug('--Tweet: %s' % tweet_id)
        self.__register({'uri': '%s/statuses/show' % self.apiurl,
                         'id': tweet_id, 'done': callback,
                         'conversation': True}, self.__handle_conversation)
        
    def destroy_direct(self, tweet_id, callback):
        '''Destruyendo tweet directo'''
        self.to_del.append(tweet_id)
        self.log.debug('Destruyendo directo: %s' % tweet_id)
        self.__register({'uri': '%s/direct_messages/destroy' % self.apiurl,
                         'id': tweet_id, 'args': '', 'tweet':True,
                         'del': True}, callback)
        
    def get_single_friends_list(self):
        '''Returns a single friends list from the original twitter hash'''
        list = []
        for friend in self.friends:
            list.append(friend['screen_name'])
        return list
        
    def end_session(self):
        '''Finalizando sesion'''
        self.__register({'uri': '%s/account/end_session' % self.apiurl,
                         'args': '', 'exit': True}, None)
        
    def quit(self):
        '''Definiendo la salida'''
        self.exit = True
        
    def run(self):
        '''Bloque principal de ejecucion'''
        while not self.exit:
            try:
                req = self.queue.get(True, 0.3)
            except Queue.Empty:
                continue
            
            (args, callback) = req
            
            if self.exit:
                self.queue.task_done()
                break
                
            if args.has_key('oauth'):
                self.__handle_oauth(args, callback)
                continue
            
            if args.has_key('mute'):
                callback(self.__handle_muted())
                continue
            
            rtn = None
            argStr = ""
            argData = None
            encoded_args = None
            method = "GET"
            uri = args['uri']
                
            for action in POST_ACTIONS:
                if uri.endswith(action):
                    method = "POST"
            
            if args.has_key('id'):
                uri = "%s/%s" % (uri, args['id'])
                
            uri = "%s.%s" % (uri, self.format)
            
            if args.has_key('args'):
                encoded_args = urlencode(args['args'])
            
            if (method == "GET"):
                if encoded_args:
                    argStr = "?%s" % (encoded_args)
            else:
                argData = encoded_args
                
            if self.is_oauth:
                try:
                    params = args['args'] if args.has_key('args') else {}
                    oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer,
                                                                               token=self.token,
                                                                               http_method=method,
                                                                               http_url=uri,
                                                                               parameters=params)
                    oauth_request.sign_request(self.signature_method_hmac_sha1,
                                               self.consumer, self.token)
                    rtn = json.loads(self.client.access_resource(oauth_request,
                                                                 uri, method))
                    #if rtn.has_key('error'): rtn = None
                except urllib2.HTTPError, e:
                    rtn = []
                    print e
                    if args.has_key('login'): 
                        if e.code == 503 or e.code == 502:
                            rtn = {'error': 'Caramba, Twitter está sobrecargado'}
                        elif e.code == 401:
                            rtn = {'error': 'Credenciales inválidas'}
                        else:
                            rtn = {'error': 'Error %i from Twitter.com' % e.code}
                except Exception, e:
                    self.log.debug("Error for URL: %s using parameters: (%s)\ndetails: %s" % (uri, params, traceback.print_exc()))
                    if args.has_key('login'): 
                        rtn = {'error': 'Error from Twitter.com'}
            else:
                headers = {}
                if (self.username):
                    headers["Authorization"] = "Basic " + b64encode("%s:%s" % (self.username, self.password))
                strReq = "%s%s" % (uri, argStr)
                req = urllib2.Request("%s%s" % (uri, argStr), argData, headers)
                response = ''
                try:
                    # Use http://www.someproxy.com:3128 for http proxying
                    #proxies = {'http': 'http://www.someproxy.com:3128'}
                    #filehandle = urllib.urlopen(some_url, proxies=proxies)
                    handle = urllib2.urlopen(req)
                    response = handle.read()
                    rtn = json.loads(response)
                except urllib2.HTTPError, e:
                    if (e.code == 304):
                        rtn = []
                    else:
                        self.log.debug("Twitter sent status %i for URL: %s using parameters: (%s)\nDetails: %s\nRequest: %s\nResponse: %s" % (
                            e.code, uri, encoded_args, e.fp.read(), strReq, response))
                        if args.has_key('login'): 
                            if e.code == 503 or e.code == 502:
                                rtn = {'error': 'Caramba, Twitter está sobrecargado'}
                            elif e.code == 401:
                                rtn = {'error': 'Credenciales inválidas'}
                            else:
                                rtn = {'error': 'Error %i from Twitter.com' % e.code}
                except (urllib2.URLError, Exception), e:
                    self.log.debug("Problem to connect to twitter.com. Check network status.\nDetails: %s\nRequest: %s\nResponse: %s" % (
                        e, strReq, response))
                    if args.has_key('login'): 
                        rtn = {'error': 'Can\'t connect to twitter.com'}
            
            if self.exit:
                self.queue.task_done()
                break
                
            if args.has_key('login'): 
                self.profile = rtn
                
            if args.has_key('timeline'):
                if rtn:
                    self.tweets = rtn
                rtn = self.__handle_muted()
            elif args.has_key('replies'):
                if rtn:
                    self.replies = rtn
            elif args.has_key('directs'):
                if rtn:
                    self.directs = rtn
            elif args.has_key('favorites'):
                if rtn:
                    self.favorites = rtn
                callback(self.tweets, self.replies, self.favorites)
                continue
                
            if args.has_key('tweet'):
                #print 'rtn', rtn
                done = self.__handle_tweets(rtn, args)
                if done:
                    rtn = self.__handle_muted()
                if args.has_key('del'):
                    callback(rtn, self.replies, self.favorites, self.directs)
                    continue
            
            if args.has_key('rt'):
                done = self.__handle_retweets(rtn)
                if done: 
                    rtn = self.__handle_muted()
                    callback(rtn, self.replies, self.favorites)
                else:
                    callback(None, None, None)
                continue
                
            if args.has_key('fav'):
                done = self.__handle_favorites(rtn, args['fav'])
                callback(self.tweets, self.replies, self.favorites)
                #if done: 
                #    callback(self.tweets, self.replies, self.favorites)
                #else:
                #    callback(None,None,None)
                continue
                
            if args.has_key('friends'):
                callback(rtn, args['done'], args['args']['cursor'])
                continue
                
            if args.has_key('conversation'):
                callback(rtn, args['done'])
                continue
                
            if args.has_key('follow'):
                self.__handle_follow(rtn, args['follow'])
                callback(self.friends, self.profile, rtn, args['follow'])
                continue
                
            if args.has_key('exit'):
                self.exit = True
                self.queue.task_done()
            else:
                callback(rtn)
            
            self.queue.task_done()
            
        self.log.debug('Terminado')
        return
        
