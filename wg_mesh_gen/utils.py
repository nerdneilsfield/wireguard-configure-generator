"""
Utility functions for WireGuard mesh generator
"""

import json
import yaml
import jsonschema
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Union
from .logger import get_logger


def ensure_dir(path: str) -> None:
    """
    Ensure directory exists, create if not.

    Args:
        path: Directory path to ensure
    """
    Path(path).mkdir(parents=True, exist_ok=True)


def load_json(file_path: str) -> Dict[str, Any]:
    """
    Load JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        Loaded JSON data
    """
    logger = get_logger()
    logger.debug(f"加载JSON文件: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_yaml(file_path: str) -> Dict[str, Any]:
    """
    Load YAML file.

    Args:
        file_path: Path to YAML file

    Returns:
        Loaded YAML data
    """
    logger = get_logger()
    logger.debug(f"加载YAML文件: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_config(file_path: str) -> Dict[str, Any]:
    """
    Load configuration file (auto-detect JSON/YAML).

    Args:
        file_path: Path to configuration file

    Returns:
        Loaded configuration data
    """
    logger = get_logger()

    if file_path.endswith('.yaml') or file_path.endswith('.yml'):
        logger.debug("检测到YAML格式")
        return load_yaml(file_path)
    elif file_path.endswith('.json'):
        logger.debug("检测到JSON格式")
        return load_json(file_path)
    else:
        # Try JSON first, then YAML
        try:
            return load_json(file_path)
        except json.JSONDecodeError:
            return load_yaml(file_path)


def save_yaml(data: Dict[str, Any], file_path: str) -> None:
    """
    Save data to YAML file.

    Args:
        data: Data to save
        file_path: Output file path
    """
    logger = get_logger()
    logger.debug(f"保存YAML文件: {file_path}")

    # Ensure directory exists
    ensure_dir(os.path.dirname(file_path))

    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def write_file(content: str, file_path: str) -> None:
    """
    Write content to file.

    Args:
        content: Content to write
        file_path: Output file path
    """
    logger = get_logger()
    logger.debug(f"写入文件: {file_path}")

    # Ensure directory exists
    ensure_dir(os.path.dirname(file_path))

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def validate_schema(data: Dict[str, Any], schema_path: str) -> bool:
    """
    Validate data against JSON schema.

    Args:
        data: Data to validate
        schema_path: Path to schema file

    Returns:
        True if valid, False otherwise
    """
    try:
        schema = load_json(schema_path)
        jsonschema.validate(data, schema)
        return True
    except ImportError:
        get_logger().warning("jsonschema not installed, skipping validation")
        return True
    except Exception as e:
        get_logger().error(f"Schema validation failed: {e}")
        return False


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除无效字符

    Args:
        filename: 原始文件名

    Returns:
        清理后的文件名
    """
    # 移除无效字符
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    # 移除前后空格
    sanitized = sanitized.strip()
    return sanitized


def flatten(nested: List[List[Any]]) -> List[Any]:
    """
    将二维列表展平为一维列表。
    """
    return [item for sublist in nested for item in sublist]


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    将列表分块

    Args:
        lst: 要分块的列表
        chunk_size: 块大小

    Returns:
        分块后的列表
    """
    if chunk_size <= 0:
        raise ValueError("Chunk size must be positive")

    chunks = []
    for i in range(0, len(lst), chunk_size):
        chunks.append(lst[i:i + chunk_size])
    return chunks


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
        # 对于7-11字符的字符串，只显示1个字符
        if len(value) <= 11:
            actual_show_chars = 1
        else:
            # 对于更长的字符串，显示更多字符，但不超过总长度的1/3
            actual_show_chars = max(1, min(show_chars // 2, len(value) // 3))
        return value[:actual_show_chars] + "..." + value[-actual_show_chars:]

    # 正常情况，显示指定数量的首尾字符
    return value[:show_chars] + "..." + value[-show_chars:]
