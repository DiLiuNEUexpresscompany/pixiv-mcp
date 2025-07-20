"""
Pixiv MCP Server - Tools Implementation
实现所有Pixiv MCP工具
"""

import asyncio
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

from pixivpy3 import AppPixivAPI
from pydantic import BaseModel, Field
from mcp.types import Tool

from .auth import get_refresh_token


# 全局API实例
_api: Optional[AppPixivAPI] = None
_refresh_token: Optional[str] = None


def get_api() -> AppPixivAPI:
    """获取或创建API实例"""
    global _api, _refresh_token
    
    if _api is None:
        _refresh_token = get_refresh_token()
        _api = AppPixivAPI()
        _api.auth(refresh_token=_refresh_token)
    
    return _api


# ==================== Pydantic Models ====================

class SearchIllustParams(BaseModel):
    word: str = Field(description="搜索关键词，支持中文、英文、日文")
    search_target: str = Field(
        default="partial_match_for_tags",
        description="搜索类型: partial_match_for_tags(标签部分匹配), exact_match_for_tags(标签完全匹配), title_and_caption(标题说明)"
    )
    sort: str = Field(
        default="date_desc", 
        description="排序方式: date_desc(最新), date_asc(最旧), popular_desc(热门，需会员)"
    )
    duration: Optional[str] = Field(
        default=None,
        description="时间范围: within_last_day(一天内), within_last_week(一周内), within_last_month(一月内)"
    )
    limit: int = Field(default=10, description="返回结果数量限制", ge=1, le=30)


class IllustRankingParams(BaseModel):
    mode: str = Field(
        default="day",
        description="排行榜类型: day(日榜), week(周榜), month(月榜), day_male(男性向日榜), day_female(女性向日榜), week_original(原创周榜), week_rookie(新人周榜), day_manga(漫画日榜)"
    )
    date: Optional[str] = Field(
        default=None,
        description="指定日期，格式: YYYY-MM-DD，不指定则为最新"
    )
    limit: int = Field(default=10, description="返回结果数量限制", ge=1, le=50)


class IllustDetailParams(BaseModel):
    illust_id: int = Field(description="插画ID")


class UserDetailParams(BaseModel):
    user_id: int = Field(description="用户ID")


class UserIllustsParams(BaseModel):
    user_id: int = Field(description="用户ID")
    type: str = Field(default="illust", description="作品类型: illust(插画), manga(漫画)")
    limit: int = Field(default=10, description="返回结果数量限制", ge=1, le=30)


class DownloadParams(BaseModel):
    illust_id: int = Field(description="插画ID")
    save_dir: Optional[str] = Field(default=None, description="保存目录，不指定则使用临时目录")
    quality: str = Field(default="large", description="图片质量: large(大图), medium(中图), original(原图)")


class NovelTextParams(BaseModel):
    novel_id: int = Field(description="小说ID")


class TrendingTagsParams(BaseModel):
    limit: int = Field(default=10, description="返回标签数量限制", ge=1, le=50)


# ==================== Tool Functions ====================

async def search_illust(params: SearchIllustParams) -> List[Dict[str, Any]]:
    """搜索插画"""
    try:
        api = get_api()
        result = await asyncio.to_thread(
            api.search_illust,
            params.word,
            search_target=params.search_target,
            sort=params.sort,
            duration=params.duration,
        )
        
        if not hasattr(result, 'illusts') or not result.illusts:
            return []
        
        illusts = []
        for i, illust in enumerate(result.illusts[:params.limit]):
            illusts.append({
                "id": illust.id,
                "title": illust.title,
                "user": {
                    "id": illust.user.id,
                    "name": illust.user.name,
                    "account": illust.user.account,
                },
                "tags": [tag.name for tag in illust.tags],
                "create_date": illust.create_date,
                "page_count": illust.page_count,
                "width": illust.width,
                "height": illust.height,
                "total_view": illust.total_view,
                "total_bookmarks": illust.total_bookmarks,
                "urls": {
                    "square_medium": illust.image_urls.square_medium,
                    "medium": illust.image_urls.medium,
                    "large": illust.image_urls.large,
                },
                "is_r18": any(tag.name in ["R-18", "R-18G"] for tag in illust.tags),
            })
        
        return illusts
        
    except Exception as e:
        raise Exception(f"搜索插画失败: {str(e)}")


