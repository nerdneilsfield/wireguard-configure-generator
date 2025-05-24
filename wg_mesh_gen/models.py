from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class KeyPair(Base):
    """
    ORM model for storing WireGuard key pairs.
    """
    __tablename__ = 'keys'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    private_key = Column(String, nullable=False)
    public_key = Column(String, nullable=False)
    psk = Column(String, nullable=True)
