from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from wg_mesh_gen.models import Base, KeyPair


def init_keystore(db_url: str = 'sqlite:///wg_keys.db'):
    """
    Initialize SQLite keystore for storing KeyPairs.
    """
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def save_key(session, name: str, private_key: str, public_key: str, psk: str = None):
    """
    Save or update a KeyPair in the keystore.
    """
    kp = session.query(KeyPair).filter_by(name=name).first()
    if kp:
        kp.private_key = private_key
        kp.public_key = public_key
        kp.psk = psk
    else:
        kp = KeyPair(name=name, private_key=private_key, public_key=public_key, psk=psk)
        session.add(kp)
    session.commit()


def load_key(session, name: str) -> KeyPair:
    """
    Load KeyPair by node name.
    """
    return session.query(KeyPair).filter_by(name=name).first()
