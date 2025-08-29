"""
WQB Expression Validator 配置管理
"""

import os
import json
from pathlib import Path
from typing import Dict, Any


class Config:
    """配置管理类"""

    def __init__(self):
        self._config = None
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        try:
            # 获取包目录
            package_dir = Path(__file__).parent
            config_path = package_dir / "config.json"

            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            else:
                # 使用默认配置
                self._config = {
                    "BASE_URL": "https://api.worldquantbrain.com",
                    "DATA_DIR": "data",
                }
        except Exception as e:
            # 使用默认配置
            self._config = {
                "BASE_URL": "https://api.worldquantbrain.com",
                "DATA_DIR": "data",
            }

    @property
    def BASE_URL(self) -> str:
        """获取API基础URL"""
        return self._config.get("BASE_URL", "https://api.worldquantbrain.com")

    @property
    def DATA_DIR(self) -> str:
        """获取数据目录"""
        return self._config.get("DATA_DIR", "data")

    def get_data_path(self, filename: str) -> Path:
        """获取数据文件路径"""
        package_dir = Path(__file__).parent
        return package_dir / self.DATA_DIR / filename

    def get_grammar_path(self, filename: str) -> Path:
        """获取语法文件路径"""
        package_dir = Path(__file__).parent
        return package_dir / "grammar" / filename


# 全局配置实例
config = Config()

# 导出配置常量
BASE_URL = config.BASE_URL
DATA_DIR = config.DATA_DIR
