import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from sqlalchemy import select

from database import Session
from helpers import get_localtime
from models import Rate, LastRate, select_rates, subq_rates
from views import CreateView, DropView


TITLE = 'New Rate'
WINDOW_WIDTH=350
R = 1.618  # golden ratio


def add_rate(currency: str, data: float):
    with Session.begin() as session:
        rate = Rate(updated=get_localtime(),
                    currency1=currency,
                    currency2='USD',
                    data=data)
        session.add(rate)

    with Session.begin() as session:
        session.execute(DropView('vrates'))
        session.execute(CreateView('vrates', select_rates))
        rows = session.query(
            select(LastRate.currency1, LastRate.data).subquery()
        ).all()
    rates = Gtk.ListStore(str, float)
    [rates.append(row) for row in rows]

    return rates


class NewRateWin(Gtk.Window):
    def __init__(self, parent, **kwargs):
        super().__init__(transient_for=parent, **kwargs)

        self.parent = parent
        self.rates_model = parent.rates_model

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
        new_model = add_rate(self.currency_entry.get_text(),
                             self.rate_entry.get_text())
        self.parent.rates_treeview.set_model(new_model)
        self.close()