async def illust_ranking(params: IllustRankingParams) -> List[Dict[str, Any]]:
    """获取插画排行榜"""
    try:
        api = get_api()
        result = await asyncio.to_thread(
            api.illust_ranking,
            mode=params.mode,
            date=params.date,
        )
        
        if not hasattr(result, 'illusts') or not result.illusts:
            return []
        
        illusts = []
        for i, illust in enumerate(result.illusts[:params.limit]):
            illusts.append({
                "rank": i + 1,
                "id": illust.id,
                "title": illust.title,
                "user": {
                    "id": illust.user.id,
                    "name": illust.user.name,
                    "account": illust.user.account,
                },
                "tags": [tag.name for tag in illust.tags],
                "create_date": illust.create_date,
                "total_view": illust.total_view,
                "total_bookmarks": illust.total_bookmarks,
                "urls": {
                    "square_medium": illust.image_urls.square_medium,
                    "medium": illust.image_urls.medium,
                    "large": illust.image_urls.large,
                },
            })
        
        return illusts
        
    except Exception as e:
        raise Exception(f"获取排行榜失败: {str(e)}")


async def illust_detail(params: IllustDetailParams) -> Dict[str, Any]:
    """获取插画详情"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.illust_detail, params.illust_id)
        
        if not hasattr(result, 'illust') or not result.illust:
            raise Exception("插画不存在或已被删除")
        
        illust = result.illust
        
        # 处理多页作品
        meta_pages = []
        if hasattr(illust, 'meta_pages') and illust.meta_pages:
            for page in illust.meta_pages:
                meta_pages.append({
                    "image_urls": {
                        "square_medium": page.image_urls.square_medium,
                        "medium": page.image_urls.medium,
                        "large": page.image_urls.large,
                        "original": page.image_urls.original if hasattr(page.image_urls, 'original') else None,
                    }
                })
        
        return {
            "id": illust.id,
            "title": illust.title,
            "caption": illust.caption,
            "user": {
                "id": illust.user.id,
                "name": illust.user.name,
                "account": illust.user.account,
                "profile_image_urls": illust.user.profile_image_urls,
            },
            "tags": [{"name": tag.name, "translated_name": tag.translated_name} for tag in illust.tags],
            "tools": illust.tools,
            "create_date": illust.create_date,
            "page_count": illust.page_count,
            "width": illust.width,
            "height": illust.height,
            "sanity_level": illust.sanity_level,
            "x_restrict": illust.x_restrict,
            "total_view": illust.total_view,
            "total_bookmarks": illust.total_bookmarks,
            "is_bookmarked": illust.is_bookmarked,
            "urls": {
                "square_medium": illust.image_urls.square_medium,
                "medium": illust.image_urls.medium,
                "large": illust.image_urls.large,
            },
            "meta_pages": meta_pages,
        }
        
    except Exception as e:
        raise Exception(f"获取插画详情失败: {str(e)}")


async def user_detail(params: UserDetailParams) -> Dict[str, Any]:
    """获取用户详情"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.user_detail, params.user_id)
        
        if not hasattr(result, 'user') or not result.user:
            raise Exception("用户不存在")
        
        user = result.user
        profile = result.profile
        profile_publicity = result.profile_publicity
        workspace = result.workspace if hasattr(result, 'workspace') else {}
        
        return {
            "user": {
                "id": user.id,
                "name": user.name,
                "account": user.account,
                "profile_image_urls": user.profile_image_urls,
                "comment": user.comment if hasattr(user, 'comment') else "",
                "is_followed": user.is_followed if hasattr(user, 'is_followed') else False,
            },
            "profile": {
                "webpage": profile.webpage if hasattr(profile, 'webpage') else "",
                "gender": profile.gender if hasattr(profile, 'gender') else "",
                "birth": profile.birth if hasattr(profile, 'birth') else "",
                "birth_day": profile.birth_day if hasattr(profile, 'birth_day') else "",
                "birth_year": profile.birth_year if hasattr(profile, 'birth_year') else "",
                "region": profile.region if hasattr(profile, 'region') else "",
                "address_id": profile.address_id if hasattr(profile, 'address_id') else "",
                "country_code": profile.country_code if hasattr(profile, 'country_code') else "",
                "job": profile.job if hasattr(profile, 'job') else "",
                "job_id": profile.job_id if hasattr(profile, 'job_id') else "",
                "total_follow_users": profile.total_follow_users if hasattr(profile, 'total_follow_users') else 0,
                "total_mypixiv_users": profile.total_mypixiv_users if hasattr(profile, 'total_mypixiv_users') else 0,
                "total_illusts": profile.total_illusts if hasattr(profile, 'total_illusts') else 0,
                "total_manga": profile.total_manga if hasattr(profile, 'total_manga') else 0,
                "total_novels": profile.total_novels if hasattr(profile, 'total_novels') else 0,
                "total_illust_bookmarks_public": profile.total_illust_bookmarks_public if hasattr(profile, 'total_illust_bookmarks_public') else 0,
            },
            "workspace": workspace.__dict__ if hasattr(workspace, '__dict__') else {},
        }
        
    except Exception as e:
        raise Exception(f"获取用户详情失败: {str(e)}")


