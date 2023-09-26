import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

from utils import create_account, set_balance, update_rates
from models import update_accounts_model

TITLE = 'New Account'
WINDOW_HEIGHT=450
R = 1.618  # golden ratio


class AccountWin(Gtk.Window):
    def __init__(self, title, **kwargs):
        super().__init__(**kwargs)

        # self.set_default_size(WINDOW_HEIGHT, WINDOW_HEIGHT * R)

        self.cancel_button = Gtk.Button(label='Cancel')
        self.cancel_button.connect('clicked', self.on_cancel)
        self.create_button = Gtk.Button(label='Create')
        self.create_button.connect('clicked', self.on_create)
        
        # Setting up the header bar
        self.hb = Gtk.HeaderBar(title=title, show_close_button=False)
        self.hb.pack_start(self.cancel_button)
        self.hb.pack_end(self.create_button)
        
        self.set_titlebar(self.hb)

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.vbox.props.border_width = 8

        self.account_entry = Gtk.Entry()
        self.currency_entry = Gtk.Entry()
        self.categories_entry = Gtk.Entry()
        self.balance_entry = Gtk.Entry()

        self.vbox.pack_start(Gtk.Label(label='Account name', halign=1), False, False, 3)
        self.vbox.pack_start(self.account_entry, False, False, 3)
        self.vbox.pack_start(Gtk.Label(label='Currency', halign=1), False, False, 3)
        self.vbox.pack_start(self.currency_entry, False, False, 3)
        self.vbox.pack_start(Gtk.Label(label='Categories', halign=1), False, False, 3)
        self.vbox.pack_start(self.categories_entry, False, False, 3)
        self.vbox.pack_start(Gtk.Label(label='Balance', halign=1), False, False, 3)
        self.vbox.pack_start(self.balance_entry, False, False, 3)                

        self.add(self.vbox)

        self.show_all()

    def on_cancel(self, widget):
        self.close()

    def on_create(self, widget):
        account = self.account_entry.get_text()
        currency = self.currency_entry.get_text()
        categories = self.categories_entry.get_text()
        balance = self.balance_entry.get_text()
        create_account(account, currency, categories)
        set_balance(account, balance)
        # update_rates()
        update_accounts_model()
        self.close()

    def on_edit(self, widget):
        account = self.account_entry.get_text()
        balance = self.balance_entry.get_text()
        categories = self.categories_entry.get_text()
        update_account(account, balance)
        self.close()
