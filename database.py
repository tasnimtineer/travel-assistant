"""
قاعدة بيانات بسيطة (SQLite) لتخزين بيانات العملاء والحجوزات.
لاستخدام PostgreSQL في الإنتاج، فقط غيّر DATABASE_URL في .env
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///travel_agency.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    booking_details = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()
