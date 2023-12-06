import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from helpers import settings

DB_FILE = '../data_test9.db'

DEFAULT_DB_FILENAME = 'untitled.db'
TMPDIR = '/tmp/'

# Code from sqlalchemy-utils
def sqlite_file_exists(database):
    if not os.path.isfile(database) or os.path.getsize(database) < 100:
        return False

    with open(database, 'rb') as f:
        header = f.read(100)

    return header[:16] == b'SQLite format 3\x00'

def open_db(database):
    return create_engine(f'sqlite:///{database}', future=True, echo=True)


last_opened = settings['recent_db_files'][0]
if sqlite_file_exists(last_opened):
    engine = create_engine(f'sqlite:///{last_opened}',
                           future=True,
                           echo=True)
else:
    engine = create_engine(f'sqlite:///{TMP + DEFAULT_DB_FILENAME}',
                           future=True,
                           echo=True)
    Base.metadata.create_all(engine)
    

Base = declarative_base()
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db(e):
    Base.metadata.create_all(e)


# def get_db():
#     db = Session()
#     try:
#         yield db
#     finally:
#         db.close()
