from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.engine import URL


# Database Configuration
DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username="root",
    password="Aryan@1234",
    host="localhost",
    port=3306,
    database="fastapi_db"
)


# Database Engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


# Database Session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# Base Model
Base = declarative_base()


# Database Dependency
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()