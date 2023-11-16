from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


DB_FILE = '../data_test8.db'

engine = create_engine(f'sqlite:///{DB_FILE}', future=True, echo=True)
Base = declarative_base()
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(engine)


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
