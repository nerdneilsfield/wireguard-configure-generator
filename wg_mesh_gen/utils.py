import os
import json
import jsonschema
import logging
from typing import Any, Dict, List


def ensure_dir(path: str) -> None:
    """
    确保目录存在，不存在则创建。
    """
    if path == "": return
    os.makedirs(path, exist_ok=True)


def load_json(path: str) -> Dict[str, Any]:
    """
    安全加载 JSON 文件。
    """
    with open(path, 'r', encoding='utf-8') as f:
        return json.loads(f.read())


def write_file(path: str, content: str) -> None:
    """
    安全写入文件（原子写入可扩展）。
    """
    ensure_dir(os.path.dirname(path))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def validate_schema(instance: Dict[str, Any], schema: Dict[str, Any]) -> None:
    """
    使用 jsonschema 验证 JSON 数据结构。
    在验证失败时抛出 jsonschema.ValidationError。
    """
    jsonschema.validate(instance=instance, schema=schema)


def init_logger(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    """
    初始化并返回一个 Logger，输出到控制台。
    """
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger


def chunk_list(data: List[Any], size: int) -> List[List[Any]]:
    """
    将列表分块。

    Args:
        data: 原始列表
        size: 分块大小

    Returns:
        分块后的列表列表
    """
    return [data[i:i + size] for i in range(0, len(data), size)]

# 其他实用函数

def sanitize_filename(name: str) -> str:
    """
    将名称转为安全的文件名。
    """
    return ''.join(c for c in name if c.isalnum() or c in (' ', '.', '_')).rstrip()


def flatten(nested: List[List[Any]]) -> List[Any]:
    """
    将二维列表展平为一维列表。
    """
    return [item for sublist in nested for item in sublist]
