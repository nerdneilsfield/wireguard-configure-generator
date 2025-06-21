"""
Data processing utilities
"""

import jsonschema
import os
from typing import Any, Dict, List
from .logger import get_logger


def validate_schema(data: Dict[str, Any], schema_path: str) -> bool:
    """
    Validate data against JSON schema.

    Args:
        data: Data to validate
        schema_path: Path to schema file

    Returns:
        True if validation passes

    Raises:
        jsonschema.ValidationError: If validation fails
    """
    logger = get_logger()
    logger.debug(f"验证数据结构: {schema_path}")

    # Load schema
    schema_file = os.path.join(os.path.dirname(__file__), 'schema', schema_path)
    
    with open(schema_file, 'r', encoding='utf-8') as f:
        import json
        schema = json.load(f)

    # Validate
    try:
        jsonschema.validate(data, schema)
        logger.debug("数据结构验证通过")
        return True
    except jsonschema.ValidationError as e:
        logger.error(f"数据结构验证失败: {e}")
        raise


def flatten(nested: List[List[Any]]) -> List[Any]:
    """
    展平嵌套列表

    Args:
        nested: 嵌套的列表

    Returns:
        展平后的列表
    """
    return [item for sublist in nested for item in sublist]


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    将列表分块

    Args:
        lst: 要分块的列表
        chunk_size: 每块大小

    Returns:
        分块后的列表
    
    Raises:
        ValueError: 如果块大小无效
    """
    if chunk_size <= 0:
        raise ValueError(f"Invalid chunk size: {chunk_size}. Must be positive.")
    
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]