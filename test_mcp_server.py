#!/usr/bin/env python3
"""
MCP服务器测试版本
===============

测试MCP服务器的工具功能，不需要真实的MCP客户端连接
"""

import asyncio
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.tools import dispatch, TOOLS
from src.auth import ensure_refresh_token


async def test_tools():
    """测试所有MCP工具"""
    print("🧪 测试Pixiv MCP服务器工具")
    print("=" * 50)
    
    # 确保认证配置
    try:
        ensure_refresh_token()
        print("✅ 认证配置检查通过")
    except Exception as e:
        print(f"❌ 认证配置失败: {e}")
        return
    
    print(f"\n📋 可用工具列表 ({len(TOOLS)}个):")
    for i, tool in enumerate(TOOLS, 1):
        print(f"   {i}. {tool.name} - {tool.description}")
    
    print("\n🔍 开始功能测试...")
    print("-" * 40)
    
    # 测试1: 搜索插画
    print("\n1️⃣ 测试搜索插画")
    try:
        result = await dispatch("pixiv_search_illust", {
            "word": "猫",
            "limit": 3
        })
        
        if result and "error" not in result:
            print(f"   ✅ 搜索成功，找到 {len(result)} 个结果")
            for i, illust in enumerate(result):
                print(f"      {i+1}. 《{illust['title']}》- {illust['user']['name']}")
        else:
            print(f"   ❌ 搜索失败: {result}")
    except Exception as e:
        print(f"   ❌ 搜索异常: {e}")
    
    # 测试2: 排行榜
    print("\n2️⃣ 测试排行榜")
    try:
        result = await dispatch("pixiv_illust_ranking", {
            "mode": "day",
            "limit": 3
        })
        
        if result and "error" not in result:
            print(f"   ✅ 排行榜获取成功，前3名:")
            for illust in result:
                print(f"      {illust['rank']}. 《{illust['title']}》- {illust['user']['name']}")
        else:
            print(f"   ❌ 排行榜获取失败: {result}")
    except Exception as e:
        print(f"   ❌ 排行榜异常: {e}")
    
    # 测试3: 热门标签
    print("\n3️⃣ 测试热门标签")
    try:
        result = await dispatch("pixiv_trending_tags", {
            "limit": 5
        })
        
        if result and "error" not in result:
            print(f"   ✅ 获取到 {len(result)} 个热门标签:")
            for i, tag in enumerate(result):
                name = tag.get('name', 'N/A')
                translated = tag.get('translated_name', '')
                display = f"{name}" + (f" ({translated})" if translated else "")
                print(f"      {i+1}. {display}")
        else:
            print(f"   ❌ 热门标签获取失败: {result}")
    except Exception as e:
        print(f"   ❌ 热门标签异常: {e}")
    
    # 测试4: 插画详情（使用一个已知的ID）
    print("\n4️⃣ 测试插画详情")
    try:
        result = await dispatch("pixiv_illust_detail", {
            "illust_id": 59580629
        })
        
        if result and "error" not in result:
            print(f"   ✅ 插画详情获取成功:")
            print(f"      标题: {result['title']}")
            print(f"      作者: {result['user']['name']}")
            print(f"      尺寸: {result['width']}x{result['height']}")
            print(f"      浏览: {result['total_view']:,}")
        else:
            print(f"   ❌ 插画详情获取失败: {result}")
    except Exception as e:
        print(f"   ❌ 插画详情异常: {e}")
    
    # 测试5: 用户详情
    print("\n5️⃣ 测试用户详情")
    try:
        result = await dispatch("pixiv_user_detail", {
            "user_id": 660788
        })
        
        if result and "error" not in result:
            print(f"   ✅ 用户详情获取成功:")
            print(f"      用户名: {result['user']['name']}")
            print(f"      账号: @{result['user']['account']}")
            print(f"      作品数: {result['profile'].get('total_illusts', 0)}")
        else:
            print(f"   ❌ 用户详情获取失败: {result}")
    except Exception as e:
        print(f"   ❌ 用户详情异常: {e}")
    
    print("\n🎉 工具测试完成!")
    print("\n💡 这些功能在Claude Desktop中的使用示例:")
    print("   • '帮我搜索可爱的猫咪插画'")
    print("   • '获取今日Pixiv排行榜前10名'")
    print("   • '现在什么标签最热门？'")
    print("   • '查看插画ID 59580629的详细信息'")
    print("   • '显示用户660788的个人资料'")


async def interactive_test():
    """交互式测试"""
    print("\n🎯 交互式测试模式")
    print("你可以手动测试任何工具函数")
    print()
    
    while True:
        print("可用工具:")
        for i, tool in enumerate(TOOLS, 1):
            print(f"   {i}. {tool.name}")
        print(f"   0. 退出")
        
        try:
            choice = input("\n请选择要测试的工具 (0-{}): ".format(len(TOOLS))).strip()
            
            if choice == "0":
                break
            
            tool_index = int(choice) - 1
            if 0 <= tool_index < len(TOOLS):
                tool = TOOLS[tool_index]
                print(f"\n测试工具: {tool.name}")
                print(f"描述: {tool.description}")
                
                # 根据工具类型提供默认参数
                if tool.name == "pixiv_search_illust":
                    keyword = input("请输入搜索关键词 (默认: 初音ミク): ").strip() or "初音ミク"
                    args = {"word": keyword, "limit": 5}
                
                elif tool.name == "pixiv_illust_ranking":
                    mode = input("请输入排行榜类型 (默认: day): ").strip() or "day"
                    args = {"mode": mode, "limit": 5}
                
                elif tool.name == "pixiv_illust_detail":
                    illust_id = input("请输入插画ID (默认: 59580629): ").strip() or "59580629"
                    args = {"illust_id": int(illust_id)}
                
                elif tool.name == "pixiv_user_detail":
                    user_id = input("请输入用户ID (默认: 660788): ").strip() or "660788"
                    args = {"user_id": int(user_id)}
                
                elif tool.name == "pixiv_trending_tags":
                    limit = input("请输入标签数量 (默认: 10): ").strip() or "10"
                    args = {"limit": int(limit)}
                
                else:
                    args = {}
                
                print(f"调用参数: {args}")
                result = await dispatch(tool.name, args)
                
                print("结果:")
                if isinstance(result, list):
                    print(f"  返回列表，包含 {len(result)} 个项目")
                    if result:
                        print(f"  第一个项目: {result[0]}")
                elif isinstance(result, dict):
                    if "error" in result:
                        print(f"  ❌ 错误: {result['error']}")
                    else:
                        print(f"  📊 返回字典，包含 {len(result)} 个字段")
                        for key, value in list(result.items())[:3]:
                            print(f"    {key}: {value}")
                else:
                    print(f"  {result}")
            
            else:
                print("❌ 无效选择")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ 测试失败: {e}")
        
        print()


async def main():
    """主函数"""
    print("🎨 Pixiv MCP Server 工具测试")
    print("=" * 50)
    print()
    print("选择测试模式:")
    print("1. 自动测试所有工具")
    print("2. 交互式测试")
    print("3. 退出")
    
    choice = input("\n请选择 (1-3): ").strip()
    
    if choice == "1":
        await test_tools()
    elif choice == "2":
        await test_tools()  # 先运行自动测试
        await interactive_test()  # 然后进入交互模式
    elif choice == "3":
        print("👋 再见!")
        return
    else:
        print("❌ 无效选择")


if __name__ == "__main__":
    asyncio.run(main())