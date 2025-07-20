#!/usr/bin/env python3
"""
Pixiv Token Manager - Pixiv Token管理工具
==========================================

这个工具提供完整的Pixiv token管理功能，包括：
1. 自动获取token
2. 交互式登录  
3. Token验证和刷新
4. 凭据管理

使用方法:
    python -m pixiv_mcp.token_manager [command]
"""

import argparse
import asyncio
import sys
import getpass
import json
from pathlib import Path

# 导入认证模块
from .auth import (
    auto_setup_token,
    get_token_with_gppt,
    get_token_with_playwright,
    refresh_existing_token,
    token_status,
    clear_saved_credentials,
    get_refresh_token,
    setup_token_file,
    is_gppt_available,
    install_gppt,
    is_playwright_available,
    install_playwright
)


def print_header():
    """打印工具头部信息"""
    print("=" * 60)
    print("🎨 Pixiv Token Manager - Pixiv Token管理工具")
    print("=" * 60)
    print()


def cmd_auto(args):
    """自动获取token"""
    print("🤖 自动获取Pixiv token...")
    
    # 检查可用的工具
    playwright_available = is_playwright_available()
    gppt_available = is_gppt_available()
    
    if not playwright_available and not gppt_available:
        print("❌ 未安装任何token获取工具")
        print("推荐安装playwright (更稳定): pip install playwright && playwright install")
        install_choice = input("是否自动安装playwright? (y/n): ").lower().strip()
        if install_choice in ['y', 'yes']:
            if not install_playwright():
                return False
        else:
            print("请手动安装: pip install playwright && playwright install")
            return False
    
    token = auto_setup_token()
    if token:
        print("✅ Token自动获取成功")
        return True
    else:
        print("❌ Token自动获取失败")
        return False


def cmd_playwright(args):
    """使用Playwright获取token"""
    print("🎭 使用Playwright获取Pixiv token...")
    
    if not is_playwright_available():
        print("❌ 需要安装playwright: pip install playwright && playwright install")
        install_choice = input("是否自动安装? (y/n): ").lower().strip()
        if install_choice in ['y', 'yes']:
            if not install_playwright():
                return False
        else:
            return False
    
    username = args.username or input("请输入Pixiv用户名/邮箱: ").strip()
    password = args.password or getpass.getpass("请输入Pixiv密码: ").strip()
    
    if not username or not password:
        print("❌ 用户名或密码不能为空")
        return False
    
    headless = not args.interactive if hasattr(args, 'interactive') else True
    token = get_token_with_playwright(username, password, headless)
    
    if token:
        setup_token_file(token)
        print("✅ Playwright获取token成功")
        return True
    else:
        print("❌ Playwright获取token失败")
        return False


def cmd_login(args):
    """交互式登录"""
    print("🖱️  交互式登录Pixiv...")
    
    if not is_gppt_available():
        print("❌ 需要安装gppt工具: pip install gppt")
        return False
    
    try:
        from gppt import GetPixivToken
        
        print("浏览器将打开，请在页面中登录Pixiv...")
        g = GetPixivToken(headless=False)
        result = g.login()
        
        if result and "refresh_token" in result:
            token = result["refresh_token"]
            setup_token_file(token)
            print("✅ 交互式登录成功")
            return True
        else:
            print("❌ 交互式登录失败")
            return False
            
    except Exception as e:
        print(f"❌ 登录过程中出现错误: {e}")
        return False


def cmd_headless_login(args):
    """无头浏览器登录"""
    print("🤖 无头浏览器登录...")
    
    if not is_gppt_available():
        print("❌ 需要安装gppt工具: pip install gppt")
        return False
    
    username = args.username or input("请输入Pixiv用户名/邮箱: ").strip()
    password = args.password or getpass.getpass("请输入Pixiv密码: ").strip()
    
    if not username or not password:
        print("❌ 用户名或密码不能为空")
        return False
    
    token = get_token_with_gppt(username, password, headless=True)
    if token:
        setup_token_file(token)
        print("✅ 无头浏览器登录成功")
        return True
    else:
        print("❌ 无头浏览器登录失败")
        return False