async def user_illusts(params: UserIllustsParams) -> List[Dict[str, Any]]:
    """获取用户作品列表"""
    try:
        api = get_api()
        result = await asyncio.to_thread(
            api.user_illusts,
            params.user_id,
            type=params.type,
        )
        
        if not hasattr(result, 'illusts') or not result.illusts:
            return []
        
        illusts = []
        for illust in result.illusts[:params.limit]:
            illusts.append({
                "id": illust.id,
                "title": illust.title,
                "caption": illust.caption,
                "tags": [tag.name for tag in illust.tags],
                "create_date": illust.create_date,
                "page_count": illust.page_count,
                "width": illust.width,
                "height": illust.height,
                "total_view": illust.total_view,
                "total_bookmarks": illust.total_bookmarks,
                "urls": {
                    "square_medium": illust.image_urls.square_medium,
                    "medium": illust.image_urls.medium,
                    "large": illust.image_urls.large,
                },
            })
        
        return illusts
        
    except Exception as e:
        raise Exception(f"获取用户作品列表失败: {str(e)}")


async def download_illust(params: DownloadParams) -> Dict[str, Any]:
    """下载插画"""
    try:
        api = get_api()
        
        # 获取插画详情
        detail_result = await asyncio.to_thread(api.illust_detail, params.illust_id)
        if not hasattr(detail_result, 'illust') or not detail_result.illust:
            raise Exception("插画不存在或已被删除")
        
        illust = detail_result.illust
        
        # 确定保存目录
        if params.save_dir:
            save_dir = Path(params.save_dir)
            save_dir.mkdir(parents=True, exist_ok=True)
        else:
            save_dir = Path(tempfile.mkdtemp(prefix="pixiv_download_"))
        
        # 确定下载URL
        urls_map = {
            "large": illust.image_urls.large,
            "medium": illust.image_urls.medium,
            "original": getattr(illust.image_urls, 'original', illust.image_urls.large),
        }
        
        download_url = urls_map.get(params.quality, illust.image_urls.large)
        
        downloaded_files = []
        
        # 处理多页作品
        if hasattr(illust, 'meta_pages') and illust.meta_pages:
            for i, page in enumerate(illust.meta_pages):
                page_url = getattr(page.image_urls, params.quality, page.image_urls.large)
                filename = f"{illust.id}_p{i}.{page_url.split('.')[-1]}"
                filepath = save_dir / filename
                
                await asyncio.to_thread(api.download, page_url, path=str(filepath))
                downloaded_files.append({
                    "page": i,
                    "filename": filename,
                    "filepath": str(filepath),
                    "url": page_url,
                })
        else:
            # 单页作品
            filename = f"{illust.id}.{download_url.split('.')[-1]}"
            filepath = save_dir / filename
            
            await asyncio.to_thread(api.download, download_url, path=str(filepath))
            downloaded_files.append({
                "page": 0,
                "filename": filename,
                "filepath": str(filepath),
                "url": download_url,
            })
        
        return {
            "illust_id": params.illust_id,
            "title": illust.title,
            "save_directory": str(save_dir),
            "quality": params.quality,
            "files": downloaded_files,
            "total_files": len(downloaded_files),
        }
        
    except Exception as e:
        raise Exception(f"下载插画失败: {str(e)}")


