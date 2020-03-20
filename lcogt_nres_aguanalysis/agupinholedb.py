import logging
import os

from sqlalchemy import Column, Float, String, DateTime, create_engine, pool, exists
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

log = logging.getLogger(__name__)

Base = declarative_base()


class PinholeMeasurement(Base):
    __tablename__ = 'pinholemasurements'

    imagename = Column(String, primary_key=True)
    instrument = Column(String, index=True)
    telescopeidentifier = Column(String, index=True)  # Use SITE-ENCLOSURE-1m0a, e.g., lsc-domb-1m0a
    altitude = Column(Float)
    azimut = Column(Float)
    xcenter = Column(Float)
    ycenter = Column(Float)
    crpix1 = Column(Float)
    crpix2 = Column(Float)
    dateobs = Column(DateTime)
    foctemp = Column(Float)

    def __repr__(self):
        return "<PinholeMeasurement(image='%s', telescope='%s', instrument='%s', x='% 6.2f', y='% 6.2f')>" % (
            self.imagename, self.telescopeidentifier, self.instrument,
            self.xcenter if self.xcenter is not None else 0,
            self.ycenter if self.ycenter is not None else 0)


Base_v1 = declarative_base()


class PinholeMeasurement_v1(Base_v1):
    __tablename__ = 'pinholemasurements'

    imagename = Column(String, primary_key=True)
    instrument = Column(String, index=True)
    altitude = Column(Float)
    azimut = Column(Float)
    xcenter = Column(Float)
    ycenter = Column(Float)
    dateobs = Column(DateTime)
    foctemp = Column(Float)

    def __repr__(self):
        return "<PinholeMeasurement(image='%s', telescope='%s', instrument='%s', x='% 6.2f', y='% 6.2f')>" % (
            self.imagename, self.telescopidentifier, self.instrument,
            self.xcenter if self.xcenter is not None else 0,
            self.ycenter if self.ycenter is not None else 0)


def pinholefrompinhole_v1(e: PinholeMeasurement_v1):
    r = PinholeMeasurement(imagename=os.path.basename(e.imagename),
                           instrument=e.instrument,
                           altitude=e.altitude,
                           azimut=e.azimut,
                           xcenter=e.xcenter,
                           ycenter=e.ycenter,
                           dateobs=e.dateobs,
                           foctemp=e.foctemp,
                           crpix1=-1,
                           crpix2=-1,
                           telescopeidentifier=_t_from_ak(e.instrument)
                           )
    return r


def _t_from_ak(i):
    if i in ['ak01', ]:
        return 'lsc-domb-1m0a'
    if i in ['ak02', ]:
        return 'lsc-domc-1m0a'
    if i in ['ak04', 'ak11']:
        return 'elp-doma-1m0a'
    if i in ['ak07', ]:
        return 'elp-domb-1m0a'
    if i in ['ak06']:
        return 'cpt-domb-1m0a'
    if i in ['ak05']:
        return 'cpt-domc-1m0a'
    if i in ['ak03', 'ak10', 'ak12']:
        return 'tlv-doma-1m0a'
    print("Error: non-existing camera")
    exit(1)
    return None


def doesRecordExists(session, filename):
    ret = session.query(exists().where(PinholeMeasurement.imagename == os.path.basename(filename))).scalar()
    log.debug(f"Checking if {filename} exists: {ret}")
    return ret


def get_session(db_address, Base=Base):
    """
    Get a connection to the database.
    Returns
    -------
    session: SQLAlchemy Database Session
    """
    # Build a new engine for each session. This makes things thread safe.
    engine = create_engine(db_address, poolclass=pool.NullPool, echo=False)
    PinholeMeasurement.__table__.create(bind=engine, checkfirst=True)
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
