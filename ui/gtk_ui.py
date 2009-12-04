# -*- coding: utf-8 -*-

# Vista para Turpial en PyGTK
#
# Author: Wil Alvarez (aka Satanas)
# Nov 08, 2009

import gtk
import util
import time
import cairo
import pango
import urllib
import logging
import gobject

#from pic_downloader import *

gtk.gdk.threads_init()

log = logging.getLogger('Gtk')

class Wrapper(gtk.VBox):
    def __init__(self):
        gtk.VBox.__init__(self)
        
    def change_mode(self, mode):
        # Reimplementar en la clase hija
        pass
        
    def update_wrap(self, width, mode):
        # Reimplementar en la clase hija
        pass
        
class LoginLabel(gtk.DrawingArea):
    def __init__(self, parent):
        gtk.DrawingArea.__init__(self)
        self.par = parent
        self.error = None
        self.active = False
        self.connect('expose-event', self.expose)
        self.set_size_request(30, 25)
    
    def set_error(self, error):
        self.error = error
        self.active = True
        self.queue_draw()
        
    def expose(self, widget, event):
        cr = widget.window.cairo_create()
        cr.set_line_width(0.8)
        rect = self.get_allocation()
        
        cr.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
        cr.clip()
        
        cr.rectangle(0, 0, rect.width, rect.height)
        if not self.active: return
        
        cr.set_source_rgb(0, 0, 0)
        cr.fill()
        cr.select_font_face('Courier', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(12)
        cr.set_source_rgb(1, 0.87, 0)
        cr.move_to(10, 15)
        
        cr.text_path(self.error)
        cr.stroke()
        
        #cr.show_text(self.error)
        
class TweetList(gtk.ScrolledWindow):
    def __init__(self, label=''):
        gtk.ScrolledWindow.__init__(self)
        
        self.list = gtk.TreeView()
        self.list.set_headers_visible(False)
        self.list.set_events(gtk.gdk.POINTER_MOTION_MASK)
        self.list.set_level_indentation(0)
        self.list.set_rules_hint(True)
        self.list.set_resize_mode(gtk.RESIZE_IMMEDIATE)
        
        self.label = gtk.Label(label)
        
        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.set_shadow_type(gtk.SHADOW_IN)
        self.add(self.list)
        
        # avatar, username, datetime, client, message
        self.model = gtk.ListStore(gtk.gdk.Pixbuf, str, str, str, str)
        self.list.set_model(self.model)
        cell_avatar = gtk.CellRendererPixbuf()
        cell_avatar.set_property('yalign', 0)
        self.cell_tweet = gtk.CellRendererText()
        self.cell_tweet.set_property('wrap-mode', pango.WRAP_WORD)
        self.cell_tweet.set_property('wrap-width', 260)
        self.cell_tweet.set_property('yalign', 0)
        self.cell_tweet.set_property('xalign', 0)
        
        column = gtk.TreeViewColumn('tweets')
        column.set_alignment(0.0)
        column.pack_start(cell_avatar, False)
        column.pack_start(self.cell_tweet, True)
        column.set_attributes(self.cell_tweet, markup=4)
        column.set_attributes(cell_avatar, pixbuf=0)
        self.list.append_column(column)
        
    def __highlight_hashtags(self, text):
        hashtags = util.detect_hashtags(text)
        if len(hashtags) == 0: return text
        
        for h in hashtags:
            torep = '#%s' % h
            cad = '<span foreground="#FF6633">#%s</span>' % h
            text = text.replace(torep, cad)
        return text
        
    def __highlight_mentions(self, text):
        mentions = util.detect_mentions(text)
        if len(mentions) == 0: return text
        
        for h in mentions:
            torep = '@%s' % h
            cad = '<span foreground="#FF6633">@%s</span>' % h
            text = text.replace(torep, cad)
        return text
        
    def update_wrap(self, val):
        #self.label.set_size_request(val, -1)
        self.cell_tweet.set_property('wrap-width', val - 80)
        iter = self.model.get_iter_first()
        
        while iter:
            path = self.model.get_path(iter)
            self.model.row_changed(path, iter)
            iter = self.model.iter_next(iter)
        
    def add_tweet(self, username, datetime, client, message, avatar):
        #log.debug('Adding Tweet: %s' % message)
        #log.debug('User image %s' % avatar)
        
        #filename = avatar[avatar.rfind('/') + 1:]
        #fullname = os.path.join('pixmaps', filename)
        #if os.path.isfile(fullname):
        #    pix = util.load_image(filename, pixbuf=True)
        #else:
            #p = PicDownloader(avatar, username, self.update_user_pic)
            #p.start()
            #pix = util.load_image('unknown.png', pixbuf=True)
        #    pass
        pix = util.load_image('unknown.png', pixbuf=True)
            
        message = '<span size="9000"><b>@%s</b> %s</span>' % (username, message)
        message = self.__highlight_hashtags(message)
        message = self.__highlight_mentions(message)
        interline = '<span size="2000">\n\n</span>'
        if client:
            footer = '<span size="small" foreground="#999">%s desde %s</span>' % (datetime, client)
        else:
            footer = '<span size="small" foreground="#999">%s</span>' % (datetime)
        
        tweet = message + interline + footer
        self.model.append([pix, username, datetime, client, tweet])
        del pix
        
    def update_user_pic(self, user, filename):
        pix = util.load_image(filename, pixbuf=True)
        iter = self.model.get_iter_first()
        while iter:
            u = self.model.get_value(iter, 1)
            if u == user:
                self.model.set_value(iter, 0, pix)
                break
            iter = self.model.iter_next(iter)
        del pix
            
        
    def update_tweets(self, arr_tweets):
        for tweet in arr_tweets:
            if tweet.has_key('user'):
                user = tweet['user']['screen_name']
                image = tweet['user']['profile_image_url']
            else:
                user = tweet['sender']['screen_name']
                image = tweet['sender']['profile_image_url']
                
            client = util.detect_client(tweet)
            timestamp = util.get_timestamp(tweet)
            
            self.add_tweet(user, timestamp, client, tweet['text'], image)
        
class PeopleList(gtk.ScrolledWindow):
    def __init__(self, label=''):
        gtk.ScrolledWindow.__init__(self)
        
        self.list = gtk.TreeView()
        self.list.set_headers_visible(False)
        self.list.set_events(gtk.gdk.POINTER_MOTION_MASK)
        self.list.set_level_indentation(0)
        self.list.set_rules_hint(True)
        self.list.set_resize_mode(gtk.RESIZE_IMMEDIATE)
        
        self.label = gtk.Label(label)
        
        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.set_shadow_type(gtk.SHADOW_IN)
        self.add(self.list)
        
        # avatar, profile(pango), screen_name, name, url, location, bio, status, protected, following
        self.model = gtk.ListStore(gtk.gdk.Pixbuf, str, str, str, str, str, str, str, str, str)
        self.list.set_model(self.model)
        cell_avatar = gtk.CellRendererPixbuf()
        cell_avatar.set_property('yalign', 0)
        self.cell_tweet = gtk.CellRendererText()
        self.cell_tweet.set_property('wrap-mode', pango.WRAP_WORD)
        self.cell_tweet.set_property('wrap-width', 260)
        self.cell_tweet.set_property('yalign', 0)
        self.cell_tweet.set_property('xalign', 0)
        
        column = gtk.TreeViewColumn('tweets')
        column.set_alignment(0.0)
        column.pack_start(cell_avatar, False)
        column.pack_start(self.cell_tweet, True)
        column.set_attributes(self.cell_tweet, markup=1)
        column.set_attributes(cell_avatar, pixbuf=0)
        self.list.append_column(column)
        
    def update_wrap(self, val):
        #self.label.set_size_request(val, -1)
        self.cell_tweet.set_property('wrap-width', val - 80)
        iter = self.model.get_iter_first()
        
        while iter:
            path = self.model.get_path(iter)
            self.model.row_changed(path, iter)
            iter = self.model.iter_next(iter)
            
    def add_profile(self, p):
        protected = ''
        following = ''
        if p['protected']: protected = '&lt;protected&gt;'
        if p['following']: protected = '&lt;following&gt;'
        
        pix = util.load_image('unknown.png', pixbuf=True)
        
        print p
        # Escape pango markup
        for key in ['url', 'location', 'description', 'name', 'screen_name']:
            if not p.has_key(key) or p[key] is None: continue
            p[key] = gobject.markup_escape_text(p[key])
            
        profile = '<span size="9000"><b>@%s</b> %s %s %s</span>\n' % (p['screen_name'], p['name'], 
                following, protected)
        profile += "<b>URL:</b> %s\n" % p['url']
        profile += "<b>Location:</b> %s\n" % p['location']
        profile += "<b>Bio:</b> %s\n" % p['description']
        profile += '<span size="2000">\n\n</span>'
        
        status = ''
        if p.has_key('status'): 
            status = '<span foreground="#999"><b>Last:</b> %s</span>\n' % (
                gobject.markup_escape_text(p['status']['text']))
        profile += status
        
        print profile
        self.model.append([pix, profile, p['screen_name'], p['name'], p['url'], 
            p['location'], p['description'], status, protected, following])
        del pix
        
    def update_profiles(self, people):
        for p in people:
            self.add_profile(p)
            
class PeopleIcons(gtk.ScrolledWindow):
    def __init__(self, label='', named=False):
        gtk.ScrolledWindow.__init__(self)
        
        self.named = named
        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.set_shadow_type(gtk.SHADOW_IN)
        
        # avatar, pango_profile, pango_name, screen_name, name, url, location, bio, status, protected, following
        #self.model = gtk.ListStore(gtk.gdk.Pixbuf, str, str, str, str, str, str, str, str, str, str)
        self.model = gtk.ListStore(gtk.gdk.Pixbuf, str, str)
        
        self.list = gtk.IconView(self.model)
        self.list.set_pixbuf_column(0)
        self.list.set_has_tooltip(True)
        self.list.set_orientation(gtk.ORIENTATION_VERTICAL)
        self.list.set_selection_mode(gtk.SELECTION_SINGLE)
        self.list.set_column_spacing(10)
        
        if self.named:
            self.list.set_markup_column(2)
            self.list.set_columns(2)
            self.list.set_item_width(120)
        else:
            self.list.set_columns(4)
            self.list.set_item_width(50)
        
        self.list.connect("query-tooltip", self.show_tooltip)
        
        self.label = gtk.Label(label)
        self.add(self.list)
        
    def show_tooltip(self, widget, x, y, keyboard_mode, tooltip):
        rel_y = self.get_property('vadjustment').value
        
        path = widget.get_path_at_pos(int(x), int(y + rel_y))
        if path is None: return False
        
        model = widget.get_model()
        iter = model.get_iter(path)
        
        pix = model.get_value(iter, 0)
        tooltip.set_icon(pix)
        tooltip.set_markup(model.get_value(iter, 1))
        del pix
        
        return True
        
    def update_wrap(self, val):
        width = val - (self.list.get_margin() * 2) - 40
        item_w = self.list.get_item_width()
        
        columns = width / (item_w + self.list.get_column_spacing())
        self.list.set_columns(columns)
        
    def add_profile(self, p):
        protected = ''
        following = ''
        if p['protected']: protected = '&lt;protected&gt;'
        if p['following']: protected = '&lt;following&gt;'
        
        pix = util.load_image('unknown.png', pixbuf=True)
        
        # Escape pango markup
        for key in ['url', 'location', 'description', 'name', 'screen_name']:
            if not p.has_key(key) or p[key] is None: continue
            p[key] = gobject.markup_escape_text(p[key])
            
        profile = '<b>@%s</b> %s %s %s\n' % (p['screen_name'], p['name'], 
                following, protected)
        
        profile += '<span size="9000">'
        if not p['url'] is None: 
            profile += "<b>URL:</b> %s\n" % p['url']
            
        if not p['location'] is None:
            profile += "<b>Location:</b> %s\n" % p['location']
            
        if not p['description'] is None:
            profile += "<b>Bio:</b> %s\n" % p['description']
        
        if p.has_key('status'): 
            profile += '<span size="2000">\n</span>'
            status = '<span foreground="#999"><b>Last:</b> %s</span>\n' % (
                gobject.markup_escape_text(p['status']['text']))
            profile += status
        
        profile += '</span>'
        
        pangoname = '<span size="9000">@%s</span>' % p['screen_name']
        #self.model.append([pix, profile, pangoname, p['screen_name'], p['name'], p['url'], 
        #    p['location'], p['description'], status, protected, following])
        self.model.append([pix, profile, pangoname])
        del pix
        
    def update_profiles(self, people):
        for p in people:
            self.add_profile(p)
            
class UserForm(gtk.VBox):
    def __init__(self, label='', profile=None):
        gtk.VBox.__init__(self, False)
        
        label_width = 75
        self.label = gtk.Label(label)
        
        self.user_pic = gtk.Button()
        self.user_pic.set_size_request(60, 60)
        pic_box = gtk.VBox(False)
        pic_box.pack_start(self.user_pic, False, False, 10)
        
        self.screen_name = gtk.Label()
        self.screen_name.set_alignment(0, 0.5)
        self.tweets_count = gtk.Label()
        self.tweets_count.set_alignment(0, 0.5)
        self.tweets_count.set_padding(8, 0)
        self.following_count = gtk.Label()
        self.following_count.set_alignment(0, 0.5)
        self.following_count.set_padding(8, 0)
        self.followers_count = gtk.Label()
        self.followers_count.set_alignment(0, 0.5)
        self.followers_count.set_padding(8, 0)
        
        info_box = gtk.VBox(False)
        info_box.pack_start(self.screen_name, False, False, 5)
        info_box.pack_start(self.tweets_count, False, False)
        info_box.pack_start(self.following_count, False, False)
        info_box.pack_start(self.followers_count, False, False)
        
        top = gtk.HBox(False)
        top.pack_start(pic_box, False, False, 10)
        top.pack_start(info_box, False, False, 5)
        
        self.real_name = gtk.Entry()
        name_lbl = gtk.Label('Nombre')
        name_lbl.set_size_request(label_width, -1)
        name_box = gtk.HBox(False)
        name_box.pack_start(name_lbl, False, False, 2)
        name_box.pack_start(self.real_name, True, True, 5)
        
        self.location = gtk.Entry()
        loc_lbl = gtk.Label('Ubicacion')
        loc_lbl.set_size_request(label_width, -1)
        loc_box = gtk.HBox(False)
        loc_box.pack_start(loc_lbl, False, False, 2)
        loc_box.pack_start(self.location, True, True, 5)
        
        self.url = gtk.Entry()
        url_lbl = gtk.Label('URL')
        url_lbl.set_size_request(label_width, -1)
        url_box = gtk.HBox(False)
        url_box.pack_start(url_lbl, False, False, 2)
        url_box.pack_start(self.url, True, True, 5)
        
        self.bio = gtk.TextView()
        self.bio.set_wrap_mode(gtk.WRAP_WORD)
        scrollwin = gtk.ScrolledWindow()
        scrollwin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)
        scrollwin.set_shadow_type(gtk.SHADOW_IN)
        scrollwin.set_size_request(-1, 80)
        scrollwin.add(self.bio)
        bio_lbl = gtk.Label('Bio')
        bio_lbl.set_size_request(label_width, -1)
        bio_box = gtk.HBox(False)
        bio_box.pack_start(bio_lbl, False, False, 2)
        bio_box.pack_start(scrollwin, True, True, 5)
        
        form = gtk.VBox(False)
        form.pack_start(name_box, False, False, 4)
        form.pack_start(loc_box, False, False, 4)
        form.pack_start(url_box, False, False, 4)
        form.pack_start(bio_box, False, False, 4)
        
        submit = gtk.Button(stock=gtk.STOCK_SAVE)
        submit_box = gtk.Alignment(1.0, 0.5)
        submit_box.set_property('right-padding', 5)
        submit_box.add(submit)
        
        self.pack_start(top, False, False)
        self.pack_start(form, False, False)
        self.pack_start(submit_box, False, False)
        
    def update(self, profile):
        self.user_pic.set_image(util.load_image('unknown.png'))
        self.screen_name.set_markup('<b>@%s</b>' % profile['screen_name'])
        self.tweets_count.set_markup('<span size="9000">%i Tweets</span>' % profile['statuses_count'])
        self.following_count.set_markup('<span size="9000">%i Following</span>' % profile['friends_count'])
        self.followers_count.set_markup('<span size="9000">%i Followers</span>' % profile['followers_count'])
        self.real_name.set_text(profile['name'])
        self.location.set_text(profile['location'])
        self.url.set_text(profile['url'])
        buffer = self.bio.get_buffer()
        buffer.set_text(profile['description'])

