#!/usr/bin/env python3
"""
Pixiv MCP HTTP Server - Streamable HTTP Server Implementation
基于HTTP协议的Pixiv MCP服务器，支持流式响应
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, AsyncGenerator
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from mcp.types import Tool, CallToolRequest, CallToolResult, ListToolsRequest
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
logger = logging.getLogger("pixiv-mcp-http")


# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动和关闭生命周期管理"""
    try:
        # 启动时检查认证
        ensure_refresh_token()
        logger.info("✅ Pixiv认证配置检查通过")
        logger.info("🚀 Pixiv MCP HTTP服务器启动中...")
        yield
    except Exception as e:
        logger.error(f"❌ 服务器启动失败: {str(e)}")
        raise
    finally:
        logger.info("👋 Pixiv MCP HTTP服务器已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="Pixiv MCP HTTP Server",
    description="Pixiv API的Model Context Protocol HTTP服务器实现",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== MCP HTTP Endpoints ====================

@app.get("/")
async def root():
    """根路径 - 服务器信息"""
    return {
        "name": "pixiv-mcp-http",
        "version": "1.0.0",
        "description": "Pixiv MCP HTTP Server with Streaming Support",
        "protocol": "mcp",
        "transport": "http",
        "capabilities": {
            "tools": True,
            "streaming": True,
            "resources": False
        },
        "endpoints": {
            "mcp": "/mcp",
            "list_tools": "/mcp/tools",
            "call_tool": "/mcp/tools/{tool_name}",
            "call_tool_stream": "/mcp/tools/{tool_name}/stream",
            "health": "/health",
            "status": "/status"
        },
        "timestamp": datetime.now().isoformat()
    }


@app.post("/")
async def mcp_root_handler(request: Request):
    """处理根路径的MCP JSON-RPC请求"""
    try:
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id")
        
        logger.info(f"MCP根路径请求: {method}")
        
        if method == "initialize":
            # 处理初始化请求
            return {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {},
                        "prompts": {},
                        "logging": {}
                    },
                    "serverInfo": {
                        "name": "pixiv-mcp-http",
                        "version": "1.0.0"
                    }
                },
                "id": request_id
            }
        
        elif method == "tools/list":
            # 列出工具
            tools_data = []
            for tool in TOOLS:
                tools_data.append({
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                })
            
            return {
                "jsonrpc": "2.0",
                "result": {
                    "tools": tools_data
                },
                "id": request_id
            }
        
        elif method == "tools/call":
            # 调用工具
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if not tool_name:
                raise ValueError("缺少工具名称")
            
            # 验证工具是否存在
            tool_names = [tool.name for tool in TOOLS]
            if tool_name not in tool_names:
                raise ValueError(f"工具 '{tool_name}' 不存在")
            
            # 调用工具
            result = await dispatch(tool_name, arguments)
            
            return {
                "jsonrpc": "2.0",
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False, indent=2)
                        }
                    ]
                },
                "id": request_id
            }
        
        elif method == "notifications/initialized":
            # 处理初始化完成通知（单向通知，不需要响应）
            logger.info("客户端初始化完成通知")
            return Response(status_code=204)  # No Content
        
        else:
            raise ValueError(f"不支持的方法: {method}")
            
    except Exception as e:
        logger.error(f"MCP根路径请求处理失败: {str(e)}")
        
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": str(e)
            },
            "id": request_id if 'request_id' in locals() else None
        }


@app.post("/mcp")
async def mcp_handler(request: Request):
    """专门的MCP协议处理端点"""
    return await mcp_root_handler(request)


@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 简单的认证检查
        from auth import get_refresh_token
        token = get_refresh_token()
        return {
            "status": "healthy",
            "service": "pixiv-mcp-http",
            "timestamp": datetime.now().isoformat(),
            "auth": "configured" if token else "missing"
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "pixiv-mcp-http",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        )


