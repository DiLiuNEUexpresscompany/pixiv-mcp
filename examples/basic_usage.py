#!/usr/bin/env python3
"""
Pixiv MCP Server - 基础使用示例
=============================

这个文件展示了如何直接使用Pixiv MCP Server的各种功能。
注意：这些示例是直接调用函数，而在Claude Desktop中，
你只需要用自然语言描述你的需求即可。

运行前请确保已配置refresh token:
    python -m pixiv_mcp.token_manager auto
"""

import asyncio
import sys
from pathlib import Path

# 添加src到路径，以便导入模块
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tools import dispatch


async def example_search(keyword: str = "初音ミク"):
    """搜索插画示例"""
    print(f"🔍 搜索关键词: {keyword}")
    
    try:
        result = await dispatch("pixiv_search_illust", {
            "word": keyword,
            "limit": 5,
            "sort": "date_desc"
        })
        
        if result and "error" not in result:
            print(f"   找到 {len(result)} 个作品:")
            for i, illust in enumerate(result, 1):
                print(f"   {i}. {illust['title']} - {illust['user']['name']}")
                print(f"      浏览: {illust.get('total_view', 0)}, 收藏: {illust.get('total_bookmarks', 0)}")
        else:
            print(f"   搜索失败: {result}")
            
    except Exception as e:
        print(f"   搜索出错: {e}")
    
    print()


async def example_ranking():
    """排行榜示例"""
    print("📊 获取今日插画排行榜")
    
    try:
        result = await dispatch("pixiv_illust_ranking", {
            "mode": "day",
            "limit": 5
        })
        
        if result and "error" not in result:
            print(f"   今日排行榜前5名:")
            for illust in result:
                print(f"   {illust['rank']}. {illust['title']} - {illust['user']['name']}")
                print(f"      浏览: {illust['total_view']}, 收藏: {illust['total_bookmarks']}")
        else:
            print(f"   获取排行榜失败: {result}")
            
    except Exception as e:
        print(f"   获取排行榜出错: {e}")
    
    print()


async def example_illust_detail(illust_id: int = 59580629):
    """插画详情示例"""
    print(f"🎨 获取插画详情 (ID: {illust_id})")
    
    try:
        result = await dispatch("pixiv_illust_detail", {
            "illust_id": illust_id
        })
        
        if result and "error" not in result:
            print(f"   标题: {result['title']}")
            print(f"   作者: {result['user']['name']} (@{result['user']['account']})")
            print(f"   尺寸: {result['width']}x{result['height']}")
            print(f"   页数: {result['page_count']}")
            print(f"   浏览: {result['total_view']}, 收藏: {result['total_bookmarks']}")
            print(f"   标签: {', '.join([tag['name'] for tag in result['tags'][:5]])}")
        else:
            print(f"   获取详情失败: {result}")
            
    except Exception as e:
        print(f"   获取详情出错: {e}")
    
    print()


async def example_user_detail(user_id: int = 660788):
    """用户详情示例"""
    print(f"👤 获取用户详情 (ID: {user_id})")
    
    try:
        result = await dispatch("pixiv_user_detail", {
            "user_id": user_id
        })
        
        if result and "error" not in result:
            user = result['user']
            profile = result['profile']
            print(f"   用户名: {user['name']} (@{user['account']})")
            print(f"   地区: {profile.get('region', 'N/A')}")
            print(f"   作品数: 插画{profile.get('total_illusts', 0)}, 漫画{profile.get('total_manga', 0)}")
            print(f"   关注数: {profile.get('total_follow_users', 0)}")
        else:
            print(f"   获取用户详情失败: {result}")
            
    except Exception as e:
        print(f"   获取用户详情出错: {e}")
    
    print()


async def example_trending_tags():
    """热门标签示例"""
    print("🏷️  获取热门标签")
    
    try:
        result = await dispatch("pixiv_trending_tags", {
            "limit": 10
        })
        
        if result and "error" not in result:
            print(f"   当前热门标签:")
            for i, tag in enumerate(result[:5], 1):
                print(f"   {i}. {tag['name']}")
                if tag.get('translated_name'):
                    print(f"      翻译: {tag['translated_name']}")
        else:
            print(f"   获取热门标签失败: {result}")
            
    except Exception as e:
        print(f"   获取热门标签出错: {e}")
    
    print()


