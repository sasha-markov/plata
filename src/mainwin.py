import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from datetime import datetime, timedelta
import locale
import queue
from shutil import move
import threading
from time import sleep

from sqlalchemy import create_engine, select

from database import Session, init_db
from helpers import exchange, get_localtime, get_rates_from_market,\
                    settings, dump_settings
from models import Account, LastRate, LastBalance, Rate,\
                   subq_accounts, select_rates

from views import CreateView, DropView
from accountwin import NewAccountWin, EditAccountWin
from ratewin import NewRateWin, add_rate

BORDER_WIDTH = 4
CELL_HEIGHT = 50
DIALOG_WINDOW_HEIGHT = 500
R = 1.618  # golden ratio
GRID_LINES = 1
PADDING = 4
SPACING = 4

api_key = settings['alphavantage_api_key']

# Accounts class? -model, -categories, +get_accounts
def get_accounts(accounts: Gtk.ListStore, categories: list):
    """
    Retrieves rows from the db and appends them to
    Gtk.ListStore(str, float, float, str) and categories to List
    """

    with Session.begin() as session:
        rows = session.query(subq_accounts).all()

    for row in rows:
        accounts.append(row)
        for category in row.categories.split(sep=','):
            if category.strip():
                categories.append(category.strip())

                
def _get_accounts() -> Gtk.ListStore:
    """
    Retrieves rows from the db and appends them to
    Gtk.ListStore(str, float, float, str)    
    """
    accounts = Gtk.ListStore(str, float, float, str)
    with Session.begin() as session:
        rows = session.query(subq_accounts).all()
    [accounts.append(row) for row in rows]
    return accounts


# Rates class? -model, +get_rates
def get_rates(rates: Gtk.ListStore):
    """
    Retrieves rows from the db and appends them to Gtk.ListStore(str, float)
    """
    with Session.begin() as session:
        rows = session.query(
            select(LastRate.currency1,
                   LastRate.data,
                   LastRate.updated)
            .subquery()
        ).all()
    [rates.append(row) for row in rows]


def delete_account(name: str):
    with Session.begin() as session:
        account = session.query(Account).filter(Account.name == name)
        account.delete(synchronize_session=False)


def get_account(name: str) -> tuple:
    with Session.begin() as session:
        subq_update_account = (
            select(
                LastBalance.account,
                Account.currency,
                LastBalance.data,
                Account.categories,
            )
            .join(Account, LastBalance.account == Account.name)
            .filter(Account.name == name)
        ).subquery()
        return session.query(subq_update_account).first()


def add_rates(rates: dict) -> Gtk.ListStore:
    with Session.begin() as session:
        for currency, data in rates.items():
            rate = Rate(updated=get_localtime(),
                        currency1=currency,
                        currency2='USD',
                        data=data)
            session.add(rate)

    with Session.begin() as session:
        session.execute(DropView('vrates'))
        session.execute(CreateView('vrates', select_rates))
        rows = session.query(
            select(LastRate.currency1,
                   LastRate.data,
                   LastRate.updated).subquery()
        ).all()
    rates_model = Gtk.ListStore(str, float, str)
    [rates_model.append(row) for row in rows]
    return rates_model



class MyThread(threading.Thread):
    def __init__(self, queue, currencies):
        threading.Thread.__init__(self)
        self._queue = queue
        self._currencies = currencies

    def run(self):
        rates = []
        i = 1
        for currency in self._currencies:
            if i == 6:
                sleep(65)
                i = 1
            if currency == 'USD':
                rate = 1.0
            else:
                try:
                    rate = exchange(currency, 'USD', api_key)
                except:
                    rate = None
            if rate == 0:
                rate = 1.0
            rates.append([currency, rate])
            self._queue.put([currency, rate])
            i += 1



