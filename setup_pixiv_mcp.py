#!/usr/bin/env python3
"""
Pixiv MCP Server 快速配置脚本
=========================

这个脚本帮助用户快速设置和配置Pixiv MCP服务器，包括：
1. 检查Python环境
2. 安装依赖
3. 配置refresh token
4. 生成Claude Desktop配置
5. 测试连接

使用方法:
    python setup_pixiv_mcp.py
"""

import json
import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
from typing import Optional


def print_header():
    """打印欢迎信息"""
    print("=" * 60)
    print("🎨 Pixiv MCP Server 快速配置工具")
    print("=" * 60)
    print()


def check_python_version():
    """检查Python版本"""
    print("🔍 检查Python版本...")
    
    if sys.version_info < (3, 10):
        print("❌ 错误: 需要Python 3.10或更高版本")
        print(f"   当前版本: {sys.version}")
        sys.exit(1)
    
    print(f"✅ Python版本检查通过: {sys.version.split()[0]}")
    print()


def check_package_manager():
    """检查包管理器"""
    print("📦 检查包管理器...")
    
    # 检查是否有uv
    if shutil.which("uv"):
        print("✅ 检测到uv包管理器")
        return "uv"
    
    # 检查是否有pip
    if shutil.which("pip"):
        print("✅ 检测到pip包管理器")
        return "pip"
    
    print("❌ 未找到合适的包管理器")
    sys.exit(1)


def install_dependencies(package_manager: str):
    """安装依赖包"""
    print("📦 安装依赖包...")
    
    dependencies = [
        "pixivpy3>=3.7.5",
        "mcp>=0.4.0", 
        "httpx>=0.24.0",
        "uvloop>=0.17.0",
        "pydantic>=2.0.0",
        "aiofiles>=23.0.0",
        "gppt>=1.0.0",  # 自动获取token工具
    ]
    
    try:
        if package_manager == "uv":
            # 使用uv安装
            print("   使用uv安装依赖...")
            subprocess.run([
                "uv", "add"
            ] + dependencies, check=True)
        else:
            # 使用pip安装
            print("   使用pip安装依赖...")
            for dep in dependencies:
                print(f"   安装 {dep}...")
                subprocess.run([
                    sys.executable, "-m", "pip", "install", dep
                ], check=True, capture_output=True)
        
        print("✅ 所有依赖安装完成")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        print("请手动运行安装命令")
        sys.exit(1)
    
    print()


