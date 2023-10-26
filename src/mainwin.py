import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

from sqlalchemy import select

from database import Session
from models import Account, LastRate, subq_accounts

# Fix this
from utils import get_account, create_table_views

from accountwin import NewAccountWin, EditAccountWin
from ratewin import NewRateWin

TOOLBAR_BORDER_WIDTH = 4
GRID_LINES = 1
CELL_HEIGHT = 50

def get_filters_set(categories: str):
    filters = set()
    for item in categories.split(sep=','):
        if item:
            filters.add(item.strip())
    return filters

# Accounts class? -model, -categories, +get_accounts
def get_accounts(accounts: Gtk.ListStore, categories: list):
    """
    Retrieve rows from the db and appends accounts to
    Gtk.ListStore(str, float, float, str) and categories to List
    """

    with Session.begin() as session:
        rows = session.query(subq_accounts).all()

    for row in rows:
        accounts.append(row)
        for category in row.categories.split(sep=','):
            if category:
                categories.append(category.strip())

# Rates class? -model, +get_rates
def get_rates(rates: Gtk.ListStore):
    """
    Retrieve rows from the db and appends rates to Gtk.ListStore(str, float)
    """
    with Session.begin() as session:
        rows = session.query(
            select(LastRate.currency1, LastRate.data).subquery()
        ).all()
    [rates.append(row) for row in rows]

def delete_account(name: str):
    with Session.begin() as session:
        account = session.query(Account).filter(Account.name == name)
        account.delete(synchronize_session=False)


class FilterElement(Gtk.ListBoxRow):
    """Describes filters by category"""
    def __init__(self, data):
        # Fix magic numbers
        super().__init__(halign=1, margin_top=3, margin_bottom=3)
        self.data = data
        self.add(Gtk.Label(label=data))


