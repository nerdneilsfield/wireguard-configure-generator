"""
Configuration file renderer using Jinja2 templates
"""

import os
from pathlib import Path
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, Template
from .file_utils import ensure_dir, write_file
from .logger import get_logger


class ConfigRenderer:
    """Configuration file renderer"""
    
    def __init__(self, template_dir: str = None):
        """
        Initialize renderer with template directory.
        
        Args:
            template_dir: Path to template directory
        """
        self.logger = get_logger()
        
        if template_dir is None:
            # Use default template directory
            current_dir = Path(__file__).parent
            template_dir = current_dir / "templates"
        
        self.template_dir = Path(template_dir)
        
        if not self.template_dir.exists():
            self.logger.error(f"模板目录不存在: {template_dir}")
            raise FileNotFoundError(f"Template directory not found: {template_dir}")
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        self.logger.debug(f"配置渲染器初始化完成，模板目录: {template_dir}")
    
    def render_config(self, node_name: str, config: Dict[str, Any], output_dir: str):
        """
        Render WireGuard configuration file for a node.
        
        Args:
            node_name: Name of the node
            config: Node configuration data
            output_dir: Output directory
        """
        self.logger.debug(f"渲染节点配置: {node_name}")
        
        try:
            # Load template
            template = self.env.get_template("interface.conf.j2")
            
            # Render configuration
            rendered_config = template.render(
                node_name=node_name,
                interface=config['interface'],
                peers=config['peers']
            )
            
            # Write configuration file
            config_file = os.path.join(output_dir, f"{node_name}.conf")
            write_file(rendered_config, config_file)
            
            self.logger.info(f"配置文件已生成: {config_file}")
            
        except Exception as e:
            self.logger.error(f"渲染配置失败 {node_name}: {e}")
            raise
    
    def render_script(self, node_name: str, config: Dict[str, Any], output_dir: str):
        """
        Render setup script for a node.
        
        Args:
            node_name: Name of the node
            config: Node configuration data
            output_dir: Output directory
        """
        self.logger.debug(f"渲染设置脚本: {node_name}")
        
        try:
            # Load template
            template = self.env.get_template("wg-quick.sh.j2")
            
            # Render script
            rendered_script = template.render(
                node_name=node_name,
                interface=config['interface'],
                peers=config['peers']
            )
            
            # Write script file
            script_file = os.path.join(output_dir, f"{node_name}.sh")
            write_file(rendered_script, script_file)
            
            # Make script executable (on Unix systems)
            try:
                os.chmod(script_file, 0o755)
            except (OSError, AttributeError):
                # Windows or permission error
                pass
            
            self.logger.info(f"设置脚本已生成: {script_file}")
            
        except Exception as e:
            self.logger.error(f"渲染脚本失败 {node_name}: {e}")
            raise
    
    def render_all(self, build_result: Dict[str, Any]):
        """
        Render all configurations and scripts.
        
        Args:
            build_result: Result from build_peer_configs
        """
        configs = build_result['configs']
        output_dir = build_result['output_dir']
        
        self.logger.info(f"开始渲染所有配置文件到: {output_dir}")
        
        # Ensure output directory exists
        ensure_dir(output_dir)
        
        # Render each node's configuration and script
        for node_name, config in configs.items():
            self.render_config(node_name, config, output_dir)
            self.render_script(node_name, config, output_dir)
        
        self.logger.info(f"所有配置文件渲染完成，共 {len(configs)} 个节点")
