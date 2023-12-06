import sys

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, GLib, Gtk

from database import init_db, sqlite_file_exists
from helpers import settings
from mainwin import MainWin

TITLE = 'Plata'
MAIN_WINDOW_HEIGHT = 700
R = 1.618  # golden ratio


class MyApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=f'net.amarkov.{TITLE}')
        GLib.set_application_name(TITLE)


    def do_startup(self):
        Gtk.Application.do_startup(self)

        action = Gio.SimpleAction.new('about', None)
        action.connect('activate', self.on_about)
        self.add_action(action)

        action = Gio.SimpleAction.new('quit', None)
        action.connect('activate', self.on_quit)
        self.add_action(action)

    def do_activate(self):
        self.main_window = MainWin(application=self,
                                   title=TITLE,
                                   default_height=MAIN_WINDOW_HEIGHT,
                                   default_width=MAIN_WINDOW_HEIGHT*R,
                                   border_width=0)
        self.css_provider = Gtk.CssProvider()
        self.css_provider.load_from_path('plata.css')
        self.main_window.popover.connect_callback(9, self.on_about)
        self.main_window.present()

    def on_about(self):
        self.about_dialog = Gtk.AboutDialog(modal=True)
        self.about_dialog.present()

    def on_quit(self, action, param):
        self.quit()


if __name__ == '__main__':
    app = MyApplication()
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)