@app.get("/status")
async def status():
    """详细状态信息"""
    try:
        from auth import token_status
        status_info = token_status()
        
        return {
            "service": "pixiv-mcp-http",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "tools_count": len(TOOLS),
            "auth_status": status_info,
            "available_tools": [tool.name for tool in TOOLS]
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "service": "pixiv-mcp-http",
                "timestamp": datetime.now().isoformat()
            }
        )


@app.get("/mcp/tools")
async def list_tools() -> Dict[str, Any]:
    """列出所有可用工具 - MCP标准接口"""
    logger.info(f"列出 {len(TOOLS)} 个Pixiv工具")
    
    tools_data = []
    for tool in TOOLS:
        tools_data.append({
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.inputSchema
        })
    
    return {
        "jsonrpc": "2.0",
        "result": {
            "tools": tools_data
        },
        "id": None
    }


@app.post("/mcp/tools/{tool_name}")
async def call_tool(tool_name: str, request: Request) -> Dict[str, Any]:
    """调用指定工具 - MCP标准接口"""
    try:
        body = await request.json()
        arguments = body.get("arguments", {})
        request_id = body.get("id")
        
        logger.info(f"调用工具: {tool_name}, 参数: {arguments}")
        
        # 验证工具是否存在
        tool_names = [tool.name for tool in TOOLS]
        if tool_name not in tool_names:
            raise HTTPException(
                status_code=404,
                detail=f"工具 '{tool_name}' 不存在。可用工具: {tool_names}"
            )
        
        # 调用工具
        result = await dispatch(tool_name, arguments)
        
        logger.info(f"工具 {tool_name} 执行成功")
        
        return {
            "jsonrpc": "2.0",
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, indent=2)
                    }
                ],
                "isError": False
            },
            "id": request_id
        }
        
    except Exception as e:
        logger.error(f"工具 {tool_name} 执行失败: {str(e)}")
        
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": str(e),
                "data": {
                    "tool": tool_name,
                    "arguments": arguments if 'arguments' in locals() else {}
                }
            },
            "id": request_id if 'request_id' in locals() else None
        }


async def stream_tool_result(tool_name: str, arguments: Dict[str, Any]) -> AsyncGenerator[str, None]:
    """流式工具调用结果生成器"""
    try:
        # 发送开始标记
        yield f"data: {json.dumps({'type': 'start', 'tool': tool_name, 'timestamp': datetime.now().isoformat()})}\n\n"
        
        # 对于某些工具，我们可以提供进度更新
        if tool_name in ["pixiv_search_illust", "pixiv_illust_ranking", "pixiv_user_illusts"]:
            yield f"data: {json.dumps({'type': 'progress', 'message': '正在连接Pixiv API...'})}\n\n"
            await asyncio.sleep(0.1)
            
            yield f"data: {json.dumps({'type': 'progress', 'message': '正在获取数据...'})}\n\n"
            await asyncio.sleep(0.1)
        
        # 执行工具调用
        result = await dispatch(tool_name, arguments)
        
        # 发送结果
        if isinstance(result, list) and len(result) > 5:
            # 对于大型结果，分批发送
            batch_size = 5
            for i in range(0, len(result), batch_size):
                batch = result[i:i + batch_size]
                yield f"data: {json.dumps({'type': 'partial', 'data': batch, 'batch': i // batch_size + 1})}\n\n"
                await asyncio.sleep(0.05)  # 小延迟模拟流式处理
        else:
            # 发送完整结果
            yield f"data: {json.dumps({'type': 'result', 'data': result})}\n\n"
        
        # 发送完成标记
        yield f"data: {json.dumps({'type': 'complete', 'tool': tool_name, 'timestamp': datetime.now().isoformat()})}\n\n"
        
    except Exception as e:
        # 发送错误信息
        yield f"data: {json.dumps({'type': 'error', 'error': str(e), 'tool': tool_name})}\n\n"


