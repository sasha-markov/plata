import sys

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, GLib, Gtk

from mainwin import MainWin

TITLE = 'Plata'
MAIN_WINDOW_HEIGHT = 700
# DIALOG_WINDOW_HEIGHT = 500
R = 1.618  # golden ratio

# class UpdateDialog(Gtk.Dialog):
#     def __init__(self, parent):
#         super().__init__(title='Update rates', transient_for=parent, flags=0)
#         self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
#         self.set_default_size(DIALOG_WINDOW_HEIGHT / R, DIALOG_WINDOW_HEIGHT)
#         label = Gtk.Label(label='This is update dialog')
#         box = self.get_content_area()
#         box.add(label)
#         self.show_all()


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
        self.main_window = MainWin(application=self, title=TITLE,
                                   default_height=MAIN_WINDOW_HEIGHT,
                                   default_width=MAIN_WINDOW_HEIGHT*R)
        self.main_window.about_button.connect('clicked', self.on_about)
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