def setup_refresh_token() -> str:
    """配置refresh token，支持自动获取"""
    print("🔐 配置Pixiv认证...")
    print()
    
    # 检查是否已有token
    token_file = Path.home() / ".pixiv" / "refresh_token"
    env_token = os.getenv("PIXIV_REFRESH_TOKEN")
    
    if env_token:
        print("✅ 检测到环境变量中的refresh token")
        return env_token
    
    if token_file.exists():
        existing_token = token_file.read_text().strip()
        if existing_token:
            print(f"✅ 检测到已存在的refresh token: {token_file}")
            use_existing = input("是否使用现有token? (y/n): ").lower().strip()
            if use_existing in ['y', 'yes', '']:
                return existing_token
    
    # 使用token管理工具
    print("选择token获取方式:")
    print("1. 🤖 自动获取 (推荐) - 使用gppt工具自动登录")
    print("2. 🖱️  交互式获取 - 打开浏览器手动登录")  
    print("3. ✋ 手动输入 - 直接输入已有token")
    print()
    
    choice = input("请选择 (1-3，默认为1): ").strip() or "1"
    
    if choice == "1":
        # 调用token管理工具的自动获取功能
        try:
            result = subprocess.run([
                sys.executable, "-m", "pixiv_mcp.token_manager", "auto"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Token自动获取成功")
                return get_saved_token()
            else:
                print("❌ 自动获取失败，请尝试其他方式")
        except Exception as e:
            print(f"❌ 调用token管理工具失败: {e}")
    
    elif choice == "2":
        # 调用交互式登录
        try:
            result = subprocess.run([
                sys.executable, "-m", "pixiv_mcp.token_manager", "login"
            ])
            
            if result.returncode == 0:
                print("✅ 交互式登录成功")
                return get_saved_token()
            else:
                print("❌ 交互式登录失败")
        except Exception as e:
            print(f"❌ 交互式登录失败: {e}")
    
    # 手动输入
    print("✋ 手动输入token模式")
    print()
    print("获取token的方法:")
    print("1. 使用gppt工具: pip install gppt && gppt login")
    print("2. 使用在线工具: https://github.com/eggplants/get-pixivpy-token")
    print("3. 手动获取: 登录Pixiv -> F12开发者工具 -> Network -> 找到包含refresh_token的请求")
    print()
    
    while True:
        token = input("请输入你的refresh token: ").strip()
        
        if len(token) < 20:
            print("❌ Token格式不正确，请重新输入")
            continue
        
        # 保存token
        token_file.parent.mkdir(exist_ok=True)
        token_file.write_text(token)
        token_file.chmod(0o600)
        
        print(f"✅ Token已保存到: {token_file}")
        break
    
    print()
    return token


def get_saved_token() -> str:
    """获取保存的token"""
    token_file = Path.home() / ".pixiv" / "refresh_token"
    if token_file.exists():
        return token_file.read_text().strip()
    
    env_token = os.getenv("PIXIV_REFRESH_TOKEN")
    if env_token:
        return env_token
    
    raise ValueError("未找到保存的token")


def get_claude_desktop_config_path() -> Optional[Path]:
    """获取Claude Desktop配置文件路径"""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        return Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    elif system == "Linux":
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    else:
        return None


def setup_claude_desktop_config(refresh_token: str):
    """配置Claude Desktop"""
    print("🔧 配置Claude Desktop...")
    
    config_path = get_claude_desktop_config_path()
    
    if not config_path:
        print("❌ 无法确定Claude Desktop配置文件路径")
        print("请手动配置claude_desktop_config.json")
        return
    
    # 读取现有配置
    config = {}
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"⚠️  读取现有配置失败: {e}")
    
    # 添加Pixiv MCP配置
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    config["mcpServers"]["pixiv"] = {
        "command": "python",
        "args": ["-m", "pixiv_mcp.server"],
        "env": {
            "PIXIV_REFRESH_TOKEN": refresh_token
        }
    }
    
    # 保存配置
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Claude Desktop配置已更新: {config_path}")
        
        # 也保存到本地config目录作为备份
        local_config_dir = Path("config")
        local_config_dir.mkdir(exist_ok=True)
        local_config_file = local_config_dir / "claude_desktop_config.json"
        
        with open(local_config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 配置备份已保存到: {local_config_file}")
        
    except Exception as e:
        print(f"❌ 配置保存失败: {e}")
        print("请手动配置Claude Desktop")
    
    print()


def test_connection(refresh_token: str):
    """测试连接"""
    print("🧪 测试Pixiv连接...")
    
    try:
        # 调用token管理工具的测试功能
        result = subprocess.run([
            sys.executable, "-m", "pixiv_mcp.token_manager", "test"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Pixiv API连接测试成功")
        else:
            print("⚠️  API连接可能有问题，请检查token是否有效")
            print(f"   错误信息: {result.stderr}")
            
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        print("   请检查:")
        print("   1. refresh token是否正确")
        print("   2. 网络连接是否正常")
        print("   3. 是否需要使用代理")
    
    print()


def create_example_files():
    """创建示例文件"""
    print("📁 创建示例文件...")
    
    # 创建examples目录
    examples_dir = Path("examples")
    examples_dir.mkdir(exist_ok=True)
    
    # 创建基础示例文件
    basic_example = examples_dir / "basic_usage.py"
    if not basic_example.exists():
        basic_example.write_text('''#!/usr/bin/env python3
"""
Pixiv MCP Server - 基础使用示例
"""

import asyncio
from pixiv_mcp.tools import dispatch


async def example_search():
    """搜索示例"""
    result = await dispatch("pixiv_search_illust", {
        "word": "初音ミク",
        "limit": 5
    })
    print(f"搜索结果: {len(result)} 个作品")
    return result


async def example_ranking():
    """排行榜示例"""
    result = await dispatch("pixiv_illust_ranking", {
        "mode": "day",
        "limit": 5
    })
    print(f"今日排行榜前5名:")
    for illust in result:
        print(f"  {illust['rank']}. {illust['title']}")
    return result


async def main():
    """主函数"""
    print("🎨 Pixiv MCP基础使用示例")
    await example_search()
    await example_ranking()


if __name__ == "__main__":
    asyncio.run(main())
''')
    
    print(f"✅ 示例文件已创建: {examples_dir}")
    print()


def print_usage_instructions():
    """打印使用说明"""
    print("🎉 配置完成！")
    print()
    print("使用方法:")
    print("1. 重启Claude Desktop应用")
    print("2. 在对话中直接询问Pixiv相关问题:")
    print("   • '帮我搜索初音未来的插画'")
    print("   • '获取今日插画排行榜'") 
    print("   • '下载ID为12345的插画'")
    print("   • '查看用户123的详细信息'")
    print()
    print("命令行工具:")
    print(f"   • python -m pixiv_mcp.token_manager status  # 查看token状态")
    print(f"   • python -m pixiv_mcp.token_manager test    # 测试连接")
    print(f"   • python -m pixiv_mcp.server                # 启动MCP服务器")
    print()
    print("故障排除:")
    config_path = get_claude_desktop_config_path()
    if config_path:
        print(f"   • 配置文件: {config_path}")
    print("   • 检查Claude Desktop是否已重启")
    print("   • 确认refresh token是否有效")
    print("   • 运行: python -m pixiv_mcp.token_manager status")


def main():
    """主函数"""
    print_header()
    
    try:
        # 1. 检查Python版本
        check_python_version()
        
        # 2. 检查包管理器
        package_manager = check_package_manager()
        
        # 3. 安装依赖
        install_dependencies(package_manager)
        
        # 4. 配置refresh token
        refresh_token = setup_refresh_token()
        
        # 5. 配置Claude Desktop
        setup_claude_desktop_config(refresh_token)
        
        # 6. 测试连接
        test_connection(refresh_token)
        
        # 7. 创建示例文件
        create_example_files()
        
        # 8. 打印使用说明
        print_usage_instructions()
        
    except KeyboardInterrupt:
        print("\n❌ 配置被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 配置过程中出现错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()