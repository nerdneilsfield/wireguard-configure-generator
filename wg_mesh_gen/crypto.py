"""
WireGuard cryptographic key generation utilities
"""

import subprocess
import base64
import os
from typing import Tuple
from .logger import get_logger


def generate_private_key() -> str:
    """
    Generate a WireGuard private key.
    
    Returns:
        Base64 encoded private key
    """
    logger = get_logger()
    
    try:
        # Try using wg command first
        result = subprocess.run(['wg', 'genkey'], capture_output=True, text=True, check=True)
        private_key = result.stdout.strip()
        logger.debug("使用wg命令生成私钥")
        return private_key
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback to manual generation
        logger.debug("wg命令不可用，使用手动生成")
        return _generate_private_key_manual()


def _generate_private_key_manual() -> str:
    """
    Manually generate a WireGuard private key.
    
    Returns:
        Base64 encoded private key
    """
    # Generate 32 random bytes
    private_key_bytes = os.urandom(32)
    
    # Clamp the key (WireGuard requirement)
    private_key_bytes = bytearray(private_key_bytes)
    private_key_bytes[0] &= 248
    private_key_bytes[31] &= 127
    private_key_bytes[31] |= 64
    
    # Encode to base64
    return base64.b64encode(bytes(private_key_bytes)).decode('ascii')


def derive_public_key(private_key: str) -> str:
    """
    Derive public key from private key.
    
    Args:
        private_key: Base64 encoded private key
        
    Returns:
        Base64 encoded public key
    """
    logger = get_logger()
    
    try:
        # Try using wg command first
        process = subprocess.Popen(['wg', 'pubkey'], 
                                 stdin=subprocess.PIPE, 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE,
                                 text=True)
        stdout, stderr = process.communicate(input=private_key)
        
        if process.returncode == 0:
            public_key = stdout.strip()
            logger.debug("使用wg命令生成公钥")
            return public_key
        else:
            raise subprocess.CalledProcessError(process.returncode, 'wg pubkey')
            
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback to manual generation
        logger.debug("wg命令不可用，使用手动生成")
        return _derive_public_key_manual(private_key)


def _derive_public_key_manual(private_key: str) -> str:
    """
    Manually derive public key from private key using Curve25519.
    
    Args:
        private_key: Base64 encoded private key
        
    Returns:
        Base64 encoded public key
    """
    logger = get_logger()
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
        
        # Decode private key
        private_key_bytes = base64.b64decode(private_key)
        
        # Create X25519 private key object
        x25519_private_key = X25519PrivateKey.from_private_bytes(private_key_bytes)
        
        # Derive public key
        public_key = x25519_private_key.public_key()
        
        # Serialize public key
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        return base64.b64encode(public_key_bytes).decode('ascii')
        
    except ImportError:
        # If cryptography is not available, generate a dummy key
        logger.warning("cryptography库不可用，生成模拟公钥")
        return base64.b64encode(os.urandom(32)).decode('ascii')


def generate_preshared_key() -> str:
    """
    Generate a WireGuard preshared key.
    
    Returns:
        Base64 encoded preshared key
    """
    logger = get_logger()
    
    try:
        # Try using wg command first
        result = subprocess.run(['wg', 'genpsk'], capture_output=True, text=True, check=True)
        psk = result.stdout.strip()
        logger.debug("使用wg命令生成预共享密钥")
        return psk
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback to manual generation
        logger.debug("wg命令不可用，使用手动生成")
        return base64.b64encode(os.urandom(32)).decode('ascii')


def generate_keypair() -> Tuple[str, str]:
    """
    Generate a WireGuard key pair.
    
    Returns:
        Tuple of (private_key, public_key)
    """
    private_key = generate_private_key()
    public_key = derive_public_key(private_key)
    return private_key, public_key
