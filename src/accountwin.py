import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

from models import update_accounts_model
from utils import create_account, set_balance, update_rates, Account, Balance, \
                  create_table_views, get_model_accounts

R = 1.618            # Golden ratio

WINDOW_HEIGHT = 450  # In pixels
BORDER_WIDTH = 8
PADDING = 3


class MyLabel(Gtk.Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_halign(1)


class AccountWin(Gtk.Window):
    def __init__(self, title, **kwargs):
        super().__init__(**kwargs)

        self.set_default_size(WINDOW_HEIGHT, WINDOW_HEIGHT * R)

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
        self.vbox.props.border_width = BORDER_WIDTH

        self.account_entry = Gtk.Entry()
        self.currency_entry = Gtk.Entry()
        self.categories_entry = Gtk.Entry()
        self.balance_entry = Gtk.Entry()

        self.entries = (MyLabel(label='Account name'), self.account_entry,
                        MyLabel(label='Currency'), self.currency_entry,
                        MyLabel(label='Categories'), self.categories_entry,
                        MyLabel(label='Balance'), self.balance_entry)
        options = (False, False, PADDING)
        [self.vbox.pack_start(item, *options) for item in self.entries]

        self.add(self.vbox)
        self.show_all()

    def on_cancel(self, widget):
        self.close()

    def on_create(self, widget):
        account = Account(name=self.account_entry.get_text(),
                          currency=self.currency_entry.get_text(),
                          categories=self.categories_entry.get_text())
        account.add()
        balance = Balance(account=self.account_entry.get_text(),
                          data=self.balance_entry.get_text())
        balance.set()
        create_table_views()
        update_accounts_model(get_model_accounts())
        self.close()

    def on_edit(self, widget):
        account = self.account_entry.get_text()
        balance = self.balance_entry.get_text()
        categories = self.categories_entry.get_text()
        update_account(account, balance)
        self.close()
