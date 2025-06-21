"""
File operation utilities
"""

import json
import yaml
import os
from pathlib import Path
from typing import Any, Dict
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
    Load configuration file (YAML or JSON).

    Args:
        file_path: Path to configuration file

    Returns:
        Loaded configuration data
    """
    logger = get_logger()
    logger.debug(f"加载配置文件: {file_path}")

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