import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

from sqlalchemy import func, select, update

from database import Session
from helpers import exchange, get_localtime, load_currencies
from models import Account, Balance, LastBalance, LastRate,\
                   select_balances, subq_accounts
from ratewin import add_rate
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
                   filters: set,
                   ):
    with Session.begin() as session:
        account = Account(name=name, currency=currency, categories=categories)
        session.add(account)
        balance = Balance(account=name, updated=get_localtime(), data=balance)
        session.add(balance)

    with Session.begin() as session:
        session.execute(DropView('vbalances'))
        session.execute(CreateView('vbalances', select_balances))
        rows = session.query(subq_accounts).all()
        
    accounts = Gtk.ListStore(str, float, float, str)
    [accounts.append(row) for row in rows]
    if categories:
        for item in categories.split(sep=','):
            filters.add(item.strip())
    return accounts

def update_account(name: str, balance: float, categories: str):
    with Session.begin() as session:
        balance = Balance(account=name, updated=get_localtime(), data=balance)
        session.add(balance)

    with Session.begin() as session:
        stmt = (
            update(Account)
            .where(Account.name == name)
            .values(categories=categories)
            .execution_options(synchronize_session='fetch')
            )
        result = session.execute(stmt)
 
    with Session.begin() as session:
        session.execute(DropView('vbalances'))
        session.execute(CreateView('vbalances', select_balances))
        rows = session.query(subq_accounts).all()

    accounts = Gtk.ListStore(str, float, float, str)
    [accounts.append(row) for row in rows]
    return accounts


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
        categories = self.categories_entry.get_text()
        new_model = update_account(name=self.account_entry.get_text(),
                                   balance=self.balance_entry.get_text(),
                                   categories=categories)
        if categories:
            for item in categories.split(sep=','):
                self.parent.new_categories.add(item.strip())
    
        self.parent.set_model(new_model)
        self.parent.update_filters()
        self.parent.update_total()        
        self.close()


class NewAccountWin(Gtk.Window):
    def __init__(self, parent, title, **kwargs):
        super().__init__(transient_for=parent, **kwargs)

        self.phys_currencies = load_currencies('../physical_currency_list.csv')
        self.digit_currencies = load_currencies('../digital_currency_list.csv')        

        self.parent = parent
        self.accounts_model = parent.accounts_model
        self.accounts_names = set([row[0] for row in self.accounts_model])
        self.rates = dict([row for row in parent.rates_model])

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
        self.rate_entry = Gtk.Entry()
        self.categories_entry = Gtk.Entry()
        self.balance_entry = Gtk.Entry()

        self.rate_label = MyLabel(label='Rate')

        self.rate_entry.connect('changed', self.on_rate_changed)
        self.rate_entry.connect('icon-press', self.on_rate_press)
        
        self.currencies_model = Gtk.ListStore(str)
        for currency in self.phys_currencies | self.digit_currencies:
            self.currencies_model.append([currency])
        
        self.currency_completion = Gtk.EntryCompletion()
        self.currency_completion.set_minimum_key_length(1)
        self.currency_completion.set_model(self.currencies_model)
        self.currency_completion.set_text_column(0)
        self.currency_completion.connect('match-selected', self.on_currency_selected)
        
        self.currency_entry.set_completion(self.currency_completion)
        
        self.rate_entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY,
                                                'view-refresh')

        self.entries = (MyLabel(label='Account name'), self.account_entry,
                        MyLabel(label='Currency'), self.currency_entry,
                        self.rate_label, self.rate_entry,
                        MyLabel(label='Categories'), self.categories_entry,
                        MyLabel(label='Balance'), self.balance_entry,
                        self.status_bar)
        options = (False, False, PADDING)
        [self.vbox.pack_start(item, *options) for item in self.entries]
        self.add(self.vbox)
        self.show_all()

    def on_cancel(self, widget):
        self.close()

    def on_currency_selected(self, entry_completion, model, treeiter):
        currency = model[treeiter][0]
        if currency in self.rates.keys():
            rate = self.rates[currency]
            self.rate_entry.set_text(str(rate))
            fs = f'Rate (1 {currency} = ${rate:,.3f} or $1 = {1/rate:,.4f} {currency})'
            self.rate_label.set_label(fs)
        else:
            self.rate_label.set_label(f'Rate (1 {currency} = $?)')

    def on_create(self, widget):
        new_rates_model = add_rate(self.currency_entry.get_text(),
                                   self.rate_entry.get_text())
        self.parent.rates_treeview.set_model(new_rates_model)        
        new_model = create_account(self.account_entry.get_text(),
                                   self.currency_entry.get_text(),
                                   self.categories_entry.get_text(),
                                   self.balance_entry.get_text(),
                                   self.parent.new_categories,
                                   )
        self.parent.set_model(new_model)
        self.parent.update_filters()
        self.parent.update_total()
        self.close()

    def on_rate_changed(self, widget):
        currency = self.currency_entry.get_text()
        rate = float(self.rate_entry.get_text())
        if rate:
            fs = f'Rate (1 {currency} = ${rate:,.3f} or $1 = {1/rate:,.4f} {currency})'
            self.rate_label.set_label(fs)
        else:
            self.rate_label.set_label('')
    
        self.status_bar.pop(303)

    def on_rate_press(self, entry, icon_pos, event):
        if self.currency_entry.get_text():
            currency = self.currency_entry.get_text()
            rate = exchange(currency, 'USD')
            if rate:
                entry.set_text(str(rate))
            else:
                self.status_bar.push(303, f'Unknown currency code {currency}')