class UpdateBox(gtk.Window):
    def __init__(self, parent):
        gtk.Window.__init__(self)
        
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.set_title('Update Status')
        self.set_default_size(500, 120)
        self.set_transient_for(parent)
        self.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        #w.add(u)
        #w.show_all()
        
        label = gtk.Label()
        label.set_use_markup(True)
        label.set_alignment(0, 0.5)
        label.set_markup('<span size="medium"><b>What are you doing?</b></span>')
        label.set_justify(gtk.JUSTIFY_LEFT)
        
        self.num_chars = gtk.Label()
        self.num_chars.set_use_markup(True)
        self.num_chars.set_markup('<span size="14000" foreground="#999"><b>140</b></span>')
        
        self.update_text = gtk.TextView()
        self.update_text.set_border_width(2)
        self.update_text.set_left_margin(2)
        self.update_text.set_right_margin(2)
        self.update_text.set_wrap_mode(gtk.WRAP_WORD)
        self.update_text.get_buffer().connect("changed", self.count_chars)
        update = gtk.Frame()
        update.add(self.update_text)
        updatebox = gtk.HBox(False)
        updatebox.pack_start(update, True, True, 3)
        
        btn_url = gtk.Button()
        btn_url.set_image(util.load_image('cut.png'))
        btn_url.set_tooltip_text('Shorten URL')
        btn_url.set_relief(gtk.RELIEF_NONE)
        btn_pic = gtk.Button()
        btn_pic.set_image(util.load_image('photos.png'))
        btn_pic.set_tooltip_text('Upload Pic')
        btn_pic.set_relief(gtk.RELIEF_NONE)
        btn_clr = gtk.Button()
        btn_clr.set_image(util.load_image('clear.png'))
        btn_clr.set_tooltip_text('Clear Box')
        btn_clr.set_relief(gtk.RELIEF_NONE)
        btn_upd = gtk.Button('Update')
        chk_short = gtk.CheckButton('Autocortado de URLs')
        
        btn_clr.connect('clicked', self.clear)
        btn_upd.connect('clicked', self.update)
        
        top = gtk.HBox(False)
        top.pack_start(label, True, True, 5)
        top.pack_start(self.num_chars, False, False, 5)
        
        self.waiting = CairoWaiting(self)
        self.waiting.start()
        
        buttonbox = gtk.HBox(False)
        buttonbox.pack_start(chk_short, False, False, 0)
        buttonbox.pack_start(gtk.HSeparator(), False, False, 2)
        buttonbox.pack_start(btn_url, False, False, 0)
        buttonbox.pack_start(btn_pic, False, False, 0)
        buttonbox.pack_start(btn_clr, False, False, 0)
        buttonbox.pack_start(gtk.HSeparator(), False, False, 2)
        buttonbox.pack_start(btn_upd, False, False, 0)
        abuttonbox = gtk.Alignment(1, 0.5)
        abuttonbox.add(buttonbox)
        
        bottom = gtk.HBox(False)
        bottom.pack_start(self.waiting, False, False, 5)
        bottom.pack_start(abuttonbox, True, True, 5)
        
        vbox = gtk.VBox(False)
        vbox.pack_start(top, False, False, 2)
        vbox.pack_start(updatebox, True, True, 2)
        vbox.pack_start(bottom, False, False, 3)
        
        self.add(vbox)
        self.show_all()
    
    def count_chars(self, widget):
        buffer = self.update_text.get_buffer()
        remain = 140 - buffer.get_char_count()
        
        if remain >= 20: color = "#999"
        elif 0 < remain < 20: color = "#d4790d"
        else: color = "#D40D12"
        
        self.num_chars.set_markup('<span size="14000" foreground="%s"><b>%i</b></span>' % (color, remain))
        
    def clear(self, widget):
        self.update_text.get_buffer().set_text('')
        
    def update(self, widget):
        buffer = self.update_text.get_buffer()
        start, end = buffer.get_bounds()
        print buffer.get_text(start, end)
        self.waiting.stop()
        buffer.set_text('')
        self.destroy()
        
