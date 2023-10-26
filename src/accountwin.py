import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

from sqlalchemy import func, select

from database import Session
from helpers import get_localtime
from models import Account, Balance, LastBalance, LastRate,\
                   select_balances, subq_accounts
from views import CreateView, DropView

#Fix this
from utils import create_table_views, get_account_mod

R = 1.618            # Golden ratio

WINDOW_WIDTH = 485  # In pixels
BORDER_WIDTH = 8
PADDING = 3

MESSAGE = 'An account with that name already exists.'


def create_account(name: str,
                   currency: str,
                   categories: str,
                   balance: float,
                   accounts: Gtk.ListStore,
                   filters: set,
                   ):

    with Session.begin() as session:
        account = Account(name=name, currency=currency, categories=categories)
        session.add(account)
        balance = Balance(account=name, updated=get_localtime(), data=balance)
        session.add(balance)

    with Session.begin() as session:
        # create_table_views()
        session.execute(DropView('vbalances'))
        session.execute(CreateView('vbalances', select_balances))
        subq_account = (
            select(
                LastBalance.account,
                LastBalance.data,
                func.round(LastBalance.data * LastRate.data).label('usd'),
                Account.categories,
            )
            .join(Account, LastBalance.account == Account.name)
            .join(LastRate, Account.currency == LastRate.currency1)
            .filter(Account.name == name)
        ).subquery()
        row = session.query(subq_account).first()

    if row.categories:
        for item in row.categories.split(sep=','):
            filters.add(item.strip())
        
    accounts.append(row)


class MyEntry(Gtk.Entry, Gtk.Editable):

    def __init__(self, create_button, status_bar, test_set):
        super(MyEntry, self).__init__()
        self.button = create_button
        self.status_bar = status_bar
        self.test_set = test_set

    def is_in_set(self, name):
        return name in self.test_set
        
    """Called when the user inserts some text, by typing or pasting"""
    def do_insert_text(self, new_text, length, position):
        if new_text:
            self.get_buffer().insert_text(position, new_text, length)
            if self.is_in_set(self.get_text()):
                self.button.set_sensitive(False)
                self.status_bar.push(303, MESSAGE)
            else:
                self.button.set_sensitive(True)
                self.status_bar.pop(303)
            return position + length
        else:
            return position

    def do_delete_text(self, start_position, end_position):
        self.get_buffer().delete_text(start_position, end_position)
        if self.is_in_set(self.get_text()):
            self.button.set_sensitive(False)
            self.status_bar.push(303, MESSAGE)
        else:
            self.button.set_sensitive(True)
            self.status_bar.pop(303)


class MyLabel(Gtk.Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_halign(1)

        
class MyStatusbar(Gtk.Statusbar):
    """Describes status bar of the main window"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        message_box = self.get_message_area()
        label = message_box.get_children()[0]
        label.set_line_wrap(True)        
        message_box.set_child_packing(label, True, True, 0, Gtk.PackType.START)


class EditAccountWin(Gtk.Window):
    def __init__(self, parent, title, **kwargs):
        super().__init__(transient_for=parent, **kwargs)

        self.parent = parent

        self.set_default_size(WINDOW_WIDTH, -1)

        self.cancel_button = Gtk.Button(label='Cancel')
        self.cancel_button.connect('clicked', self.on_cancel)
        self.done_button = Gtk.Button(label='Done')
        self.done_button.connect('clicked', self.on_done)

        # Setting up the header bar
        self.hb = Gtk.HeaderBar(title=title, show_close_button=False)
        self.hb.pack_start(self.cancel_button)
        self.hb.pack_end(self.done_button)

        self.set_titlebar(self.hb)

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.vbox.props.border_width = BORDER_WIDTH

        self.account_entry = Gtk.Entry()
        self.currency_entry = Gtk.Entry()
        self.categories_entry = Gtk.Entry()
        self.balance_entry = Gtk.Entry()

        self.account_entry.set_sensitive(False)
        self.currency_entry.set_sensitive(False)

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

    def on_done(self, widget):
        balance = Balance(account=self.account_entry.get_text(),
                          data=self.balance_entry.get_text())
        balance.set()
        account = get_account_mod(self.account_entry.get_text())
        account.categories = self.categories_entry.get_text()
        create_table_views()
        self.accounts_model = get_accounts_model()
        self.parent.set_model(self.accounts_model)
        self.close()


class NewAccountWin(Gtk.Window):
    def __init__(self, parent, title, **kwargs):
        super().__init__(transient_for=parent, **kwargs)

        self.parent = parent
        self.accounts_model = parent.accounts_model
        self.accounts_names = set([row[0] for row in self.accounts_model])

        self.set_default_size(WINDOW_WIDTH, -1)

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

        self.status_bar = MyStatusbar()

        self.account_entry = MyEntry(create_button=self.create_button,
                                     status_bar=self.status_bar,
                                     test_set=self.accounts_names)
        self.currency_entry = Gtk.Entry()
        self.categories_entry = Gtk.Entry()
        self.balance_entry = Gtk.Entry()

        self.entries = (MyLabel(label='Account name'), self.account_entry,
                        MyLabel(label='Currency'), self.currency_entry,
                        MyLabel(label='Categories'), self.categories_entry,
                        MyLabel(label='Balance'), self.balance_entry,
                        self.status_bar)
        options = (False, False, PADDING)
        [self.vbox.pack_start(item, *options) for item in self.entries]
        self.add(self.vbox)
        self.show_all()

    def on_cancel(self, widget):
        self.close()

    def on_create(self, widget):
        create_account(self.account_entry.get_text(),
                       self.currency_entry.get_text(),
                       self.categories_entry.get_text(),
                       self.balance_entry.get_text(),
                       self.parent.accounts_model,
                       self.parent.new_categories,
                       )
        self.parent.update_filters()
        self.close()