class MyStatusbar(Gtk.Statusbar):
    """Describes status bar of the main window"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        message_box = self.get_message_area()
        label = message_box.get_children()[0]
        message_box.set_child_packing(label, False, False, 0, Gtk.PackType.END)


class MainWin(Gtk.ApplicationWindow):
    def __init__(self, title, **kwargs):
        super().__init__(**kwargs)
        self.title = title

        accounts, categories = Gtk.ListStore(str, float, float, str), []
        get_accounts(accounts, categories)
        self.accounts_model = accounts

        self.categories = set(categories)
        self.categories.add('All')
        self.new_categories = set()
        
        rates = Gtk.ListStore(str, float)
        get_rates(rates)
        self.rates_model = rates

        self.update_button = Gtk.Button(hexpand=True)
        self.update_button.connect('clicked', self.on_update_button_clicked)
        self.new_account_button = Gtk.Button(hexpand=True)
        self.add_filter_button = Gtk.Button(hexpand=True)

        # Setting up boxes in which buttons and menu items are to be positioned
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=0)
        for box in [self.vbox, self.hbox]:
            box.props.border_width = TOOLBAR_BORDER_WIDTH * 2

        # Creating buttons in the hbox
        for button in [self.update_button,
                       self.new_account_button,
                       self.add_filter_button]:
            self.hbox.add(button)
        self.hbox.show_all()

        # Adding hbox with buttons and separator to the vbox
        self.vbox.add(self.hbox)
        self.vbox.add(Gtk.Separator())

        # Adding menu items to box
        labels = ['Preferences', 'Keyboard Shortcuts', 'Help']
        for label in labels:
            self.vbox.add(Gtk.ModelButton(label=label, halign=1))

        self.about_button = Gtk.ModelButton(label='About', halign=1)
        self.vbox.add(self.about_button)
        self.vbox.show_all()

        # Creating the popover and adding to it vbox
        # which contains hbox with buttons and separator
        self.popover = Gtk.Popover()
        self.popover.add(self.vbox)

        # Creating the context popover
        self.accounts_menu = Gtk.Menu()
        self.rates_menu = Gtk.Menu()

        self.menuitem1 = Gtk.MenuItem(label='Add Account...')
        self.menuitem1.connect('activate', self.create_account)

        self.menuitem3 = Gtk.MenuItem(label='Edit Account...')
        self.menuitem3.connect('activate', self.edit_account)

        self.menuitem4 = Gtk.MenuItem(label='Delete Account...')
        self.menuitem4.connect('activate', self.on_delete_account)

        for item in [self.menuitem1, self.menuitem3, self.menuitem4]:
            item.show()
            self.accounts_menu.append(item)

        self.menuitem2 = Gtk.MenuItem(label='Add Rate...')
        self.menuitem2.connect('activate', self.add_rate)
        self.menuitem2.show()
        self.rates_menu.append(self.menuitem2)

        # Setting up the header bar with menu button which opens popover
        self.hb = Gtk.HeaderBar(title=self.title, show_close_button=True)
        self.hb.pack_end(Gtk.MenuButton(popover=self.popover))
        self.set_titlebar(self.hb)

        self.current_filter = 'All'

        # Creating the filter, feeding it with the ListStore model,
        self.user_filter = self.accounts_model.filter_new()
        # setting the filter function
        self.user_filter.set_visible_func(self.user_filter_func)

        # Creating the treeview, making it use the filter as a model,
        # and adding the columns
        self.treeview = Gtk.TreeView(model=self.user_filter)
        self.treeview.set_grid_lines(GRID_LINES)
        self.treeview.connect('button-press-event', self.on_right_button_press)
        for i, column_title in enumerate(['Account', 'Balance', 'In USD']):
            renderer = Gtk.CellRendererText(height=CELL_HEIGHT)
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_cell_data_func(renderer,
                                      self.cell_data_func,
                                      func_data=i)
            column.set_expand(True)
            self.treeview.append_column(column)

        self.rates_treeview = Gtk.TreeView(model=self.rates_model)
        self.rates_treeview.set_grid_lines(GRID_LINES)
        self.rates_treeview.connect('button-press-event',
                                    self.on_right_button_press)
        for i, column_title in enumerate(['Currency', 'Rate']):
            renderer = Gtk.CellRendererText(height=CELL_HEIGHT)
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_cell_data_func(renderer,
                                      self.cell_data_func_rate,
                                      func_data=i)
            column.set_expand(True)
            self.rates_treeview.append_column(column)

        # Creating the ListBox to filter by category and setting up events
        self.filters = Gtk.ListBox()
        self.filters.connect('row-selected', self.on_row_selected)
        # and setting the sort function
        self.filters.set_sort_func(self.sort_func)
        for item in self.categories:
            filter_element = FilterElement(item)
            self.filters.add(filter_element)

        self.filters_window = Gtk.ScrolledWindow(border_width=0, vexpand=True)
        self.filters_window.add(self.filters)

        self.accounts_window = Gtk.ScrolledWindow(border_width=2, vexpand=True)
        self.accounts_window.add(self.treeview)

        self.status_bar = MyStatusbar()

        self.vvbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.vvbox.add(self.accounts_window)
        self.vvbox.add(self.status_bar)

        self.grid = Gtk.Grid(column_homogeneous=True, row_homogeneous=False)
        self.grid.add(self.filters_window)
        self.grid.attach(self.vvbox, 1, 0, 4, 1)

        self.notebook = Gtk.Notebook()
        self.notebook.append_page(self.grid,
                                  Gtk.Label(label='Accounts'))

        self.rates_window = Gtk.ScrolledWindow(vexpand=True)
        self.rates_window.add(self.rates_treeview)
        self.notebook.append_page(self.rates_window,
                                  Gtk.Label(label='Exchange rates'))

        self.add(self.notebook)
        self.filters.select_row(self.filters.get_row_at_index(0))
        self.show_all()

    def add_rate(self, widget):
        # Opens New Rate window
        dialog = NewRateWin(modal=True)
        dialog.present()        

    def cell_data_func(self, column, cell, model, iter, i):
        value = model.get(iter, i)[0]
        if value != 0.0:
            if i == 1:
                cell.set_property('text', f'{value:,.2f}')
            elif i == 2:
                cell.set_property('text', f'{value:,.0f}')
        else:
            cell.set_property('text', '')

    def cell_data_func_rate(self, column, cell, model, iter, i):
        value = model.get(iter, i)[0]
        if i == 1:
            cell.set_property('text', f'{value:,.3f}')

    def create_account(self, widget):
        # Opens New Account window
        dialog = NewAccountWin(title='New Account', modal=True, parent=self)

    def edit_account(self, menuitem):
        selection = self.treeview.get_selection().get_selected_rows()
        iterator = self.accounts_model.get_iter(selection[1])
        account = self.accounts_model.get_value(iterator, 0)
        account_name, currency, balance, categories = get_account(account)

        dialog = EditAccountWin(title='Edit Account', modal=True, parent=self)

        dialog.account_entry.set_text(account_name)
        dialog.account_entry.set_editable(False)
        dialog.currency_entry.set_text(currency)
        dialog.currency_entry.set_editable(False)
        dialog.balance_entry.set_text(str(balance))
        dialog.categories_entry.set_text(categories)

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
            # print(item)
            self.filters.add(FilterElement(item))
        self.new_categories.clear()

    def update_total(self):
        total = self.sum_accounts(self.user_filter)
        self.status_bar.pop(303)
        self.status_bar.push(303, f'${total:,.0f}')    

    def user_filter_func(self, model, iter, data):
        """Tests if the account in the row is the one in the filter"""
        if (
            self.current_filter is None
            or self.current_filter == 'All'
        ):
            return True
        else:
            return self.current_filter in model[iter][3]

    def on_delete_account(self, menuitem):
        selection = self.treeview.get_selection()
        model_filter, treeiter = selection.get_selected()
        account_name = model_filter[0][0]
        child_model = model_filter.get_model()
        if len(model_filter) == 1:
            row = self.filters.get_selected_row()
            self.filters.remove(row)
            # self.current_filter = 'All'           
        if treeiter:
            child_iter = model_filter.convert_iter_to_child_iter(treeiter)            
            child_model.remove(child_iter)
        delete_account(account_name)
        
    def on_right_button_press(self, widget, event):
        #  Check of right mouse button was pressed
        selection = widget.get_selection()
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            if widget is self.treeview:
                self.accounts_menu.popup_at_pointer(event)
                return True  # event has been handled
            elif widget is self.treeview and selection.count_selected_rows() == 1:
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

    def on_update_button_clicked(self, widget):
        dialog = UpdateDialog(self)
        response = dialog.run()