class Home(gtk.VBox):
    def __init__(self, mode='single'):
        gtk.VBox.__init__(self)
        
        self.timeline = TweetList('Home')
        self.replies = TweetList('Replies')
        self.direct = TweetList('Direct')
        self.change_mode(mode)
        
    def change_mode(self, mode):
        for child in self.get_children():
            self.remove(child)
        
        if mode == 'wide':
            wrapper = gtk.HBox(True)
            
            tbox = gtk.VBox(False)
            tbox.pack_start(gtk.Label('Home'), False, False)
            if self.timeline.get_parent(): 
                self.timeline.reparent(tbox)
            else:
                tbox.pack_start(self.timeline, True, True)
            wrapper.pack_start(tbox)
            
            rbox = gtk.VBox(False)
            rbox.pack_start(gtk.Label('Replies'), False, False)
            if self.replies.get_parent(): 
                self.replies.reparent(rbox)
            else:
                rbox.pack_start(self.replies, True, True)
            wrapper.pack_start(rbox)
                
            dbox = gtk.VBox(False)
            dbox.pack_start(gtk.Label('Direct'), False, False)
            if self.direct.get_parent(): 
                self.direct.reparent(dbox)
            else:
                dbox.pack_start(self.direct, True, True)
            wrapper.pack_start(dbox)
        else:
            wrapper = gtk.Notebook()
            if self.timeline.get_parent(): 
                self.timeline.reparent(wrapper)
                wrapper.set_tab_label(self.timeline, self.timeline.label)
            else:
                wrapper.append_page(self.timeline, self.timeline.label)
            if self.replies.get_parent(): 
                self.replies.reparent(wrapper)
                wrapper.set_tab_label(self.replies, self.replies.label)
            else:
                wrapper.append_page(self.replies, self.replies.label)
            if self.direct.get_parent(): 
                self.direct.reparent(wrapper)
                wrapper.set_tab_label(self.direct, self.direct.label)
            else:
                wrapper.append_page(self.direct, self.direct.label)
            
            wrapper.set_tab_label_packing(self.timeline, True, True, gtk.PACK_START)
            wrapper.set_tab_label_packing(self.replies, True, True, gtk.PACK_START)
            wrapper.set_tab_label_packing(self.direct, True, True, gtk.PACK_START)
            
        self.add(wrapper)
        self.show_all()
        
    def update_wrap(self, width, mode):
        if mode == 'single':
            w = width
        else:
            w = width / 3
        
        self.timeline.update_wrap(w)
        self.replies.update_wrap(w)
        self.direct.update_wrap(w)
        
