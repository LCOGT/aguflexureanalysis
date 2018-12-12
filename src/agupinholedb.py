import sqlite3
from sqlalchemy import Column, Integer, Float, String, DateTime, create_engine, pool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging


log = logging.getLogger(__name__)

Base = declarative_base()

class PinholeMeasurement (Base):
    __tablename__ = 'pinholemasurements'

    imagename = Column (String, primary_key=True)
    altitude = Column (Float)
    azimut = Column(Float)
    xcenter = Column(Float)
    ycenter= Column(Float)
    dateobs = Column (DateTime)


def get_session(db_address):
    """
    Get a connection to the database.
    Returns
    -------
    session: SQLAlchemy Database Session
    """
    # Build a new engine for each session. This makes things thread safe.
    engine = create_engine(db_address, poolclass=pool.NullPool)
    Base.metadata.bind = engine

    # We don't use autoflush typically. I have run into issues where SQLAlchemy would try to flush
    # incomplete records causing a crash. None of the queries here are large, so it should be ok.
    db_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = db_session()
    return session

def create_db(db_address):
    # Create an engine for the database
    engine = create_engine(db_address)

    # Create all tables in the engine
    # This only needs to be run once on initialization.
    Base.metadata.create_all(engine)


