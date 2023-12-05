import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


DB_FILE = '../data_test10.db'

DEFAULT_DB_FILENAME = 'untitled.db'
TMPDIR = '/tmp/'

engine = create_engine(f'sqlite:///{TMPDIR + DEFAULT_DB_FILENAME}',
                       future=True,
                       echo=True)
Base = declarative_base()
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Code from sqlalchemy-utils
def sqlite_file_exists(database = DB_FILE):
    if not os.path.isfile(database) or os.path.getsize(database) < 100:
        return False

    with open(database, 'rb') as f:
        header = f.read(100)

    return header[:16] == b'SQLite format 3\100'


def init_db():
    Base.metadata.create_all(engine)


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