class Favorites(Wrapper):
    def __init__(self):
        Wrapper.__init__(self)
        
        self.favorites = TweetList('Favorites')
        wrapper = gtk.HBox(False)
        wrapper.pack_start(self.favorites, True, True)
        self.pack_start(gtk.Label('Favorites'), False, False)
        self.pack_start(wrapper, True, True)
        self.show_all()
        
    def update_wrap(self, width, mode):
        self.favorites.update_wrap(width)
    # self.show_followers(self.controller.get_followers())
class Profile(Wrapper):
    def __init__(self, mode='single'):
        Wrapper.__init__(self)
        
        self.user_form = UserForm('Profile')
        self.following = PeopleIcons('Following')
        self.followers = PeopleIcons('Followers')
        self.change_mode(mode)
        
    def change_mode(self, mode):
        for child in self.get_children():
            self.remove(child)
        
        if mode == 'wide':
            wrapper = gtk.HBox(True)
            
            tbox = gtk.VBox(False)
            tbox.pack_start(gtk.Label('Profile'), False, False)
            if self.user_form.get_parent(): 
                self.user_form.reparent(tbox)
            else:
                tbox.pack_start(self.user_form, True, True)
            wrapper.pack_start(tbox)
            
            rbox = gtk.VBox(False)
            rbox.pack_start(gtk.Label('Following'), False, False)
            if self.following.get_parent(): 
                self.following.reparent(rbox)
            else:
                rbox.pack_start(self.following, True, True)
            wrapper.pack_start(rbox)
                
            dbox = gtk.VBox(False)
            dbox.pack_start(gtk.Label('Followers'), False, False)
            if self.followers.get_parent(): 
                self.followers.reparent(dbox)
            else:
                dbox.pack_start(self.followers, True, True)
            wrapper.pack_start(dbox)
        else:
            wrapper = gtk.Notebook()
            if self.user_form.get_parent(): 
                self.user_form.reparent(wrapper)
                wrapper.set_tab_label(self.user_form, self.user_form.label)
            else:
                wrapper.append_page(self.user_form, self.user_form.label)
            #bbbox = gtk.VBox(False)
            #wrapper.append_page(bbbox, gtk.Label('Profile'))
            print self.following
            if self.following.get_parent(): 
                self.following.reparent(wrapper)
                wrapper.set_tab_label(self.following, self.following.label)
            else:
                wrapper.append_page(self.following, self.following.label)
                
            if self.followers.get_parent(): 
                self.followers.reparent(wrapper)
                wrapper.set_tab_label(self.followers, self.followers.label)
            else:
                wrapper.append_page(self.followers, self.followers.label)
            
            wrapper.set_tab_label_packing(self.user_form, True, True, gtk.PACK_START)
            wrapper.set_tab_label_packing(self.following, True, True, gtk.PACK_START)
            wrapper.set_tab_label_packing(self.followers, True, True, gtk.PACK_START)
            
        self.add(wrapper)
        self.show_all()
        
    def set_user_profile(self, user_profile):
        self.user_form.update(user_profile)
        
    def set_following(self, arr_following):
        self.following.update_profiles(arr_following)
        
    def set_followers(self, arr_followers):
        self.followers.update_profiles(arr_followers)
        
    def update_wrap(self, width, mode):
        if mode == 'single':
            w = width
        else:
            w = width / 3
        
        self.following.update_wrap(w)
        self.followers.update_wrap(w)
        