async def example_download(illust_id: int = 59580629):
    """下载示例"""
    print(f"📥 下载插画 (ID: {illust_id})")
    print("   注意: 下载可能需要一些时间...")
    
    try:
        # 创建下载目录
        download_dir = Path("downloads")
        download_dir.mkdir(exist_ok=True)
        
        result = await dispatch("pixiv_download", {
            "illust_id": illust_id,
            "save_dir": str(download_dir),
            "quality": "large"
        })
        
        if result and "error" not in result:
            print(f"   下载成功!")
            print(f"   标题: {result['title']}")
            print(f"   保存目录: {result['save_directory']}")
            print(f"   文件数量: {result['total_files']}")
            for file_info in result['files']:
                print(f"   文件: {file_info['filename']}")
        else:
            print(f"   下载失败: {result}")
            
    except Exception as e:
        print(f"   下载出错: {e}")
    
    print()


async def run_all_examples():
    """运行所有示例"""
    print("🎨 Pixiv MCP Server - 基础使用示例")
    print("=" * 50)
    print()
    
    print("这些示例展示了Pixiv MCP Server的各种功能。")
    print("在Claude Desktop中，你只需要用自然语言提问即可！")
    print()
    
    # 基础功能
    await example_search("初音ミク")
    await example_ranking()
    await example_trending_tags()
    
    # 详情功能
    await example_illust_detail()
    await example_user_detail()
    
    # 下载功能（可选，注释掉以避免实际下载）
    # await example_download()
    
    print("✅ 所有示例执行完成!")
    print()
    print("在Claude Desktop中的使用方法:")
    print("- '帮我搜索初音未来的插画'")
    print("- '获取今日插画排行榜前10名'")
    print("- '查看插画ID 12345的详细信息'")
    print("- '现在什么标签最热门？'")


async def interactive_mode():
    """交互式模式"""
    print("🎯 交互式模式")
    print("输入数字选择要测试的功能:")
    print("1. 搜索插画")
    print("2. 排行榜")
    print("3. 插画详情")
    print("4. 用户详情")
    print("5. 热门标签")
    print("6. 下载插画")
    print("7. 运行所有示例")
    print("0. 退出")
    print()
    
    while True:
        try:
            choice = input("请选择 (0-7): ").strip()
            
            if choice == "0":
                print("👋 再见!")
                break
            elif choice == "1":
                keyword = input("请输入搜索关键词 (默认: 初音ミク): ").strip() or "初音ミク"
                await example_search(keyword)
            elif choice == "2":
                await example_ranking()
            elif choice == "3":
                illust_id = input("请输入插画ID (默认: 59580629): ").strip()
                illust_id = int(illust_id) if illust_id.isdigit() else 59580629
                await example_illust_detail(illust_id)
            elif choice == "4":
                user_id = input("请输入用户ID (默认: 660788): ").strip()
                user_id = int(user_id) if user_id.isdigit() else 660788
                await example_user_detail(user_id)
            elif choice == "5":
                await example_trending_tags()
            elif choice == "6":
                illust_id = input("请输入要下载的插画ID (默认: 59580629): ").strip()
                illust_id = int(illust_id) if illust_id.isdigit() else 59580629
                confirm = input(f"确定要下载插画 {illust_id}? (y/n): ").lower().strip()
                if confirm in ['y', 'yes']:
                    await example_download(illust_id)
            elif choice == "7":
                await run_all_examples()
            else:
                print("❌ 无效选择，请重新输入")
                
        except KeyboardInterrupt:
            print("\n👋 再见!")
            break
        except Exception as e:
            print(f"❌ 执行出错: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Pixiv MCP Server 基础使用示例")
    parser.add_argument("--all", action="store_true", help="运行所有示例")
    parser.add_argument("--interactive", action="store_true", help="交互式模式")
    
    args = parser.parse_args()
    
    if args.all:
        asyncio.run(run_all_examples())
    elif args.interactive:
        asyncio.run(interactive_mode())
    else:
        # 默认交互式模式
        asyncio.run(interactive_mode())


if __name__ == "__main__":
    main()