async def novel_text(params: NovelTextParams) -> Dict[str, Any]:
    """获取小说正文"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.webview_novel, params.novel_id)
        
        if not hasattr(result, 'novel_text') or not result.novel_text:
            raise Exception("小说不存在或无法获取正文")
        
        # 获取小说详情
        detail_result = await asyncio.to_thread(api.novel_detail, params.novel_id)
        novel = detail_result.novel if hasattr(detail_result, 'novel') else None
        
        response = {
            "novel_id": params.novel_id,
            "text": result.novel_text,
            "text_length": len(result.novel_text),
        }
        
        if novel:
            response.update({
                "title": novel.title,
                "caption": novel.caption,
                "user": {
                    "id": novel.user.id,
                    "name": novel.user.name,
                    "account": novel.user.account,
                },
                "tags": [tag.name for tag in novel.tags],
                "create_date": novel.create_date,
                "page_count": novel.page_count,
                "text_length": novel.text_length,
                "total_view": novel.total_view,
                "total_bookmarks": novel.total_bookmarks,
                "x_restrict": novel.x_restrict,
                "is_original": novel.is_original if hasattr(novel, 'is_original') else False,
            })
        
        return response
        
    except Exception as e:
        raise Exception(f"获取小说正文失败: {str(e)}")


async def trending_tags(params: TrendingTagsParams) -> List[Dict[str, Any]]:
    """获取热门标签"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.trending_tags_illust)
        
        if not hasattr(result, 'trend_tags') or not result.trend_tags:
            return []
        
        tags = []
        for tag_info in result.trend_tags[:params.limit]:
            tag = tag_info.tag
            tags.append({
                "name": tag.name,
                "translated_name": tag.translated_name if hasattr(tag, 'translated_name') else "",
                "illust": {
                    "id": tag_info.illust.id,
                    "title": tag_info.illust.title,
                    "image_urls": tag_info.illust.image_urls,
                } if hasattr(tag_info, 'illust') and tag_info.illust else None,
            })
        
        return tags
        
    except Exception as e:
        raise Exception(f"获取热门标签失败: {str(e)}")


# ==================== Tools Registry ====================

TOOLS = [
    Tool(
        name="pixiv_search_illust",
        description="搜索Pixiv插画。支持按关键词、标签搜索，可指定排序方式和时间范围",
        inputSchema=SearchIllustParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_illust_ranking",
        description="获取Pixiv插画排行榜。支持日榜、周榜、月榜等多种排行榜类型",
        inputSchema=IllustRankingParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_illust_detail",
        description="获取指定插画的详细信息，包括标签、用户信息、统计数据等",
        inputSchema=IllustDetailParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_user_detail",
        description="获取指定用户的详细信息，包括个人资料、作品统计等",
        inputSchema=UserDetailParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_user_illusts",
        description="获取指定用户的作品列表，支持插画和漫画类型",
        inputSchema=UserIllustsParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_download",
        description="下载指定插画到本地，支持多种图片质量选择",
        inputSchema=DownloadParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_novel_text",
        description="获取指定小说的完整正文内容",
        inputSchema=NovelTextParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_trending_tags",
        description="获取当前热门标签列表",
        inputSchema=TrendingTagsParams.model_json_schema(),
    ),
]


# ==================== Dispatcher ====================

async def dispatch(name: str, arguments: dict) -> Any:
    """工具调用分发器"""
    try:
        if name == "pixiv_search_illust":
            return await search_illust(SearchIllustParams(**arguments))
        elif name == "pixiv_illust_ranking":
            return await illust_ranking(IllustRankingParams(**arguments))
        elif name == "pixiv_illust_detail":
            return await illust_detail(IllustDetailParams(**arguments))
        elif name == "pixiv_user_detail":
            return await user_detail(UserDetailParams(**arguments))
        elif name == "pixiv_user_illusts":
            return await user_illusts(UserIllustsParams(**arguments))
        elif name == "pixiv_download":
            return await download_illust(DownloadParams(**arguments))
        elif name == "pixiv_novel_text":
            return await novel_text(NovelTextParams(**arguments))
        elif name == "pixiv_trending_tags":
            return await trending_tags(TrendingTagsParams(**arguments))
        else:
            raise ValueError(f"未知工具: {name}")
    except Exception as e:
        return {"error": str(e), "tool": name, "arguments": arguments}