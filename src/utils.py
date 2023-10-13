
"""
utils.py - track financial accounts (SQLAlchemy version)
"""

from sqlalchemy import create_engine, insert, delete, desc, select, text, \
                       func, update, Table, Column, Float, Integer, String, \
                       MetaData

from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.sql import table

from helpers import get_localtime, get_rates
from views import view, CreateView, DropView


DB_FILE = '../data_test7.db'


Base = declarative_base()
engine = create_engine(f'sqlite:///{DB_FILE}', future=True, echo=True)


class Account(Base):
    """ Describe an account
    """

    __tablename__ = 'accounts'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    currency = Column(String)
    categories = Column(String)

    def add(self):
        with Session(engine) as session, session.begin():
            stmt = insert(Account).values(name=self.name,
                                          currency=self.currency,
                                          categories=self.categories)
            session.execute(stmt)


class Balance(Base):
    """ Describe a balance
    """

    __tablename__ = 'balances'
    id = Column(Integer, primary_key=True)
    account = Column(String)
    updated = Column(String)
    data = Column(Float)

    def set(self):
        with Session(engine) as session, session.begin():
            stmt = insert(Balance).values(account=self.account,
                                          updated=get_localtime(),
                                          data=self.data)
            session.execute(stmt)


class Rate(Base):
    """ Describe an exchange rate
    
    """

    __tablename__ = 'exchange_rates'
    id = Column(Integer, primary_key=True)
    updated = Column(String)
    currency1 = Column(String)
    currency2 = Column(String)
    data = Column(Float)


subq_rates = (
    select(
        Rate.id,
        Rate.currency1,
        Rate.data,
        Rate.updated,
        func.row_number().over(
            order_by=Rate.updated.desc(), partition_by=Rate.currency1)
        .label('rn')
    ).subquery()
)

select_rates = (
    select(
        subq_rates.c.id.label('id'),
        subq_rates.c.currency1.label('currency1'),
        subq_rates.c.data.label('data'),
        subq_rates.c.updated.label('updated'),
    )
    .where(subq_rates.c.rn == 1)
)

subq_balances = (
    select(
        Balance.id,
        Balance.account,
        Balance.updated,
        Balance.data,
        func.row_number().over(
            order_by=Balance.updated.desc(), partition_by=Balance.account)
        .label('rn')
    )
    .subquery()
)

select_balances = (
    select(
        subq_balances.c.id.label('id'),
        subq_balances.c.account.label('account'),
        subq_balances.c.updated.label('updated'),
        subq_balances.c.data.label('data'),
    )
    .where(subq_balances.c.rn == 1)    
)

rates_view = view('vrates', Base.metadata, select_rates)
assert rates_view.primary_key == [rates_view.c.id]

balances_view = view('vbalances', Base.metadata, select_balances)
assert balances_view.primary_key == [balances_view.c.id]


class LastRate(Base):
    __table__ = rates_view


class LastBalance(Base):
    __table__ = balances_view


def init_db():
    Base.metadata.create_all(engine)

def update_rates():
    with Session(engine) as session, session.begin():
        rows = session.execute(select(Account.currency))
        currencies = set([row[0] for row in rows])
        rates = get_rates(currencies)
        for currency, rate in rates.items():
            session.add(Rate(updated=get_localtime(),
                             currency1=currency,
                             currency2='USD',
                             data=rate)
                        )
        session.execute(DropView('vrates'))
        session.execute(CreateView('vrates', select_rates))

def get_accounts():
    with Session(engine) as session, session.begin():
        stmt = (
            select(
                LastBalance.account,
                LastBalance.data,
                func.round(LastBalance.data * LastRate.data).label('usd'),
                Account.categories,                
            )
        .join(Account, LastBalance.account == Account.name)
        .join(LastRate, Account.currency == LastRate.currency1)
        .where(LastBalance.data != 0)
        .order_by(desc('usd'))
        )
        return session.execute(stmt).all()

def get_account(name):
    with Session(engine) as session, session.begin():
        stmt = (
            select(
                Balance.account,
                Account.currency,
                Balance.data,
                Account.categories,
                )
            .join(Balance, Balance.account == Account.name)
            .where(Account.name == name)
            )
        return session.execute(stmt).first()

def get_model_rates():
    with Session(engine) as session, session.begin():
        stmt = select(LastRate.currency1, LastRate.data)
        return session.execute(stmt).all()

def update_categories(account, categories):
    with Session(engine) as session, session.begin():
        stmt = (
            update(Account)
            .where(Account.name == account)
            .values(categories=categories)
            .execution_options(synchronize_session='fetch')
        )
        return session.execute(stmt)

def create_account(name, currency, categories):
    with Session(engine) as session, session.begin():
        stmt = insert(Account).values(name=name,
                                      currency=currency,
                                      categories=categories)
        session.execute(stmt)

def delete_account(name):
    with Session(engine) as session, session.begin():
        stmt = delete(Account).where(Account.name == name)
        return session.execute(stmt)

def set_balance(account, data):
    with Session(engine) as session, session.begin():
        stmt = insert(Balance).values(account=account,
                                      updated=get_localtime(),
                                      data=data)
        session.execute(stmt)
        session.execute(DropView('vbalances'))
        session.execute(CreateView('vbalances', select_balances))
        
# def get_account(account):
#     with Session(engine) as session, session.begin():
#         stmt = 
#     return Account

def create_table_views():
    with Session(engine) as session, session.begin():
        session.execute(DropView('vbalances'))
        session.execute(CreateView('vbalances', select_balances))
