import os
from typing import List, Dict, Any
from wg_mesh_gen.utils import load_json, validate_schema


def load_json_file(path: str) -> Dict[str, Any]:
    """
    Load a JSON file and return its content.
    """
    return load_json(path)


def get_schema_path(config_dir: str, name: str) -> str:
    """
    Return the path to a schema file located in the package's schema directory.
    """
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    schema_dir = os.path.join(pkg_dir, 'schema')
    return os.path.join(schema_dir, f"{name}.schema.json")


def load_nodes(nodes_path: str, config_dir: str = None) -> List[Dict[str, Any]]:
    """
    Load and validate nodes configuration.

    Args:
        nodes_path: Path to nodes.json file
        config_dir: Optional config directory for schema validation
    """
    data = load_json_file(nodes_path)
    if config_dir:
        schema_path = get_schema_path(config_dir, 'nodes')
        if os.path.exists(schema_path):
            schema = load_json_file(schema_path)
            validate_schema(data, schema)
    return data.get('nodes', [])


def load_topology(topo_path: str, config_dir: str = None) -> List[Dict[str, Any]]:
    """
    Load and validate topology configuration.

    Args:
        topo_path: Path to topology.json file
        config_dir: Optional config directory for schema validation
    """
    data = load_json_file(topo_path)
    if config_dir:
        schema_path = get_schema_path(config_dir, 'topology')
        if os.path.exists(schema_path):
            schema = load_json_file(schema_path)
            validate_schema(data, schema)
    return data.get('peers', [])
