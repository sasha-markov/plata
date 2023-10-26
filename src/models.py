from sqlalchemy import insert, delete, desc, select, text, \
                       func, update, Table, Column, Float, Integer, String, \
                       MetaData

from sqlalchemy.sql import table

from views import view, CreateView, DropView

from database import Base


class Account(Base):
    """ Describe an account """

    __tablename__ = 'accounts'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    currency = Column(String)
    categories = Column(String)


class Balance(Base):
    """ Describe a balance """

    __tablename__ = 'balances'
    id = Column(Integer, primary_key=True)
    account = Column(String)
    updated = Column(String)
    data = Column(Float)


class Rate(Base):
    """ Describe an exchange rate """

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


subq_accounts = (
    select(
        LastBalance.account,
        LastBalance.data,
        func.round(LastBalance.data * LastRate.data).label('usd'),
        Account.categories,
    )
    .join(Account, LastBalance.account == Account.name)
    .join(LastRate, Account.currency == LastRate.currency1)
    # .where(LastBalance.data != 0)
    .order_by(desc('usd'))
).subquery()