@app.post("/mcp/tools/{tool_name}/stream")
async def call_tool_stream(tool_name: str, request: Request):
    """流式调用指定工具"""
    try:
        body = await request.json()
        arguments = body.get("arguments", {})
        
        logger.info(f"流式调用工具: {tool_name}, 参数: {arguments}")
        
        # 验证工具是否存在
        tool_names = [tool.name for tool in TOOLS]
        if tool_name not in tool_names:
            raise HTTPException(
                status_code=404,
                detail=f"工具 '{tool_name}' 不存在。可用工具: {tool_names}"
            )
        
        # 返回流式响应
        return StreamingResponse(
            stream_tool_result(tool_name, arguments),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )
        
    except Exception as e:
        logger.error(f"流式工具 {tool_name} 执行失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 便捷REST API端点 ====================

@app.get("/api/tools")
async def api_list_tools():
    """REST API - 列出所有工具"""
    return {
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "schema": tool.inputSchema
            }
            for tool in TOOLS
        ],
        "count": len(TOOLS)
    }


@app.post("/api/search")
async def api_search_illust(word: str, limit: int = 10, sort: str = "date_desc"):
    """REST API - 搜索插画"""
    try:
        result = await dispatch("pixiv_search_illust", {
            "word": word,
            "limit": limit,
            "sort": sort
        })
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ranking")
async def api_ranking(mode: str = "day", limit: int = 10):
    """REST API - 获取排行榜"""
    try:
        result = await dispatch("pixiv_illust_ranking", {
            "mode": mode,
            "limit": limit
        })
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/illust/{illust_id}")
async def api_illust_detail(illust_id: int):
    """REST API - 获取插画详情"""
    try:
        result = await dispatch("pixiv_illust_detail", {
            "illust_id": illust_id
        })
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/user/{user_id}")
async def api_user_detail(user_id: int):
    """REST API - 获取用户详情"""
    try:
        result = await dispatch("pixiv_user_detail", {
            "user_id": user_id
        })
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/user/{user_id}/illusts")
async def api_user_illusts(user_id: int, limit: int = 10, type: str = "illust"):
    """REST API - 获取用户作品"""
    try:
        result = await dispatch("pixiv_user_illusts", {
            "user_id": user_id,
            "limit": limit,
            "type": type
        })
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== WebSocket支持 (可选) ====================

try:
    from fastapi import WebSocket, WebSocketDisconnect
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket端点 - 支持实时通信"""
        await websocket.accept()
        logger.info("WebSocket连接已建立")
        
        try:
            while True:
                # 接收消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "call_tool":
                    tool_name = message.get("tool")
                    arguments = message.get("arguments", {})
                    
                    try:
                        # 发送开始通知
                        await websocket.send_text(json.dumps({
                            "type": "start",
                            "tool": tool_name
                        }))
                        
                        # 执行工具
                        result = await dispatch(tool_name, arguments)
                        
                        # 发送结果
                        await websocket.send_text(json.dumps({
                            "type": "result",
                            "tool": tool_name,
                            "data": result
                        }))
                        
                    except Exception as e:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "tool": tool_name,
                            "error": str(e)
                        }))
                
                elif message.get("type") == "list_tools":
                    await websocket.send_text(json.dumps({
                        "type": "tools",
                        "tools": [{"name": tool.name, "description": tool.description} for tool in TOOLS]
                    }))
                
        except WebSocketDisconnect:
            logger.info("WebSocket连接已断开")
        except Exception as e:
            logger.error(f"WebSocket错误: {str(e)}")

except ImportError:
    logger.warning("WebSocket支持不可用，跳过WebSocket端点")


def create_app() -> FastAPI:
    """创建应用实例"""
    return app


def main():
    """主函数 - 启动HTTP服务器"""
    logger.info("🌐 启动Pixiv MCP HTTP服务器...")
    
    # 配置服务器
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8080,
        log_level="info",
        access_log=True,
        reload=False,
        workers=1
    )
    
    server = uvicorn.Server(config)
    
    try:
        # 在Windows上使用ProactorEventLoop
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        # 启动服务器
        server.run()
        
    except KeyboardInterrupt:
        logger.info("🛑 收到中断信号，关闭服务器...")
    except Exception as e:
        logger.error(f"❌ 服务器启动失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()