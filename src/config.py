"""
Pixiv MCP Server - Configuration Management
配置管理模块
"""

import os
from typing import Optional
from pathlib import Path
from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    """服务器配置"""
    host: str = Field(default="0.0.0.0", description="服务器主机地址")
    port: int = Field(default=8080, description="服务器端口")
    workers: int = Field(default=1, description="工作进程数")
    reload: bool = Field(default=False, description="开发模式自动重载")
    log_level: str = Field(default="info", description="日志级别")
    cors_origins: list = Field(default=["*"], description="CORS允许的源")


class PixivConfig(BaseModel):
    """Pixiv API配置"""
    refresh_token: Optional[str] = Field(default=None, description="Pixiv refresh token")
    proxy_url: Optional[str] = Field(default=None, description="代理URL")
    timeout: int = Field(default=30, description="API请求超时时间（秒）")
    rate_limit: int = Field(default=60, description="每分钟请求限制")


class Config(BaseModel):
    """完整配置"""
    server: ServerConfig = Field(default_factory=ServerConfig)
    pixiv: PixivConfig = Field(default_factory=PixivConfig)
    
    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置"""
        server_config = ServerConfig(
            host=os.getenv("SERVER_HOST", "0.0.0.0"),
            port=int(os.getenv("SERVER_PORT", "8080")),
            workers=int(os.getenv("SERVER_WORKERS", "1")),
            reload=os.getenv("SERVER_RELOAD", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "info").lower(),
            cors_origins=os.getenv("CORS_ORIGINS", "*").split(",")
        )
        
        pixiv_config = PixivConfig(
            refresh_token=os.getenv("PIXIV_REFRESH_TOKEN"),
            proxy_url=os.getenv("PROXY_URL"),
            timeout=int(os.getenv("PIXIV_TIMEOUT", "30")),
            rate_limit=int(os.getenv("PIXIV_RATE_LIMIT", "60"))
        )
        
        return cls(server=server_config, pixiv=pixiv_config)
    
    @classmethod 
    def from_env_file(cls, env_file: Optional[Path] = None) -> "Config":
        """从.env文件加载配置"""
        if env_file is None:
            # 获取项目根目录
            project_root = Path(__file__).parent.parent
            env_file = project_root / ".env"
        
        # 读取.env文件
        if env_file.exists():
            env_vars = {}
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip()
                
                # 临时设置环境变量
                for key, value in env_vars.items():
                    os.environ.setdefault(key, value)
                    
            except Exception as e:
                print(f"警告：读取.env文件失败: {e}")
        
        return cls.from_env()


# 全局配置实例
config = Config.from_env_file()