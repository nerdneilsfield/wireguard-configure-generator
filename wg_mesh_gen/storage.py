"""
Key storage management for WireGuard mesh generator
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, KeyPair
from .logger import get_logger


class KeyStorage:
    """Key storage manager using SQLite database"""

    def __init__(self, db_path: str = "wg_keys.db"):
        self.db_path = db_path
        # 添加连接池配置，确保连接能正确关闭
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.logger = get_logger()

    def store_keypair(self, name: str, private_key: str, public_key: str, psk: str = None):
        """Store a key pair in the database"""
        try:
            # Check if key already exists
            existing = self.session.query(KeyPair).filter_by(name=name).first()
            if existing:
                self.logger.warning(f"密钥对 {name} 已存在，将更新")
                existing.private_key = private_key
                existing.public_key = public_key
                existing.psk = psk
            else:
                keypair = KeyPair(
                    name=name,
                    private_key=private_key,
                    public_key=public_key,
                    psk=psk
                )
                self.session.add(keypair)

            self.session.commit()
            self.logger.debug(f"已存储密钥对: {name}")

        except Exception as e:
            self.session.rollback()
            self.logger.error(f"存储密钥对失败: {e}")
            raise

    def get_keypair(self, name: str):
        """Get a key pair from the database"""
        try:
            keypair = self.session.query(KeyPair).filter_by(name=name).first()
            if keypair:
                return {
                    'private_key': keypair.private_key,
                    'public_key': keypair.public_key,
                    'psk': keypair.psk
                }
            return None
        except Exception as e:
            self.logger.error(f"获取密钥对失败: {e}")
            return None

    def list_keys(self):
        """List all stored keys"""
        try:
            keypairs = self.session.query(KeyPair).all()
            return [kp.name for kp in keypairs]
        except Exception as e:
            self.logger.error(f"列出密钥失败: {e}")
            return []

    def delete_keypair(self, name: str):
        """Delete a key pair from the database"""
        try:
            keypair = self.session.query(KeyPair).filter_by(name=name).first()
            if keypair:
                self.session.delete(keypair)
                self.session.commit()
                self.logger.debug(f"已删除密钥对: {name}")
                return True
            return False
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"删除密钥对失败: {e}")
            return False

    def close(self):
        """Close the database session and engine"""
        try:
            if self.session:
                self.session.close()
            if self.engine:
                self.engine.dispose()
        except Exception as e:
            self.logger.error(f"关闭数据库连接时出错: {e}")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
