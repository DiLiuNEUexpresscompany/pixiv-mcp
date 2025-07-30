#!/usr/bin/env python3
"""
Pixiv MCP Server - Main Server Entry Point
Pixiv API的Model Context Protocol服务器实现
"""

import asyncio
import logging
import sys
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool

from auth import ensure_refresh_token
from tools import TOOLS, dispatch


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("pixiv-mcp")


# 创建MCP服务器实例
app = Server("pixiv-mcp")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """列出所有可用工具"""
    logger.info(f"列出 {len(TOOLS)} 个Pixiv工具")
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> Any:
    """调用指定工具"""
    logger.info(f"调用工具: {name}, 参数: {arguments}")
    
    try:
        result = await dispatch(name, arguments)
        logger.info(f"工具 {name} 执行成功")
        return result
    except Exception as e:
        logger.error(f"工具 {name} 执行失败: {str(e)}")
        return {
            "error": str(e),
            "tool": name,
            "arguments": arguments,
            "success": False
        }


@app.list_resources()
async def list_resources() -> List[Resource]:
    """列出可用资源（可选功能）"""
    # 这里可以添加一些静态资源，比如帮助文档等
    return []


async def main():
    """主函数 - 启动MCP服务器"""
    try:
        # 确保refresh token已配置
        ensure_refresh_token()
        logger.info("✅ Pixiv认证配置检查通过")
        
        # 启动stdio服务器
        logger.info("🚀 启动Pixiv MCP服务器...")
        
        async with stdio_server() as (read_stream, write_stream):
            logger.info("📡 MCP服务器已启动，等待客户端连接...")
            await app.run(read_stream, write_stream)
            
    except KeyboardInterrupt:
        logger.info("🛑 收到中断信号，关闭服务器...")
    except Exception as e:
        logger.error(f"❌ 服务器启动失败: {str(e)}")
        sys.exit(1)
    finally:
        logger.info("👋 Pixiv MCP服务器已关闭")


def cli_main():
    """命令行入口点"""
    try:
        # 在Windows上使用ProactorEventLoop以支持asyncio
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        asyncio.run(main())
    except Exception as e:
        logger.error(f"程序异常退出: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()