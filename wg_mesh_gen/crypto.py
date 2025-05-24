import base64
from typing import Tuple
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives import serialization


def gen_private_key() -> str:
    """
    生成 WireGuard X25519 私钥，并返回 Base64 编码字符串。
    """
    private_key = X25519PrivateKey.generate()
    raw = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    return base64.b64encode(raw).decode()


def gen_public_key(privkey_b64: str) -> str:
    """
    根据 Base64 编码的私钥推导对应的公钥，并返回 Base64 编码字符串。
    """
    raw_priv = base64.b64decode(privkey_b64)
    private_key = X25519PrivateKey.from_private_bytes(raw_priv)
    public_key = private_key.public_key()
    raw_pub = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    return base64.b64encode(raw_pub).decode()


def gen_psk() -> str:
    """
    生成 WireGuard 预共享密钥，与私钥生成相同，返回 Base64 编码字符串。
    """
    return gen_private_key()


def gen_keypair() -> Tuple[str, str, str]:
    """
    生成 WireGuard 密钥对，包括私钥、公钥和预共享密钥，
    并返回 Base64 编码的字符串元组 (privkey, pubkey, psk)。
    """
    privkey = gen_private_key()
    pubkey = gen_public_key(privkey)
    psk = gen_psk()
    return (privkey, pubkey, psk)
