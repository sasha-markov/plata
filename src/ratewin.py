import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


from utils4 import add_rate


TITLE = 'New Rate'
WINDOW_WIDTH=350
R = 1.618  # golden ratio


class NewRateWin(Gtk.Window):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # self.set_default_size(WINDOW_WIDTH, WINDOW_WIDTH * R)

        self.cancel_button = Gtk.Button(label='Cancel')
        self.cancel_button.connect('clicked', self.on_cancel)
        self.add_button = Gtk.Button(label='Add')
        self.add_button.connect('clicked', self.on_add)
        
        # Setting up the header bar
        self.hb = Gtk.HeaderBar(title=TITLE, show_close_button=False)
        self.hb.pack_start(self.cancel_button)
        self.hb.pack_end(self.add_button)
        
        self.set_titlebar(self.hb)

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.vbox.props.border_width = 8

        self.currency_entry = Gtk.Entry()
        self.rate_entry = Gtk.Entry()

        self.vbox.pack_start(Gtk.Label(label='Currency', halign=1), False, False, 3)
        self.vbox.pack_start(self.currency_entry, False, False, 3)
        self.vbox.pack_start(Gtk.Label(label='Rate', halign=1), False, False, 3)
        self.vbox.pack_start(self.rate_entry, False, False, 3)

        self.add(self.vbox)

        self.show_all()

    def on_cancel(self, widget):
        self.close()

    def on_add(self, widget):
        currency = self.currency_entry.get_text()
        rate = self.rate_entry.get_text()
        print(currency + ': ' + rate)
        add_rate(currency, rate)
        self.close()