class CairoWaiting(gtk.DrawingArea):
    def __init__(self, parent):
        gtk.DrawingArea.__init__(self)
        self.par = parent
        self.active = False
        self.connect('expose-event', self.expose)
        self.set_size_request(16, 16)
        self.timer = None
        self.count = 0
    
    def start(self):
        self.active = True
        self.timer = gobject.timeout_add(150, self.update)
        self.queue_draw()
        
    def stop(self):
        self.active = False
        self.queue_draw()
        gobject.source_remove(self.timer)
        
    def update(self):
        self.count += 1
        if self.count > 3: self.count = 0
        self.queue_draw()
        return True
        
    def expose(self, widget, event):
        cr = widget.window.cairo_create()
        cr.set_line_width(0.8)
        rect = self.get_allocation()
        
        cr.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
        cr.clip()
        
        cr.rectangle(0, 0, rect.width, rect.height)
        if not self.active: return
        
        img = 'wait-%i.png' % (self.count + 1)
        pix = util.load_image(img, True)
        cr.set_source_pixbuf(pix, 0, 0)
        cr.paint()
        del pix
        
        #cr.text_path(self.error)
        #cr.stroke()
        
class Dock(gtk.Alignment):
    def __init__(self, parent, mode='single'):
        gtk.Alignment.__init__(self, 0.5, 0.5)
        
        self.mainwin = parent
        self.btn_home = gtk.Button()
        self.btn_home.set_relief(gtk.RELIEF_NONE)
        self.btn_home.set_tooltip_text('Home')
        self.btn_favs = gtk.Button()
        self.btn_favs.set_relief(gtk.RELIEF_NONE)
        self.btn_favs.set_tooltip_text('Favoritos')
        self.btn_lists = gtk.Button()
        self.btn_lists.set_relief(gtk.RELIEF_NONE)
        self.btn_lists.set_tooltip_text('Listas')
        self.btn_update = gtk.Button()
        self.btn_update.set_relief(gtk.RELIEF_NONE)
        self.btn_update.set_tooltip_text('Actualizar Estado')
        self.btn_search = gtk.Button()
        self.btn_search.set_relief(gtk.RELIEF_NONE)
        self.btn_search.set_tooltip_text('Buscar')
        self.btn_profile = gtk.Button()
        self.btn_profile.set_relief(gtk.RELIEF_NONE)
        self.btn_profile.set_tooltip_text('Perfil')
        self.btn_settings = gtk.Button()
        self.btn_settings.set_relief(gtk.RELIEF_NONE)
        self.btn_settings.set_tooltip_text('Preferencias')
        
        self.btn_home.connect('clicked', self.mainwin.show_home)
        self.btn_favs.connect('clicked', self.mainwin.show_favs)
        self.btn_update.connect('clicked', self.show_update)
        self.btn_profile.connect('clicked', self.mainwin.show_profile)
        self.btn_settings.connect('clicked', self.mainwin.switch_mode)
        
        box = gtk.HBox()
        box.pack_start(self.btn_home, False, False)
        box.pack_start(self.btn_favs, False, False)
        box.pack_start(self.btn_lists, False, False)
        box.pack_start(self.btn_update, False, False)
        box.pack_start(self.btn_search, False, False)
        box.pack_start(self.btn_profile, False, False)
        box.pack_start(self.btn_settings, False, False)
        
        self.change_mode(mode)
        self.add(box)
        self.show_all()
        
    def show_update(self, widget):
        u = UpdateBox(self.mainwin)
        
    def change_mode(self, mode):
        if mode == 'wide':
            self.btn_home.set_image(util.load_image('button-test.png'))
            self.btn_favs.set_image(util.load_image('button-test.png'))
            self.btn_lists.set_image(util.load_image('button-test.png'))
            self.btn_update.set_image(util.load_image('button-update.png'))
            self.btn_search.set_image(util.load_image('button-test.png'))
            self.btn_profile.set_image(util.load_image('button-test.png'))
            self.btn_settings.set_image(util.load_image('button-test.png'))
        else:
            self.btn_home.set_image(util.load_image('button-test-single.png'))
            self.btn_favs.set_image(util.load_image('button-test-single.png'))
            self.btn_lists.set_image(util.load_image('button-test-single.png'))
            self.btn_update.set_image(util.load_image('button-update-single.png'))
            self.btn_search.set_image(util.load_image('button-test-single.png'))
            self.btn_profile.set_image(util.load_image('button-test-single.png'))
            self.btn_settings.set_image(util.load_image('button-test-single.png'))
        
