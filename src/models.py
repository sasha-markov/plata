import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

from utils import get_model_accounts


# Creating the ListStore models
accounts_model = Gtk.ListStore(str, float, float, str)


def update_accounts_model():
    accounts_model.clear()
    for row in get_model_accounts():
        accounts_model.append(row)