def cmd_refresh(args):
    """刷新token"""
    print("🔄 刷新Pixiv token...")
    
    try:
        current_token = get_refresh_token()
        new_token = refresh_existing_token(current_token)
        
        if new_token:
            setup_token_file(new_token)
            print("✅ Token刷新成功")
            return True
        else:
            print("❌ Token刷新失败")
            return False
            
    except Exception as e:
        print(f"❌ 刷新过程中出现错误: {e}")
        return False


def cmd_status(args):
    """查看token状态"""
    print("📊 Token状态检查...")
    print()
    
    status = token_status()
    
    print("🔍 检查结果:")
    print(f"  环境变量token: {'✅' if status['env_token_exists'] else '❌'}")
    print(f"  文件token: {'✅' if status['file_token_exists'] else '❌'}")
    print(f"  保存的凭据: {'✅' if status['credentials_saved'] else '❌'}")
    print(f"  playwright工具: {'✅' if status['playwright_available'] else '❌'}")
    print(f"  gppt工具: {'✅' if status['gppt_available'] else '❌'}")
    
    if status.get('file_token_valid') is not None:
        print(f"  token格式: {'✅' if status['file_token_valid'] else '❌'}")
        print(f"  token长度: {status.get('file_token_length', 0)}")
    
    print()
    
    # 尝试验证token
    if status['env_token_exists'] or status['file_token_exists']:
        verify_choice = input("是否验证token有效性? (y/n): ").lower().strip()
        if verify_choice in ['y', 'yes']:
            return cmd_test(args)
    
    return True


def cmd_test(args):
    """测试token有效性"""
    print("🧪 测试token有效性...")
    
    try:
        from pixivpy3 import AppPixivAPI
        
        token = get_refresh_token()
        api = AppPixivAPI()
        api.auth(refresh_token=token)
        
        # 尝试获取热门标签来测试
        result = api.trending_tags_illust()
        
        if hasattr(result, 'trend_tags') and result.trend_tags:
            print("✅ Token有效，API连接正常")
            print(f"   获取到 {len(result.trend_tags)} 个热门标签")
            
            # 显示一些热门标签（修复数据格式问题）
            print("   热门标签示例:")
            try:
                for i, tag_info in enumerate(result.trend_tags[:3]):
                    if hasattr(tag_info, 'tag'):
                        # 新版API格式
                        tag_name = tag_info.tag.name if hasattr(tag_info.tag, 'name') else str(tag_info.tag)
                    else:
                        # 旧版API格式或直接是标签名
                        tag_name = str(tag_info)
                    print(f"     {i+1}. {tag_name}")
            except Exception as e:
                print(f"     (标签显示格式解析中...)")
            
            return True
        else:
            print("⚠️  API返回异常，token可能有问题")
            return False
            
    except Exception as e:
        print(f"❌ Token验证失败: {e}")
        print("   可能的原因:")
        print("   1. Token已过期")
        print("   2. 网络连接问题")
        print("   3. Pixiv服务不可用")
        return False


def cmd_clear(args):
    """清除所有保存的数据"""
    print("🗑️  清除保存的数据...")
    
    confirm = input("⚠️  这将删除所有保存的token和凭据，确定继续? (yes/no): ").lower().strip()
    
    if confirm == "yes":
        clear_saved_credentials()
        print("✅ 所有数据已清除")
        return True
    else:
        print("❌ 操作已取消")
        return False


