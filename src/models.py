import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

from utils import get_model_rates


# Creating the ListStore models
accounts_model = Gtk.ListStore(str, float, float, str)
rates_model = Gtk.ListStore(str, float)

# accounts_model.connect()

def update_accounts_model(accounts):
    accounts_model.clear()
    for row in accounts:
        accounts_model.append(row)


def update_rates_model():
    rates_model.clear()
    for rate in get_model_rates():
        rates_model.append(rate)
