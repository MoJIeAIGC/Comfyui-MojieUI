from pathlib import Path
import configparser


class ConfigUtils:
    _instance = None  # 单例模式
    _config = None

    def __new__(cls, config_path=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_config(config_path)
        return cls._instance

    def _init_config(self, config_path=None):
        """初始化配置文件"""
        if config_path is None:
            # 默认路径：项目根目录/config/config.ini
            config_path = Path(__file__).parent.parent / "config" / "config.ini"

        if not Path(config_path).exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        self._config = configparser.ConfigParser()
        self._config.read(config_path)

    @classmethod
    def get(cls, section: str, key: str, default=None):
        """获取配置参数"""
        if cls._instance is None or cls._instance._config is None:
            cls()  # 自动初始化
        try:
            return cls._instance._config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if default is not None:
                return default
            raise

    @classmethod
    def get_path(cls, section: str, key: str, base_dir=None) -> str:
        """获取路径配置（自动拼接为绝对路径）"""
        relative_path = cls.get(section, key)
        if base_dir is None:
            base_dir = Path(__file__).parent.parent  # 默认项目根目录
        return str(Path(base_dir) / relative_path)