def cmd_setup_claude(args):
    """生成Claude Desktop配置"""
    print("🔧 生成Claude Desktop配置...")
    
    try:
        token = get_refresh_token()
        
        config = {
            "mcpServers": {
                "pixiv": {
                    "command": "python",
                    "args": ["-m", "pixiv_mcp.server"],
                    "env": {
                        "PIXIV_REFRESH_TOKEN": token
                    }
                }
            }
        }
        
        config_json = json.dumps(config, indent=2, ensure_ascii=False)
        
        print("📋 Claude Desktop配置:")
        print("-" * 40)
        print(config_json)
        print("-" * 40)
        
        # 保存到config目录
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "claude_desktop_config.json"
        config_file.write_text(config_json, encoding='utf-8')
        print(f"✅ 配置已保存到: {config_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ 生成配置失败: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Pixiv Token Manager - Pixiv Token管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python -m pixiv_mcp.token_manager auto           # 自动获取token
  python -m pixiv_mcp.token_manager playwright -u user -p pass  # 使用Playwright获取
  python -m pixiv_mcp.token_manager playwright -i  # Playwright交互模式
  python -m pixiv_mcp.token_manager login          # 交互式登录
  python -m pixiv_mcp.token_manager headless -u user -p pass  # 无头浏览器登录
  python -m pixiv_mcp.token_manager refresh        # 刷新token
  python -m pixiv_mcp.token_manager status         # 查看状态
  python -m pixiv_mcp.token_manager test           # 测试token
  python -m pixiv_mcp.token_manager clear          # 清除数据
  python -m pixiv_mcp.token_manager claude         # 生成Claude配置
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # auto命令
    subparsers.add_parser('auto', help='自动获取token')
    
    # playwright命令
    playwright_parser = subparsers.add_parser('playwright', help='使用Playwright获取token')
    playwright_parser.add_argument('-u', '--username', help='Pixiv用户名/邮箱')
    playwright_parser.add_argument('-p', '--password', help='Pixiv密码')
    playwright_parser.add_argument('-i', '--interactive', action='store_true', help='显示浏览器界面')
    
    # login命令
    subparsers.add_parser('login', help='交互式登录')
    
    # headless命令
    headless_parser = subparsers.add_parser('headless', help='无头浏览器登录')
    headless_parser.add_argument('-u', '--username', help='Pixiv用户名/邮箱')
    headless_parser.add_argument('-p', '--password', help='Pixiv密码')
    
    # 其他命令
    subparsers.add_parser('refresh', help='刷新现有token')
    subparsers.add_parser('status', help='查看token状态')
    subparsers.add_parser('test', help='测试token有效性')
    subparsers.add_parser('clear', help='清除所有保存的数据')
    subparsers.add_parser('claude', help='生成Claude Desktop配置')
    
    args = parser.parse_args()
    
    print_header()
    
    # 根据命令执行相应功能
    commands = {
        'auto': cmd_auto,
        'playwright': cmd_playwright,
        'login': cmd_login,
        'headless': cmd_headless_login,
        'refresh': cmd_refresh,
        'status': cmd_status,
        'test': cmd_test,
        'clear': cmd_clear,
        'claude': cmd_setup_claude,
    }
    
    if args.command in commands:
        try:
            success = commands[args.command](args)
            sys.exit(0 if success else 1)
        except KeyboardInterrupt:
            print("\n❌ 操作被用户中断")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ 执行过程中出现错误: {e}")
            sys.exit(1)
    else:
        print("❌ 未指定命令，使用 -h 查看帮助")
        parser.print_help()
        
        # 交互式模式
        print("\n🎯 交互式模式:")
        print("1. 自动获取token")
        print("2. Playwright获取token")
        print("3. 交互式登录")
        print("4. 查看token状态")
        print("5. 测试token")
        print("6. 退出")
        
        while True:
            choice = input("\n请选择操作 (1-6): ").strip()
            
            if choice == '1':
                cmd_auto(args)
                break
            elif choice == '2':
                cmd_playwright(args)
                break
            elif choice == '3':
                cmd_login(args)
                break
            elif choice == '4':
                cmd_status(args)
            elif choice == '5':
                cmd_test(args)
            elif choice == '6':
                print("👋 再见!")
                break
            else:
                print("❌ 无效选择，请重新输入")


if __name__ == "__main__":
    main()