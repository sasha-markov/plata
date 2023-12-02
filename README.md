# Plata

Plata is a GTK application for tracking balances of financial accounts
in different currencies. It is a personal project for learning SQL and
object-oriented design. The main features are:

- Maintain the table containing balances or digital assets with
  breakdown by category
- Convert and sum balances using up-to-date exchange rates and prices
- Store exchange rates, prices, and balances to analyze changes over time

## Intro


## Storage

Application stores data in three tables: `accounts`, `balances`,
`exchange_rates`.

### Tables

    class Account(Base):
        __tablename__ = 'accounts'
        id = Column(Integer, primary_key=True)
        name = Column(String)
        currency = Column(String)
        categories = Column(String)

    class Balance(Base):
        __tablename__ = 'balances'
        id = Column(Integer, primary_key=True)
        account = Column(String)
        updated = Column(String)
        data = Column(Float)

    class Rate(Base):
        __tablename__ = 'exchange_rates'
        id = Column(Integer, primary_key=True)
        updated = Column(String)
        currency1 = Column(String)
        currency2 = Column(String)
        data = Column(Float)