class Main(gtk.Window):
    def __init__(self, controller):
        gtk.Window.__init__(self)
        
        self.controller = controller
        self.set_title('Turpial')
        self.set_size_request(280, 350)
        self.set_default_size(320, 480)
        self.set_icon(util.load_image('turpial_icon.png', True))
        self.set_position(gtk.WIN_POS_CENTER)
        self.connect('destroy', self.quit)
        self.connect('size-request', self.size_request)
        self.mode = 0
        self.workspace = 'wide'
        self.vbox = None
        self.contentbox = gtk.VBox(False)
        
        self.home = Home(self.workspace)
        self.favs = Favorites()
        self.profile = Profile()
        self.contenido = self.home
        
    def quit(self, widget):
        gtk.main_quit()
        self.controller.signout()
        log.debug('Adios')
        exit(0)
        
    def main_loop(self):
        gtk.main()
        
    def show_login(self):
        self.mode = 1
        if self.vbox is not None: self.remove(self.vbox)
        
        avatar = util.load_image('logo.png')
        self.message = LoginLabel(self)
        
        lbl_user = gtk.Label()
        lbl_user.set_justify(gtk.JUSTIFY_LEFT)
        lbl_user.set_use_markup(True)
        lbl_user.set_markup('<span size="small">Username</span>')
        
        lbl_pass = gtk.Label()
        lbl_pass.set_justify(gtk.JUSTIFY_LEFT)
        lbl_pass.set_use_markup(True)
        lbl_pass.set_markup('<span size="small">Password</span>')
        
        self.username = gtk.Entry()
        self.password = gtk.Entry()
        self.password.set_visibility(False)
        
        self.btn_signup = gtk.Button('Conectar')
        
        table = gtk.Table(8,1,False)
        
        table.attach(avatar,0,1,0,1,gtk.FILL,gtk.FILL, 20, 10)
        table.attach(self.message,0,1,1,2,gtk.EXPAND|gtk.FILL,gtk.FILL, 20, 3)
        table.attach(lbl_user,0,1,2,3,gtk.EXPAND,gtk.FILL,0,0)
        table.attach(self.username,0,1,3,4,gtk.EXPAND|gtk.FILL,gtk.FILL, 20, 0)
        table.attach(lbl_pass,0,1,4,5,gtk.EXPAND,gtk.FILL, 0, 5)
        table.attach(self.password,0,1,5,6,gtk.EXPAND|gtk.FILL,gtk.FILL, 20, 0)
        #table.attach(alignRem,0,1,6,7,gtk.EXPAND,gtk.FILL,0, 0)
        table.attach(self.btn_signup,0,1,7,8,gtk.EXPAND,gtk.FILL,0, 30)
        
        self.vbox = gtk.VBox(False, 5)
        self.vbox.pack_start(table, False, False, 2)
        
        self.add(self.vbox)
        self.show_all()
        
        self.btn_signup.connect('clicked', self.request_login, self.username, self.password)
        self.password.connect('activate', self.request_login, self.username, self.password)
        
    def request_login(self, widget, username, password):
        self.btn_signup.set_sensitive(False)
        self.username.set_sensitive(False)
        self.password.set_sensitive(False)
        gtk.main_iteration(False)
        self.controller.signin(username.get_text(), password.get_text())
        
    def cancel_login(self, error):
        #e = '<span background="#C00" foreground="#FFF" size="small">%s</span>' % error
        self.message.set_error(error)
        self.btn_signup.set_sensitive(True)
        self.username.set_sensitive(True)
        self.password.set_sensitive(True)
        
    def show_main(self):
        #self.set_size_request(620, 480)
        #self.set_position(gtk.WIN_POS_CENTER)
        log.debug('Cargando ventana principal')
        self.mode = 2
        
        self.profile.set_user_profile(self.controller.profile)
        self.profile.set_following(self.controller.get_following())
        self.profile.set_followers(self.controller.get_followers())
        
        self.contentbox.add(self.contenido)
        self.dock = Dock(self, self.workspace)
        self.statusbar = gtk.Statusbar()
        self.statusbar.push(0, 'Turpial')
        if (self.vbox is not None): self.remove(self.vbox)
        
        self.vbox = gtk.VBox(False, 5)
        self.vbox.pack_start(self.contentbox, True, True, 0)
        self.vbox.pack_start(self.dock, False, False, 0)
        self.vbox.pack_start(self.statusbar, False, False, 0)
        
        self.add(self.vbox)
        self.switch_mode()
        self.show_all()
        
    def show_home(self, widget):
        self.contentbox.remove(self.contenido)
        self.contenido = self.home
        self.contentbox.add(self.contenido)
        
    def show_favs(self, widget):
        self.contentbox.remove(self.contenido)
        self.contenido = self.favs
        self.contentbox.add(self.contenido)
        
    def show_profile(self, widget):
        self.contentbox.remove(self.contenido)
        self.contenido = self.profile
        self.contentbox.add(self.contenido)
    
    def update_timeline(self, tweets):
        self.home.timeline.update_tweets(tweets)
        #self.timeline.add_tweet('pupu', 'xxx', 'mierda', 'Hola joe')
        
    def update_replies(self, tweets):
        self.home.replies.update_tweets(tweets)
        
    def update_favs(self, tweets):
        self.favs.favorites.update_tweets(tweets)
        
    def update_directs(self, sent, recv):
        self.home.direct.update_tweets(sent)
        
    def update_rate_limits(self, val):
        tsec = val['reset_time_in_seconds'] - time.timezone
        t = time.strftime('%I:%M %P', time.gmtime(tsec))
        hits = val['remaining_hits']
        limit = val['hourly_limit']
        status = "%s of %s API calls. Next reset: %s" % (hits, limit, t)
        self.statusbar.push(0, status)
    
    def switch_mode(self, widget=None):
        cur_x, cur_y = self.get_position()
        cur_w, cur_h = self.get_size()
        
        if self.workspace == 'single':
            self.workspace = 'wide'
            self.set_size_request(960, 480)
            self.resize(960, 480)
            x = (960 - cur_w)/2
            self.move(cur_x - x, cur_y)
        else:
            self.workspace = 'single'
            self.set_size_request(320, 480)
            self.resize(320, 480)
            x = (cur_w - 320)/2
            self.move(cur_x + x, cur_y)
        
        self.dock.change_mode(self.workspace)
        self.home.change_mode(self.workspace)
        self.favs.change_mode(self.workspace)
        self.profile.change_mode(self.workspace)
        self.show_all()
        
    def size_request(self, widget, event, data=None):
        """Callback when the window changes its sizes. We use it to set the
        proper word-wrapping for the message column."""
        if self.mode < 2: return
        
        w, h = self.get_size()
        self.contenido.update_wrap(w, self.workspace)
        return
        
