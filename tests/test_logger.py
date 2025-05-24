"""
测试日志系统
"""

import pytest
import tempfile
import os
from wg_mesh_gen.logger import get_logger, setup_logging, SingletonLogger


class TestSingletonLogger:
    """测试单例日志器"""
    
    def test_singleton_behavior(self):
        """测试单例模式"""
        logger1 = get_logger()
        logger2 = get_logger()
        
        # 应该是同一个实例
        assert logger1 is logger2
        assert isinstance(logger1, SingletonLogger)
    
    def test_logger_instance(self):
        """测试日志器实例"""
        logger = get_logger()
        
        # 应该有logger属性
        assert hasattr(logger, 'logger')
        assert logger.logger is not None
    
    def test_log_levels(self):
        """测试日志级别设置"""
        logger = get_logger()
        
        # 测试设置不同级别
        logger.set_level('DEBUG')
        assert logger.logger.level == 10  # DEBUG level
        
        logger.set_level('INFO')
        assert logger.logger.level == 20  # INFO level
        
        logger.set_level('WARNING')
        assert logger.logger.level == 30  # WARNING level
    
    def test_log_methods(self):
        """测试日志方法"""
        logger = get_logger()
        
        # 这些方法应该不抛出异常
        logger.info("Test info message")
        logger.debug("Test debug message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        logger.critical("Test critical message")
    
    def test_file_handler(self):
        """测试文件处理器"""
        # 创建一个新的logger实例来避免单例问题
        import logging
        test_logger = logging.getLogger('test_file_handler')
        test_logger.setLevel(logging.INFO)
        
        # 清理已有的处理器
        for handler in test_logger.handlers[:]:
            test_logger.removeHandler(handler)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            log_file = f.name
        
        try:
            # 创建文件处理器
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            test_logger.addHandler(file_handler)
            
            # 写入日志
            test_logger.info("Test file logging")
            
            # 强制刷新和关闭处理器
            file_handler.flush()
            file_handler.close()
            test_logger.removeHandler(file_handler)
            
            # 检查文件是否存在且有内容
            assert os.path.exists(log_file)
            
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "Test file logging" in content
                
        finally:
            # 清理文件
            try:
                os.unlink(log_file)
            except (OSError, PermissionError):
                pass


class TestSetupLogging:
    """测试日志设置函数"""
    
    def test_setup_logging_verbose(self):
        """测试详细模式设置"""
        setup_logging(verbose=True)
        logger = get_logger()
        
        # 详细模式应该设置为DEBUG级别
        assert logger.logger.level == 10  # DEBUG level
    
    def test_setup_logging_normal(self):
        """测试普通模式设置"""
        setup_logging(verbose=False)
        logger = get_logger()
        
        # 普通模式应该设置为INFO级别
        assert logger.logger.level == 20  # INFO level
    
    def test_setup_logging_with_file(self):
        """测试带文件的日志设置"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            log_file = f.name
        
        try:
            setup_logging(verbose=True, log_file=log_file)
            logger = get_logger()
            
            # 写入测试日志
            logger.info("Test setup logging with file")
            
            # 检查文件
            assert os.path.exists(log_file)
            
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "Test setup logging with file" in content
                
        finally:
            # 清理
            try:
                os.unlink(log_file)
            except (OSError, PermissionError):
                pass
