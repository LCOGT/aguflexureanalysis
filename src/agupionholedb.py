import sqlite3
from sqlalchemy import Column, Integer, Float, create_engine, pool
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
    dateobs = Column ()