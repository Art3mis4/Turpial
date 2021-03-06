# -*- coding: utf-8 -*-

"""Widget para mostrar respuestas de un tweet en Turpial"""
#
# Author: Wil Alvarez (aka Satanas)
# Feb 02, 2010

import gtk

from turpial.ui.gtk.tweetslist import TweetList

class ReplyBox(gtk.Window):
    def __init__(self, parent):
        gtk.Window.__init__(self)
        
        self.working = True
        self.mainwin = parent
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.set_title(_('In reply to...'))
        self.set_resizable(False)
        self.set_size_request(400, 300)
        self.set_transient_for(parent)
        self.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        
        self.tweets = TweetList(parent, _('In reply to...'))
        
        top = gtk.VBox(False, 0)
        top.pack_start(self.tweets, True, True, 0)
        
        self.add(top)
        
        self.connect('delete-event', self.__unclose)
        self.connect('size-request', self.__size_request)
    
    def __size_request(self, widget, event, data=None):
        w, h = self.get_size()
        self.tweets.update_wrap(w)
        
    def __unclose(self, widget, event=None):
        if not self.working:
            self.hide()
        return True
        
    def show(self, twt_id, user):
        self.in_reply_id = twt_id
        self.in_reply_user = user
        self.set_title(_('In reply to %s') % user)
        self.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.tweets.clear()
        self.tweets.start_update()
        self.show_all()
        
    def update(self, tweets):
        self.working = False
        if not tweets or (len(tweets) == 0): 
            self.tweets.stop_update(True, _('Oops... something went wrong'))
        else:
            self.tweets.stop_update()
            self.tweets.clear()
            self.tweets.update_tweets(tweets)

