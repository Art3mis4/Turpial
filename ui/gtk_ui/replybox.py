# -*- coding: utf-8 -*-

# Widget para mostrar respuestas de un tweet en Turpial
#
# Author: Wil Alvarez (aka Satanas)
# Feb 02, 2010

import gtk

from waiting import*
from tweetslist import *
from ui import util as util

class ReplyBox(gtk.Window):
    def __init__(self, parent):
        gtk.Window.__init__(self)
        
        self.working = True
        self.mainwin = parent
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.set_title('En respuesta a...')
        self.set_resizable(False)
        self.set_size_request(500, 150)
        self.set_transient_for(parent)
        self.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        
        self.tweets = TweetList(parent, 'En respuesta a...')
        
        self.waiting = CairoWaiting(self)
        self.lblerror = gtk.Label()
        self.lblerror.set_use_markup(True)
        error_align = gtk.Alignment(xalign=0.0)
        error_align.add(self.lblerror)
        
        top = gtk.VBox(False)
        top.pack_start(self.tweets, True, True, 5)
        
        bottom = gtk.HBox(False)
        bottom.pack_start(self.waiting, False, False, 5)
        bottom.pack_start(error_align, True, True, 4)
        #bottom.pack_start(abuttonbox, True, True, 5)
        
        vbox = gtk.VBox(False)
        vbox.pack_start(top, True, True, 2)
        #vbox.pack_start(updatebox, True, True, 2)
        vbox.pack_start(bottom, False, False, 2)
        #vbox.pack_start(self.toolbox, False, False, 2)
        
        self.add(vbox)
        
        self.connect('delete-event', self.__unclose)
        self.connect('size-request', self.__size_request)
    
    def __size_request(self, widget, event, data=None):
        w, h = self.get_size()
        self.tweets.update_wrap(w)
        
    def __unclose(self, widget, event=None):
        if not self.working: self.hide()
        return True
        
    def show(self, id, user):
        self.in_reply_id = id
        self.in_reply_user = user
        self.set_title('En respuesta a %s' % user)
        self.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.tweets.clear()
        self.waiting.start()
        self.show_all()
        
    def update(self, tweets):
        self.working = False
        if not tweets or (len(tweets) == 0): 
            self.waiting.stop(error=True)
            self.lblerror.set_markup(u"<span size='small'>Oops... algo salío mal</span>")
            return
        
        self.waiting.stop()
        self.tweets.update_tweets(tweets)
