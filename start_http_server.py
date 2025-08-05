#!/usr/bin/env python3
"""
Pixiv MCP HTTP Server 启动脚本
快速启动HTTP服务器的便捷脚本
"""

import sys
import argparse
import uvicorn
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import config
from http_server import create_app


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Pixiv MCP HTTP Server")
    parser.add_argument("--host", default=config.server.host, help="服务器主机地址")
    parser.add_argument("--port", type=int, default=config.server.port, help="服务器端口")
    parser.add_argument("--workers", type=int, default=config.server.workers, help="工作进程数")
    parser.add_argument("--reload", action="store_true", help="开发模式自动重载")
    parser.add_argument("--log-level", default=config.server.log_level, help="日志级别")
    
    args = parser.parse_args()
    
    print("🌐 启动Pixiv MCP HTTP服务器...")
    print(f"   主机: {args.host}")
    print(f"   端口: {args.port}")
    print(f"   工作进程: {args.workers}")
    print(f"   重载模式: {args.reload}")
    print(f"   日志级别: {args.log_level}")
    print()
    print("📡 服务器端点:")
    print(f"   主页: http://{args.host}:{args.port}/")
    print(f"   API文档: http://{args.host}:{args.port}/docs")
    print(f"   工具列表: http://{args.host}:{args.port}/mcp/tools")
    print(f"   健康检查: http://{args.host}:{args.port}/health")
    print()
    
    # 启动服务器
    uvicorn.run(
        "http_server:app",
        host=args.host,
        port=args.port,
        workers=args.workers if not args.reload else 1,
        reload=args.reload,
        log_level=args.log_level,
        access_log=True,
        app_dir="src"
    )


if __name__ == "__main__":
    main()