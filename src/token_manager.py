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
from auth import (
    get_token,
    refresh_existing_token,
    token_status,
    clear_saved_credentials,
    get_refresh_token,
    setup_token_file,
    is_playwright_available,
    install_playwright
)


def print_header():
    """打印工具头部信息"""
    print("=" * 60)
    print("🎨 Pixiv Token Manager - Pixiv Token管理工具")
    print("=" * 60)
    print()





def cmd_login(args):
    """交互式登录"""
    print("🖱️  交互式登录Pixiv...")
    print("📋 由于需要处理二步验证和图片验证码，浏览器将保持打开状态")
    print("⏰ 超时时间：5分钟，请完成所有验证步骤")
    print()
    
    username = args.username if hasattr(args, 'username') and args.username else None
    password = args.password if hasattr(args, 'password') and args.password else None
    
    if not username or not password:
        print("💡 提示：如果未提供用户名密码，请在浏览器中手动输入")
    
    # 使用交互式模式（显示浏览器）
    token = get_token(username, password, headless=False)
    if token:
        setup_token_file(token)
        print("✅ 交互式登录成功")
        return True
    else:
        print("❌ 交互式登录失败")
        print("💡 提示：请确保完成了所有验证步骤，包括图片验证码和二步验证")
        return False


def cmd_headless(args):
    """无头浏览器登录"""
    print("🤖 无头浏览器登录...")
    
    username = args.username if hasattr(args, 'username') and args.username else None
    password = args.password if hasattr(args, 'password') and args.password else None
    
    # 使用无头模式
    token = get_token(username, password, headless=True)
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
    print(f"  系统环境变量token: {'✅' if status['env_token_exists'] else '❌'}")
    print(f"  .env文件token: {'✅' if status['env_file_token_exists'] else '❌'}")
    print(f"  旧版文件token: {'✅' if status['old_file_token_exists'] else '❌'}")
    print(f"  playwright工具: {'✅' if status['playwright_available'] else '❌'}")
    
    if status.get('env_file_token_valid') is not None:
        print(f"  .env token格式: {'✅' if status['env_file_token_valid'] else '❌'}")
        print(f"  .env token长度: {status.get('env_file_token_length', 0)}")
    
    if status.get('old_file_token_exists') and status.get('old_file_token_valid'):
        print("  💡 检测到旧版token文件，下次使用时将自动迁移到.env文件")
    
    print()
    # 使用与auth.py相同的PROJECT_ROOT计算方式
    project_root = Path(__file__).parent.parent
    print(f"📁 .env文件位置: {project_root / '.env'}")
    
    # 尝试验证token
    has_token = status['env_token_exists'] or status['env_file_token_exists'] or status['old_file_token_exists']
    if has_token:
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
  python -m pixiv_mcp.token_manager login          # 交互式登录 (推荐)
  python -m pixiv_mcp.token_manager login -u user -p pass  # 指定账号交互式登录
  python -m pixiv_mcp.token_manager headless -u user -p pass  # 无头浏览器登录
  python -m pixiv_mcp.token_manager refresh        # 刷新token
  python -m pixiv_mcp.token_manager status         # 查看状态
  python -m pixiv_mcp.token_manager test           # 测试token
  python -m pixiv_mcp.token_manager clear          # 清除数据
  python -m pixiv_mcp.token_manager claude         # 生成Claude配置

注意: 由于Pixiv需要二步验证和图片验证码，必须使用交互式登录手动完成验证。
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # login命令 (交互式) - 主要使用方式
    login_parser = subparsers.add_parser('login', help='交互式登录 (推荐)')
    login_parser.add_argument('-u', '--username', help='Pixiv用户名/邮箱')
    login_parser.add_argument('-p', '--password', help='Pixiv密码')
    
    # headless命令 (无头浏览器)
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
        'login': cmd_login,
        'headless': cmd_headless,
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
        print("1. 交互式登录 (推荐)")
        print("2. 查看token状态")
        print("3. 测试token")
        print("4. 退出")
        
        while True:
            choice = input("\n请选择操作 (1-4): ").strip()
            
            if choice == '1':
                cmd_login(args)
                break
            elif choice == '2':
                cmd_status(args)
            elif choice == '3':
                cmd_test(args)
            elif choice == '4':
                print("👋 再见!")
                break
            else:
                print("❌ 无效选择，请重新输入")


if __name__ == "__main__":
    main()