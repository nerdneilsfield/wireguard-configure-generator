"""
String processing utilities
"""

import re
from typing import Union


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')
    
    # Ensure not empty
    if not sanitized:
        sanitized = 'unnamed'
    
    return sanitized


def mask_sensitive_info(value: str, show_chars: int = 4) -> str:
    """
    遮蔽敏感信息，只显示前后几个字符

    Args:
        value: 要遮蔽的值
        show_chars: 显示的字符数

    Returns:
        遮蔽后的字符串
    """
    if not value:
        return ""

    # 对于非常短的字符串，特殊保护
    if len(value) <= 6:
        return "*" * len(value)

    # 对于短字符串，动态调整显示字符数
    if len(value) <= show_chars * 2 + 3:  # +3 for "..."
        actual_show = max(1, (len(value) - 3) // 2)
    else:
        actual_show = show_chars

    # 返回遮蔽的字符串
    return f"{value[:actual_show]}...{value[-actual_show:]}"