class FilterElement(Gtk.ListBoxRow):
    """Describes filters by category"""
    def __init__(self, data):
        # Fix magic numbers
        super().__init__(halign=1, margin_top=SPACING, margin_bottom=SPACING)
        self.data = data
        self.add(Gtk.Label(label=data))


class MyStatusbar(Gtk.Statusbar):
    """Describes status bar of the main window"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        message_box = self.get_message_area()
        label = message_box.get_children()[0]
        message_box.set_child_packing(label, False, False, 0, Gtk.PackType.END)


class MyCellRenderer(Gtk.CellRendererText):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.height = CELL_HEIGHT
        self.props.editable = True



class MyPopover(Gtk.Popover):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.vbox = Gtk.VBox()
        self.vbox.props.border_width = BORDER_WIDTH * 2

        menu_items = ['New Database...',
                      '---',
                      'Open Database...',
                      '---',
                      'Save Database As...',
                      '---',
                      'Preferences',
                      'Keyboard Shortcuts',
                      'Help',
                      'About']
        for item in menu_items:
            if item == '---':
                self.vbox.pack_start(Gtk.HSeparator(), False, False, 0)
            else:
                self.vbox.pack_start(
                    Gtk.ModelButton(label=item, halign=1), True, True, 0
                )
        self.vbox.show_all()

        self.add(self.vbox)


    def connect_callback(self, index: int, func):
        button = self.vbox.get_children()[index]
        button.connect('clicked', func)



class MyTreeView(Gtk.TreeView):
    def __init__(self,
                 column_titles: list,
                 func,
                 cols_editable={},
                 **kwargs):
        super().__init__(**kwargs)
        self.set_grid_lines(GRID_LINES)
        for i, title in enumerate(column_titles):
            renderer = Gtk.CellRendererText(height=CELL_HEIGHT)
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            #! Fix this: renderer class?
            if i in cols_editable.keys():
                renderer.props.editable = True
                renderer.connect('edited', cols_editable[i])
            column.set_cell_data_func(renderer, func, func_data=i)
            column.set_expand(True)
            self.append_column(column)



class MainWin(Gtk.ApplicationWindow):
    def __init__(self, title, **kwargs):
        super().__init__(**kwargs)
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        self.title = title

        self.accounts_model = Gtk.ListStore(str, float, float, str)
        categories = []
        # Retrieves rows (categories) from db and
        # appends them to the model (list);
        get_accounts(self.accounts_model, categories)

        self.categories = set(categories)
        self.categories.add('All')
        self.new_categories = set()

        self.rates_model = Gtk.ListStore(str, float, str)
        get_rates(self.rates_model)
        self.rates_updated = False # True if db updated, but model is not

        # queue to share data between threads
        self._queue = queue.Queue()
        self.rates = []


        """
        HeaderBar {
            update_rates_button,
            menu_button {
            }
        }
        popover {}
        notebook {
            accounts {
                grid {
                    vvbox {
                        accounts_window {
                            accounts_treeview {3*TreeViewColumn}
                        },
                        frame {status_bar},
                        buttons_box {
                            delete_account_button,
                            edit_account_button,
                            add_account_button
                        }
                    },
                    hhbox {
                        filters_window {
                            filters_listbox {n*FilterElement}
                        },
                        VSeparator
                    }
                }
            },
            exchange_rates {
                vvvbox {
                    rates_window {
                        rates_treeview {3*TreeViewColumn}
                    },
                    HSeparator,
                    buttons_box {
                        delete_rate_button,
                        update_rate_button,
                        edit_rate_button,
                        add_rate_button
                    }
                }
            }
        }
        """
 
        self.popover = MyPopover()
        self.popover.connect_callback(0, self.on_new_button)
        self.popover.connect_callback(2, self.on_open_button)
        self.popover.connect_callback(4, self.on_save_button)

        # Creating the context popovers
        self.accounts_menu, self.rates_menu = Gtk.Menu(), Gtk.Menu()

        self.add_account_menuitem = Gtk.MenuItem(label='Add Account...')
        self.edit_account_menuitem = Gtk.MenuItem(label='Edit Account...')
        self.delete_account_menuitem = Gtk.MenuItem(label='Delete Account')

        self.add_account_menuitem.connect('activate', self.add_account)
        self.edit_account_menuitem.connect('activate', self.edit_account)
        self.delete_account_menuitem.connect('activate', self._delete_account)

        for item in [self.add_account_menuitem,
                     self.edit_account_menuitem,
                     self.delete_account_menuitem]:
            item.show()
            self.accounts_menu.append(item)

        self.add_rate_menuitem = Gtk.MenuItem(label='Add Rate...')
        self.delete_rate_menuitem = Gtk.MenuItem(label='Delete Rate')
        self.update_rate_menuitem = Gtk.MenuItem(label='Update Rate')

        self.add_rate_menuitem.connect('activate', self._add_rate)
        self.delete_rate_menuitem.connect('activate', self.delete_rate)
        self.update_rate_menuitem.connect('activate', self.update_rate)

        for item in [self.add_rate_menuitem,
                     self.delete_rate_menuitem,
                     self.update_rate_menuitem]:
            item.show()
            self.rates_menu.append(item)

        # Setting up the header bar with menu button which opens popover
        self.hb = Gtk.HeaderBar(title=self.title,
                                subtitle=Session.kw['bind'].url.database,
                                show_close_button=True)
        self.hb.pack_end(Gtk.MenuButton(popover=self.popover))
        self.update_rates_button = Gtk.Button(label='Update Rates')
        self.update_rates_button.connect('clicked', self.update_rates)
        self.hb.pack_end(self.update_rates_button)

        self.set_titlebar(self.hb)

        self.current_filter = 'All'

        # Creating the filter, feeding it with the ListStore model,
        self.user_filter = self.accounts_model.filter_new()
        # setting the filter function
        self.user_filter.set_visible_func(self.user_filter_func)

        # Creating the treeview, making it use the filter as a model,
        # and adding the columns
        titles = ['Account', 'Balance', 'In USD']
        self.accounts_treeview = MyTreeView(column_titles=titles,
                                            func=self.accounts_cell_data_func,
                                            model=self.user_filter)
        self.accounts_treeview.connect('button-press-event',
                                       self.on_right_button_press)        
        
        titles = ['Currency', 'Rate', 'Updated']
        self.rates_treeview = MyTreeView(column_titles=titles,
                                         func=self.rates_cell_data_func,
                                         cols_editable={1: self.on_rate_edited},
                                         model=self.rates_model)
        self.rates_treeview.connect('button-press-event',
                                    self.on_right_button_press)
        

        # Creating the ListBox to filter by category and setting up events
        self.filters_listbox = Gtk.ListBox(border_width=BORDER_WIDTH*2)
        self.filters_listbox.connect('row-selected', self.on_row_selected)
        # and setting the sort function
        self.filters_listbox.set_sort_func(self.sort_func)
        for item in self.categories:
            self.filters_listbox.add(FilterElement(item))

        self.filters_window = Gtk.ScrolledWindow(vexpand=True)
        self.filters_window.add(self.filters_listbox)

        self.hhbox = Gtk.HBox()
        self.hhbox.pack_start(self.filters_window, True, True, 0)
        self.hhbox.pack_start(Gtk.VSeparator(), False, False, 0)

        self.accounts_window = Gtk.ScrolledWindow(vexpand=True)
        self.accounts_window.add(self.accounts_treeview)

        self.status_bar = MyStatusbar()
        self.status_bar.props.name = 'status_bar'
        self.frame = Gtk.Frame()
        self.frame.add(self.status_bar)

        self.delete_account_button = Gtk.Button(label='Delete Account')
        self.delete_account_button.connect('clicked', self._delete_account)
        self.delete_account_button.props.sensitive = False

        self.edit_account_button = Gtk.Button(label='Edit Account...')
        self.edit_account_button.connect('clicked', self.edit_account)
        self.edit_account_button.props.sensitive = False

        self.add_account_button = Gtk.Button(label='Add Account...')
        self.add_account_button.connect('clicked', self.add_account)

        self.bbox = Gtk.HBox()
        self.bbox.pack_start(self.delete_account_button, False, False, 0)
        self.bbox.pack_end(self.edit_account_button, False, False, 0)
        self.bbox.pack_end(self.add_account_button, False, False, PADDING)

        self.vvbox = Gtk.VBox()
        self.vvbox.pack_start(self.accounts_window, True, True, PADDING)
        self.vvbox.pack_start(self.frame, False, False, PADDING)
        self.vvbox.pack_start(self.bbox, False, False, PADDING)

        self.grid = Gtk.Grid(column_homogeneous=True,
                             row_homogeneous=False,
                             column_spacing=SPACING,
                             row_spacing=SPACING,
                             border_width=BORDER_WIDTH)
        self.grid.add(self.hhbox)
        self.grid.attach(self.vvbox, 1, 0, 4, 1)

        self.notebook = Gtk.Notebook()
        self.notebook.append_page(self.grid, Gtk.Label(label='Accounts'))

        self.add_rate_button = Gtk.Button(label='Add Rate...')
        self.delete_rate_button = Gtk.Button(label='Delete Rate')
        self.edit_rate_button = Gtk.Button(label='Edit Rate...')
        self.update_rate_button = Gtk.Button(label='Update Rate')

        self.add_rate_button.connect('clicked', self._add_rate)
        self.delete_rate_button.connect('clicked', self.delete_rate)

        for button in [self.delete_rate_button,
                       self.edit_rate_button,
                       self.update_rate_button]:
            button.props.sensitive = False

        self.buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.buttons_box.pack_start(self.delete_rate_button, False, False, 0)
        self.buttons_box.pack_end(self.update_rate_button, False, False, 0)
        self.buttons_box.pack_end(self.edit_rate_button, False, False, PADDING)
        self.buttons_box.pack_end(self.add_rate_button, False, False, 0)

        self.rates_window = Gtk.ScrolledWindow(vexpand=True)
        self.rates_window.add(self.rates_treeview)

        self.vvvbox = Gtk.VBox(border_width=BORDER_WIDTH)
        self.vvvbox.pack_start(self.rates_window, True, True, PADDING)
        self.vvvbox.pack_start(Gtk.HSeparator(), False, False, PADDING)
        self.vvvbox.pack_start(self.buttons_box, False, False, PADDING)

        self.notebook.append_page(self.vvvbox,
                                  Gtk.Label(label='Exchange rates'))

        self.notebook.connect('switch-page', self.on_switch_page)

        self.overlay = Gtk.Overlay()
        self.overlay.add(self.notebook)
        self.ssbar = MyStatusbar(halign=1, valign=2)
        self.ssbar.props.name = 'ssbar'
        self.overlay.add_overlay(self.ssbar)
        self.add(self.overlay)
        
        self.filters_listbox.select_row(
            self.filters_listbox.get_row_at_index(0)
        )
        self.show_all()

    def accounts_cell_data_func(self, column, cell, model, treeiter, i):
        value = model.get(treeiter, i)[0]
        if i == 1:
            cell.props.text = f'{value:,.2f}'
        elif i == 2:
            cell.props.text = f'{value:,.0f}'

    def add_account(self, widget):
        # Opens New Account window
        dialog = NewAccountWin(title='New Account', modal=True, parent=self)

    def _add_rate(self, widget):
        # Opens New Rate window
        dialog = NewRateWin(modal=True, parent=self)

    # Fix empty filters after deleting accounts
    def _delete_account(self, menuitem):
        selection = self.accounts_treeview.get_selection()
        model_filter, treeiter = selection.get_selected()
        # account_name = model_filter[0][0]
        child_model = model_filter.get_model()
        if len(model_filter) == 1:
            row = self.filters_listbox.get_selected_row()
            self.filters_listbox.remove(row)
            # self.current_filter = 'All'
        if treeiter:
            child_iter = model_filter.convert_iter_to_child_iter(treeiter)
            account_name = child_model.get_value(child_iter, 0)
            delete_account(account_name)
            child_model.remove(child_iter)
            self.update_total()

    def delete_rate(self, menuitem):
        selection = self.rates_treeview.get_selection()
        model, treeiter = selection.get_selected()
        print(self.rates_model.get_value(treeiter, 0))

    def edit_account(self, menuitem):
        # Opens Edit Account window
        selection = self.accounts_treeview.get_selection()
        model_filter, treeiter = selection.get_selected()
        child_model = model_filter.get_model()
        if treeiter:
            child_iter = model_filter.convert_iter_to_child_iter(treeiter)
            account_name = child_model.get_value(child_iter, 0)            
        account_name, currency, balance, categories = get_account(account_name)
        dialog = EditAccountWin(title='Edit Account', modal=True, parent=self)
        dialog.account_entry.props.editable = False
        dialog.account_entry.props.text = account_name
        dialog.currency_entry.props.editable = False
        dialog.currency_entry.props.text = currency
        dialog.balance_entry.props.text = str(balance)
        dialog.categories_entry.props.text = categories

    def rates_cell_data_func(self, column, cell, model, treeiter, i):
        # !Fix
        value = model.get(treeiter, i)[0]
        if i == 1:
            cell.props.text = f'{value:,.3f}'
        if i == 2:
            d = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            if datetime.today() - d < timedelta(days=1):
                s = datetime.strftime(d, '%H:%M')
            else:
                s = datetime.strftime(d, '%d %b')
            cell.set_property('text', s)

    def set_model(self, model):
        self.user_filter = model.filter_new()
        self.user_filter.set_visible_func(self.user_filter_func)
        self.accounts_treeview.set_model(self.user_filter)

    def sort_func(self, row1, row2):
        return row1.data.lower() > row2.data.lower()

    def sum_accounts(self, accounts):
        sum = 0
        for account in accounts:
            sum += account[2]
        return sum

    def update_filters(self):
        for item in self.new_categories - self.categories:
            self.categories.add(item)
            self.filters_listbox.add(FilterElement(item))
        self.show_all()
        self.new_categories.clear()

    def update_rate(self, menuitem):
        selection = self.rates_treeview.get_selection()
        model, treeiter = selection.get_selected()
        currency = self.rates_model.get_value(treeiter, 0)
        rate = self.rates_model.get_value(treeiter, 1)
        print(f'Old Rate: {rate}')
        new_rate = exchange(currency, 'USD')
        if rate != new_rate:
            add_rate(currency, new_rate)
            self.rates_updated = True
            self.rates_model[treeiter][1] = new_rate
            self.rates_model[treeiter][2] = get_localtime()
        print(f'New Rate: {new_rate}')

    def update_rates(self, widget):
        # self.ssbar.pop(303)
        exceptions = {'ARS', 'RUB', 'USD', 'USDC', 'USDT'}
        currencies = {row[0] for row in self.rates_model}

        # install timer event to check the queue for new data from the thread
        GLib.timeout_add(interval=250, function=self._on_timer)
        # start the thread
        self._thread = MyThread(self._queue, currencies - exceptions)
        self._thread.start()
          
        # print(currencies)
        # self.ssbar.push(303, f'Updating rates...')
        # new_rates = get_rates_from_market(currencies - exceptions, logger)
        # print(new_rates)
        # new_rates_model = add_rates(new_rates)

    def update_total(self):
        total = self.sum_accounts(self.user_filter)
        self.status_bar.pop(303)
        self.status_bar.push(303, f'${total:,.0f}')

    def user_filter_func(self, model, treeiter, data):
        """Tests if the account in the row is the one in the filter"""
        if (
            self.current_filter is None
            or self.current_filter == 'All'
        ):
            return True
        else:
            return self.current_filter in model[treeiter][3]

    def on_new_button(self, widget):
        dialog = Gtk.FileChooserDialog(
            title='New',
            parent=self,
            action=Gtk.FileChooserAction.SAVE,
            # default_height=DIALOG_WINDOW_HEIGHT,
            # default_width=DIALOG_WINDOW_HEIGHT*R
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE,
            0)
        response = dialog.run()
        if response == 0:
            self.db_file = dialog.get_filename()
            print(self.db_file)
            engine = create_engine(f'sqlite:///{self.db_file}',
                                   future=True, echo=True)
            Session.configure(bind=engine)
            init_db(engine)
        dialog.destroy()

    def on_open_button(self, widget):
        pass

    def on_rate_edited(self, widget, path, new_rate):
        currency, rate, updated = self.rates_model[path]
        new_rate = locale.atof(new_rate)
        if rate != new_rate:
            add_rate(currency, new_rate)
            self.rates_updated = True
            self.rates_model[path][1] = new_rate
            self.rates_model[path][2] = get_localtime()

    def on_right_button_press(self, widget, event):
        #  Check of right mouse button was pressed
        selection = widget.get_selection()
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            if widget is self.accounts_treeview:
                self.accounts_menu.popup_at_pointer(event)
                return True  # event has been handled
            elif (
                  widget is self.accounts_treeview
                  and selection.count_selected_rows() == 1
            ):
                print('Ha!!')
                return True
            elif widget is self.rates_treeview:
                self.rates_menu.popup_at_pointer(event)
                return True  # event has been handled

    def on_row_selected(self, widget, row):
        """Called if the row in the ListBox is selected"""
        # Sets the current category filter to the data field of selected row
        if row:
            self.current_filter = row.data
        # Updates the filter, which updates in turn the view
        self.user_filter.refilter()
        self.update_total()

    def on_save_button(self, widget):
        dialog = Gtk.FileChooserDialog(
            title='Save',
            parent=self,
            action=Gtk.FileChooserAction.SAVE,
            # default_height=DIALOG_WINDOW_HEIGHT,
            # default_width=DIALOG_WINDOW_HEIGHT*R
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE,
            0)
        dialog.set_current_name('untitled.db')
        response = dialog.run()
        if response == 0:
            self.db_file = dialog.get_filename()
            # !fix: try..except
            move('/tmp/untitled.db', self.db_file)
            settings['recent_db_files'].append(self.db_file)
            dump_settings()
            # print(self.settings)
            self.hb.props.subtitle = self.db_file
            # print(f'file selected: {self.db_file}')
        dialog.destroy()

    def on_switch_page(self, notebook, page, page_num):
        if page_num == 0 and self.rates_updated:
            new_model = _get_accounts()
            self.set_model(new_model)
            self.update_total()
            self.rates_updated = False

    def _on_timer(self):
        # if the thread is dead and no more data available...
        if not self._thread.is_alive() and self._queue.empty():
            # ...end the timer
            self.new_rates = dict(self.rates)
            print(self.new_rates)
            new_rates_model = add_rates(self.new_rates)
            self.rates_treeview.set_model(new_rates_model)
            new_accounts_model = _get_accounts()
            self.set_model(new_accounts_model)
            self.update_total()
            return False

        # if data available
        while not self._queue.empty():
            # read data from the thread
            currency, rate = self._queue.get()
            if rate is not None:
                self.rates.append([currency, rate])
                # update the statusbar
                self.ssbar.push(303, f'{currency} updated')
            else:
                self.ssbar.push(303, f'There is error while updating {currency}')

        # keep the timer alive
        return True

    def on_update_button_clicked(self, widget):
        dialog = UpdateDialog(self)
        response = dialog.run()
