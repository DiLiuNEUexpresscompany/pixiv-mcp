"""
Pixiv MCP Server - Tools Implementation
实现所有Pixiv MCP工具
"""

import asyncio
import os
import tempfile
import random
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

from pixivpy3 import AppPixivAPI, ByPassSniApi
from pydantic import BaseModel, Field
from mcp.types import Tool

from auth import get_refresh_token


# 全局API实例
_api: Optional[AppPixivAPI] = None
_bypass_api: Optional[AppPixivAPI] = None
_refresh_token: Optional[str] = None


def get_api() -> AppPixivAPI:
    """获取或创建标准API实例"""
    global _api, _refresh_token
    
    if _api is None:
        _refresh_token = get_refresh_token()
        _api = AppPixivAPI()
        _api.auth(refresh_token=_refresh_token)
    
    return _api


def get_bypass_api() -> AppPixivAPI:
    """获取或创建ByPassSniApi实例，用于绕过GFW和Cloudflare"""
    global _bypass_api, _refresh_token
    
    if _bypass_api is None:
        _refresh_token = get_refresh_token()
        _bypass_api = ByPassSniApi()
        
        # 尝试获取真实IP，如果失败则使用默认hosts
        try:
            hosts_result = _bypass_api.require_appapi_hosts()
            if hosts_result:
                print(f"✓ 成功解析真实IP: {hosts_result}")
            else:
                print("⚠️ DNS解析失败，使用默认hosts")
        except Exception as e:
            print(f"⚠️ DNS解析出错: {e}，使用默认hosts")
        
        _bypass_api.set_accept_language("zh-CN,zh;q=0.9,en;q=0.8")
        _bypass_api.auth(refresh_token=_refresh_token)
    
    return _bypass_api


def get_api_with_fallback() -> AppPixivAPI:
    """获取API实例，优先使用ByPassSniApi，失败时回退到标准API"""
    try:
        # 首先尝试ByPassSniApi
        bypass_api = get_bypass_api()
        return bypass_api
    except Exception as e:
        print(f"⚠️ ByPassSniApi初始化失败: {e}，回退到标准API")
        return get_api()



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
    start_date: Optional[str] = Field(
        default=None,
        description="开始日期，格式: YYYY-MM-DD，用于指定搜索的开始时间"
    )
    end_date: Optional[str] = Field(
        default=None,
        description="结束日期，格式: YYYY-MM-DD，用于指定搜索的结束时间"
    )
    limit: int = Field(default=10, description="返回结果数量限制", ge=1, le=50)


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


class UserBookmarksParams(BaseModel):
    user_id: int = Field(description="用户ID")
    restrict: str = Field(default="public", description="限制类型: public(公开), private(私人)")
    limit: int = Field(default=10, description="返回结果数量限制", ge=1, le=30)


class UserRelatedParams(BaseModel):
    seed_user_id: int = Field(description="种子用户ID")
    limit: int = Field(default=10, description="返回结果数量限制", ge=1, le=30)


class IllustFollowParams(BaseModel):
    restrict: str = Field(default="public", description="限制类型: public(公开), private(私人)")
    limit: int = Field(default=10, description="返回结果数量限制", ge=1, le=30)


class IllustCommentsParams(BaseModel):
    illust_id: int = Field(description="插画ID")
    include_total_comments: bool = Field(default=True, description="是否包含评论总数")


class IllustRelatedParams(BaseModel):
    illust_id: int = Field(description="插画ID")
    limit: int = Field(default=10, description="返回结果数量限制", ge=1, le=30)


class IllustRecommendedParams(BaseModel):
    content_type: str = Field(default="illust", description="内容类型: illust(插画), manga(漫画)")
    limit: int = Field(default=10, description="返回结果数量限制", ge=1, le=30)


class NovelRecommendedParams(BaseModel):
    limit: int = Field(default=10, description="返回结果数量限制", ge=1, le=30)


class SearchNovelParams(BaseModel):
    word: str = Field(description="搜索关键词")
    search_target: str = Field(
        default="partial_match_for_tags",
        description="搜索类型: partial_match_for_tags(标签部分匹配), exact_match_for_tags(标签完全匹配), text(正文), keyword(关键词)"
    )
    sort: str = Field(default="date_desc", description="排序方式: date_desc(最新), date_asc(最旧)")
    start_date: Optional[str] = Field(default=None, description="开始日期，格式: YYYY-MM-DD")
    end_date: Optional[str] = Field(default=None, description="结束日期，格式: YYYY-MM-DD")
    limit: int = Field(default=10, description="返回结果数量限制", ge=1, le=30)


class SearchUserParams(BaseModel):
    word: str = Field(description="搜索关键词")
    sort: str = Field(default="date_desc", description="排序方式: date_desc(最新), date_asc(最旧)")
    duration: Optional[str] = Field(default=None, description="时间范围")
    limit: int = Field(default=10, description="返回结果数量限制", ge=1, le=30)


class GetCurrentTimeParams(BaseModel):
    """获取当前时间参数（无需参数）"""
    pass


class IllustBookmarkParams(BaseModel):
    illust_id: int = Field(description="插画ID")
    restrict: str = Field(default="public", description="限制类型: public(公开), private(私人)")
    tags: Optional[List[str]] = Field(default=None, description="收藏标签列表")


class UserFollowParams(BaseModel):
    user_id: int = Field(description="用户ID")
    restrict: str = Field(default="public", description="限制类型: public(公开), private(私人)")


class UserFollowingParams(BaseModel):
    user_id: int = Field(description="用户ID")
    restrict: str = Field(default="public", description="限制类型: public(公开), private(私人)")
    limit: int = Field(default=10, description="返回结果数量限制", ge=1, le=30)


class UserFollowerParams(BaseModel):
    user_id: int = Field(description="用户ID")
    limit: int = Field(default=10, description="返回结果数量限制", ge=1, le=30)


class UserMypixivParams(BaseModel):
    user_id: int = Field(description="用户ID")
    limit: int = Field(default=10, description="返回结果数量限制", ge=1, le=30)


class UserListParams(BaseModel):
    user_id: int = Field(description="用户ID")
    limit: int = Field(default=10, description="返回结果数量限制", ge=1, le=30)


class UgoiraMetadataParams(BaseModel):
    illust_id: int = Field(description="动图插画ID")


class UserNovelsParams(BaseModel):
    user_id: int = Field(description="用户ID")
    limit: int = Field(default=10, description="返回结果数量限制", ge=1, le=30)


class NovelSeriesParams(BaseModel):
    series_id: int = Field(description="小说系列ID")
    last_order: Optional[int] = Field(default=None, description="最后阅读顺序")


class NovelDetailParams(BaseModel):
    novel_id: int = Field(description="小说ID")


class NovelCommentsParams(BaseModel):
    novel_id: int = Field(description="小说ID")


class IllustNewParams(BaseModel):
    content_type: str = Field(default="illust", description="内容类型: illust(插画), manga(漫画)")
    max_illust_id: Optional[int] = Field(default=None, description="最大插画ID")
    limit: int = Field(default=10, description="返回结果数量限制", ge=1, le=30)


class NovelNewParams(BaseModel):
    max_novel_id: Optional[int] = Field(default=None, description="最大小说ID")
    limit: int = Field(default=10, description="返回结果数量限制", ge=1, le=30)


class ShowcaseArticleParams(BaseModel):
    showcase_id: int = Field(description="特辑ID")


class UserBookmarkTagsParams(BaseModel):
    restrict: str = Field(default="public", description="限制类型: public(公开), private(私人)")


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
            start_date=params.start_date,
            end_date=params.end_date,
        )
        
        if not hasattr(result, 'illusts') or not result.illusts:
            return []
        
        illusts = []
        for i, illust in enumerate(result.illusts[:params.limit]):
            illusts.append({
                "id": illust.id,
                "title": illust.title,
                "link": f"https://www.pixiv.net/artworks/{illust.id}",  # 添加链接字段
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
        # 添加随机延迟，避免被检测
        await asyncio.sleep(random.uniform(1, 3))
        
        # 尝试使用ByPassSniApi，如果失败则回退到标准API
        api = get_api_with_fallback()
        
        try:
            result = await asyncio.to_thread(
                api.webview_novel, 
                novel_id=params.novel_id, 
                raw=False, 
                req_auth=True
            )
        except Exception as bypass_error:
            print(f"⚠️ ByPassSniApi失败: {bypass_error}，尝试使用标准API")
            # 回退到标准API
            standard_api = get_api()
            result = await asyncio.to_thread(
                standard_api.webview_novel, 
                novel_id=params.novel_id, 
                raw=False, 
                req_auth=True
            )
        
        # 检查返回结果
        if not result:
            raise Exception("小说不存在或无法获取正文")
        
        # 根据SimpleNovelResult的字段结构处理
        text = getattr(result, 'text', '') or getattr(result, 'content', '') or getattr(result, 'novelText', '')
        if not text:
            raise Exception("小说正文为空")
        
        response = {
            "novel_id": params.novel_id,
            "text": text,
            "text_length": len(text),
            "title": getattr(result, 'title', ''),
            "description": getattr(result, 'description', ''),
            "author_name": getattr(result, 'author_name', '') or getattr(result, 'userName', ''),
            "create_date": getattr(result, 'create_date', ''),
            "bookmark_count": getattr(result, 'bookmark_count', 0),
            "comment_count": getattr(result, 'comment_count', 0),
            "total_view": getattr(result, 'total_view', 0) or getattr(result, 'viewCount', 0),
        }
        
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


async def get_current_time(params: GetCurrentTimeParams) -> Dict[str, Any]:
    """获取当前时间信息"""
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc)
    local_now = datetime.now()
    
    # 计算常用的时间范围
    two_years_ago = now.replace(year=now.year - 2, month=1, day=1)
    one_year_ago = now.replace(year=now.year - 1, month=1, day=1)
    current_year_start = now.replace(month=1, day=1)
    
    # 为了让Claude更容易使用，直接提供推荐的搜索参数
    recommended_two_years_search = {
        "start_date": two_years_ago.strftime("%Y-%m-%d"),
        "end_date": now.strftime("%Y-%m-%d")
    }
    
    return {
        "current_utc": now.isoformat(),
        "current_local": local_now.isoformat(),
        "current_date": now.strftime("%Y-%m-%d"),
        "current_year": now.year,
        "current_month": now.month,
        "current_day": now.day,
        "timezone_info": str(local_now.astimezone().tzinfo),
        
        # 明确的提示信息
        "IMPORTANT_MESSAGE": f"今天是 {now.strftime('%Y-%m-%d')}，请使用以下日期进行搜索",
        
        # 直接可用的搜索参数
        "recommended_search_params_for_two_years": recommended_two_years_search,
        
        "suggested_date_ranges": {
            "last_two_years": {
                "start_date": two_years_ago.strftime("%Y-%m-%d"),
                "end_date": now.strftime("%Y-%m-%d"),
                "description": "过去两年"
            },
            "last_year": {
                "start_date": one_year_ago.strftime("%Y-%m-%d"), 
                "end_date": now.strftime("%Y-%m-%d"),
                "description": "过去一年"
            },
            "current_year": {
                "start_date": current_year_start.strftime("%Y-%m-%d"),
                "end_date": now.strftime("%Y-%m-%d"),
                "description": "今年至今"
            }
        }
    }


async def user_bookmarks_illust(params: UserBookmarksParams) -> List[Dict[str, Any]]:
    """获取用户收藏插画列表"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.user_bookmarks_illust, params.user_id, restrict=params.restrict)
        
        if not hasattr(result, 'illusts') or not result.illusts:
            return []
        
        illusts = []
        for illust in result.illusts[:params.limit]:
            illusts.append({
                "id": illust.id,
                "title": illust.title,
                "link": f"https://www.pixiv.net/artworks/{illust.id}",
                "user": {
                    "id": illust.user.id,
                    "name": illust.user.name,
                    "account": illust.user.account,
                },
                "tags": [tag.name for tag in illust.tags],
                "create_date": illust.create_date,
                "page_count": illust.page_count,
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
        raise Exception(f"获取用户收藏插画失败: {str(e)}")


async def user_bookmarks_novel(params: UserBookmarksParams) -> List[Dict[str, Any]]:
    """获取用户收藏小说列表"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.user_bookmarks_novel, params.user_id, restrict=params.restrict)
        
        if not hasattr(result, 'novels') or not result.novels:
            return []
        
        novels = []
        for novel in result.novels[:params.limit]:
            novels.append({
                "id": novel.id,
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
                "is_original": novel.is_original if hasattr(novel, 'is_original') else False,
                "image_urls": novel.image_urls if hasattr(novel, 'image_urls') else {},
            })
        
        return novels
        
    except Exception as e:
        raise Exception(f"获取用户收藏小说失败: {str(e)}")


async def user_related(params: UserRelatedParams) -> List[Dict[str, Any]]:
    """获取相关用户"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.user_related, params.seed_user_id)
        
        if not hasattr(result, 'user_previews') or not result.user_previews:
            return []
        
        users = []
        for user_preview in result.user_previews[:params.limit]:
            user = user_preview.user
            users.append({
                "id": user.id,
                "name": user.name,
                "account": user.account,
                "profile_image_urls": user.profile_image_urls,
                "comment": user.comment if hasattr(user, 'comment') else "",
                "is_followed": user.is_followed if hasattr(user, 'is_followed') else False,
                "illusts": [
                    {
                        "id": illust.id,
                        "title": illust.title,
                        "image_urls": illust.image_urls,
                    } for illust in user_preview.illusts[:3]  # 只取前3个作品作为预览
                ] if hasattr(user_preview, 'illusts') and user_preview.illusts else [],
            })
        
        return users
        
    except Exception as e:
        raise Exception(f"获取相关用户失败: {str(e)}")


async def illust_follow(params: IllustFollowParams) -> List[Dict[str, Any]]:
    """获取关注用户的新作"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.illust_follow, restrict=params.restrict)
        
        if not hasattr(result, 'illusts') or not result.illusts:
            return []
        
        illusts = []
        for illust in result.illusts[:params.limit]:
            illusts.append({
                "id": illust.id,
                "title": illust.title,
                "link": f"https://www.pixiv.net/artworks/{illust.id}",
                "user": {
                    "id": illust.user.id,
                    "name": illust.user.name,
                    "account": illust.user.account,
                },
                "tags": [tag.name for tag in illust.tags],
                "create_date": illust.create_date,
                "page_count": illust.page_count,
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
        raise Exception(f"获取关注用户新作失败: {str(e)}")


async def illust_comments(params: IllustCommentsParams) -> List[Dict[str, Any]]:
    """获取插画评论"""
    try:
        api = get_api()
        result = await asyncio.to_thread(
            api.illust_comments, 
            params.illust_id, 
            include_total_comments=params.include_total_comments
        )
        
        if not hasattr(result, 'comments') or not result.comments:
            return []
        
        comments = []
        for comment in result.comments:
            comments.append({
                "id": comment.id,
                "comment": comment.comment,
                "date": comment.date,
                "user": {
                    "id": comment.user.id,
                    "name": comment.user.name,
                    "account": comment.user.account,
                    "profile_image_urls": comment.user.profile_image_urls,
                },
                "parent_comment": {
                    "id": comment.parent_comment.id,
                    "user": {
                        "id": comment.parent_comment.user.id,
                        "name": comment.parent_comment.user.name,
                    }
                } if hasattr(comment, 'parent_comment') and comment.parent_comment else None,
            })
        
        return comments
        
    except Exception as e:
        raise Exception(f"获取插画评论失败: {str(e)}")


async def illust_related(params: IllustRelatedParams) -> List[Dict[str, Any]]:
    """获取相关插画"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.illust_related, params.illust_id)
        
        if not hasattr(result, 'illusts') or not result.illusts:
            return []
        
        illusts = []
        for illust in result.illusts[:params.limit]:
            illusts.append({
                "id": illust.id,
                "title": illust.title,
                "link": f"https://www.pixiv.net/artworks/{illust.id}",
                "user": {
                    "id": illust.user.id,
                    "name": illust.user.name,
                    "account": illust.user.account,
                },
                "tags": [tag.name for tag in illust.tags],
                "create_date": illust.create_date,
                "page_count": illust.page_count,
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
        raise Exception(f"获取相关插画失败: {str(e)}")


async def illust_recommended(params: IllustRecommendedParams) -> List[Dict[str, Any]]:
    """获取推荐插画"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.illust_recommended, content_type=params.content_type)
        
        if not hasattr(result, 'illusts') or not result.illusts:
            return []
        
        illusts = []
        for illust in result.illusts[:params.limit]:
            illusts.append({
                "id": illust.id,
                "title": illust.title,
                "link": f"https://www.pixiv.net/artworks/{illust.id}",
                "user": {
                    "id": illust.user.id,
                    "name": illust.user.name,
                    "account": illust.user.account,
                },
                "tags": [tag.name for tag in illust.tags],
                "create_date": illust.create_date,
                "page_count": illust.page_count,
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
        raise Exception(f"获取推荐插画失败: {str(e)}")


async def novel_recommended(params: NovelRecommendedParams) -> List[Dict[str, Any]]:
    """获取推荐小说"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.novel_recommended)
        
        if not hasattr(result, 'novels') or not result.novels:
            return []
        
        novels = []
        for novel in result.novels[:params.limit]:
            novels.append({
                "id": novel.id,
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
                "is_original": novel.is_original if hasattr(novel, 'is_original') else False,
                "image_urls": novel.image_urls if hasattr(novel, 'image_urls') else {},
            })
        
        return novels
        
    except Exception as e:
        raise Exception(f"获取推荐小说失败: {str(e)}")


async def search_novel(params: SearchNovelParams) -> List[Dict[str, Any]]:
    """搜索小说"""
    try:
        api = get_api()
        result = await asyncio.to_thread(
            api.search_novel,
            params.word,
            search_target=params.search_target,
            sort=params.sort,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        
        if not hasattr(result, 'novels') or not result.novels:
            return []
        
        novels = []
        for novel in result.novels[:params.limit]:
            novels.append({
                "id": novel.id,
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
                "is_original": novel.is_original if hasattr(novel, 'is_original') else False,
                "image_urls": novel.image_urls if hasattr(novel, 'image_urls') else {},
            })
        
        return novels
        
    except Exception as e:
        raise Exception(f"搜索小说失败: {str(e)}")


async def search_user(params: SearchUserParams) -> List[Dict[str, Any]]:
    """搜索用户"""
    try:
        api = get_api()
        result = await asyncio.to_thread(
            api.search_user,
            params.word,
            sort=params.sort,
            duration=params.duration,
        )
        
        if not hasattr(result, 'user_previews') or not result.user_previews:
            return []
        
        users = []
        for user_preview in result.user_previews[:params.limit]:
            user = user_preview.user
            users.append({
                "id": user.id,
                "name": user.name,
                "account": user.account,
                "profile_image_urls": user.profile_image_urls,
                "comment": user.comment if hasattr(user, 'comment') else "",
                "is_followed": user.is_followed if hasattr(user, 'is_followed') else False,
                "illusts": [
                    {
                        "id": illust.id,
                        "title": illust.title,
                        "image_urls": illust.image_urls,
                    } for illust in user_preview.illusts[:3]  # 只取前3个作品作为预览
                ] if hasattr(user_preview, 'illusts') and user_preview.illusts else [],
            })
        
        return users
        
    except Exception as e:
        raise Exception(f"搜索用户失败: {str(e)}")


async def illust_bookmark_detail(params: IllustDetailParams) -> Dict[str, Any]:
    """获取作品收藏详情"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.illust_bookmark_detail, params.illust_id)
        
        if not hasattr(result, 'bookmark_detail'):
            return {"is_bookmarked": False, "tags": [], "restrict": "public"}
        
        detail = result.bookmark_detail
        return {
            "is_bookmarked": detail.is_bookmarked if hasattr(detail, 'is_bookmarked') else False,
            "tags": [tag.name for tag in detail.tags] if hasattr(detail, 'tags') and detail.tags else [],
            "restrict": detail.restrict if hasattr(detail, 'restrict') else "public",
        }
        
    except Exception as e:
        raise Exception(f"获取作品收藏详情失败: {str(e)}")


async def illust_bookmark_add(params: IllustBookmarkParams) -> Dict[str, Any]:
    """添加作品收藏"""
    try:
        api = get_api()
        result = await asyncio.to_thread(
            api.illust_bookmark_add, 
            params.illust_id, 
            restrict=params.restrict,
            tags=params.tags
        )
        
        return {
            "success": True,
            "illust_id": params.illust_id,
            "restrict": params.restrict,
            "tags": params.tags or [],
        }
        
    except Exception as e:
        raise Exception(f"添加作品收藏失败: {str(e)}")


async def illust_bookmark_delete(params: IllustDetailParams) -> Dict[str, Any]:
    """删除作品收藏"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.illust_bookmark_delete, params.illust_id)
        
        return {
            "success": True,
            "illust_id": params.illust_id,
        }
        
    except Exception as e:
        raise Exception(f"删除作品收藏失败: {str(e)}")


async def user_follow_add(params: UserFollowParams) -> Dict[str, Any]:
    """关注用户"""
    try:
        api = get_api()
        result = await asyncio.to_thread(
            api.user_follow_add, 
            params.user_id, 
            restrict=params.restrict
        )
        
        return {
            "success": True,
            "user_id": params.user_id,
            "restrict": params.restrict,
        }
        
    except Exception as e:
        raise Exception(f"关注用户失败: {str(e)}")


async def user_follow_delete(params: UserDetailParams) -> Dict[str, Any]:
    """取消关注用户"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.user_follow_delete, params.user_id)
        
        return {
            "success": True,
            "user_id": params.user_id,
        }
        
    except Exception as e:
        raise Exception(f"取消关注用户失败: {str(e)}")


async def user_bookmark_tags_illust(params: UserBookmarkTagsParams) -> List[Dict[str, Any]]:
    """获取用户收藏标签列表"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.user_bookmark_tags_illust, restrict=params.restrict)
        
        if not hasattr(result, 'bookmark_tags') or not result.bookmark_tags:
            return []
        
        tags = []
        for tag_info in result.bookmark_tags:
            tags.append({
                "name": tag_info.name,
                "count": tag_info.count if hasattr(tag_info, 'count') else 0,
            })
        
        return tags
        
    except Exception as e:
        raise Exception(f"获取用户收藏标签失败: {str(e)}")


async def user_following(params: UserFollowingParams) -> List[Dict[str, Any]]:
    """获取用户关注列表"""
    try:
        api = get_api()
        result = await asyncio.to_thread(
            api.user_following, 
            params.user_id, 
            restrict=params.restrict
        )
        
        if not hasattr(result, 'user_previews') or not result.user_previews:
            return []
        
        users = []
        for user_preview in result.user_previews[:params.limit]:
            user = user_preview.user
            users.append({
                "id": user.id,
                "name": user.name,
                "account": user.account,
                "profile_image_urls": user.profile_image_urls,
                "comment": user.comment if hasattr(user, 'comment') else "",
                "is_followed": user.is_followed if hasattr(user, 'is_followed') else False,
                "illusts": [
                    {
                        "id": illust.id,
                        "title": illust.title,
                        "image_urls": illust.image_urls,
                    } for illust in user_preview.illusts[:3]
                ] if hasattr(user_preview, 'illusts') and user_preview.illusts else [],
            })
        
        return users
        
    except Exception as e:
        raise Exception(f"获取用户关注列表失败: {str(e)}")


async def user_follower(params: UserFollowerParams) -> List[Dict[str, Any]]:
    """获取用户粉丝列表"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.user_follower, params.user_id)
        
        if not hasattr(result, 'user_previews') or not result.user_previews:
            return []
        
        users = []
        for user_preview in result.user_previews[:params.limit]:
            user = user_preview.user
            users.append({
                "id": user.id,
                "name": user.name,
                "account": user.account,
                "profile_image_urls": user.profile_image_urls,
                "comment": user.comment if hasattr(user, 'comment') else "",
                "is_followed": user.is_followed if hasattr(user, 'is_followed') else False,
                "illusts": [
                    {
                        "id": illust.id,
                        "title": illust.title,
                        "image_urls": illust.image_urls,
                    } for illust in user_preview.illusts[:3]
                ] if hasattr(user_preview, 'illusts') and user_preview.illusts else [],
            })
        
        return users
        
    except Exception as e:
        raise Exception(f"获取用户粉丝列表失败: {str(e)}")


async def user_mypixiv(params: UserMypixivParams) -> List[Dict[str, Any]]:
    """获取用户好P友列表"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.user_mypixiv, params.user_id)
        
        if not hasattr(result, 'user_previews') or not result.user_previews:
            return []
        
        users = []
        for user_preview in result.user_previews[:params.limit]:
            user = user_preview.user
            users.append({
                "id": user.id,
                "name": user.name,
                "account": user.account,
                "profile_image_urls": user.profile_image_urls,
                "comment": user.comment if hasattr(user, 'comment') else "",
                "illusts": [
                    {
                        "id": illust.id,
                        "title": illust.title,
                        "image_urls": illust.image_urls,
                    } for illust in user_preview.illusts[:3]
                ] if hasattr(user_preview, 'illusts') and user_preview.illusts else [],
            })
        
        return users
        
    except Exception as e:
        raise Exception(f"获取用户好P友列表失败: {str(e)}")


async def ugoira_metadata(params: UgoiraMetadataParams) -> Dict[str, Any]:
    """获取动图元数据"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.ugoira_metadata, params.illust_id)
        
        if not hasattr(result, 'ugoira_metadata'):
            raise Exception("无法获取动图元数据")
        
        metadata = result.ugoira_metadata
        return {
            "zip_urls": metadata.zip_urls.__dict__ if hasattr(metadata, 'zip_urls') else {},
            "frames": [
                {
                    "file": frame.file,
                    "delay": frame.delay,
                } for frame in metadata.frames
            ] if hasattr(metadata, 'frames') and metadata.frames else [],
        }
        
    except Exception as e:
        raise Exception(f"获取动图元数据失败: {str(e)}")


async def user_novels(params: UserNovelsParams) -> List[Dict[str, Any]]:
    """获取用户小说列表"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.user_novels, params.user_id)
        
        if not hasattr(result, 'novels') or not result.novels:
            return []
        
        novels = []
        for novel in result.novels[:params.limit]:
            novels.append({
                "id": novel.id,
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
                "is_original": novel.is_original if hasattr(novel, 'is_original') else False,
                "image_urls": novel.image_urls if hasattr(novel, 'image_urls') else {},
            })
        
        return novels
        
    except Exception as e:
        raise Exception(f"获取用户小说列表失败: {str(e)}")


async def novel_series(params: NovelSeriesParams) -> Dict[str, Any]:
    """获取小说系列详情"""
    try:
        api = get_api()
        result = await asyncio.to_thread(
            api.novel_series, 
            params.series_id, 
            last_order=params.last_order
        )
        
        if not hasattr(result, 'novels') or not result.novels:
            return {"novels": [], "series_detail": {}}
        
        novels = []
        for novel in result.novels:
            novels.append({
                "id": novel.id,
                "title": novel.title,
                "caption": novel.caption,
                "tags": [tag.name for tag in novel.tags],
                "create_date": novel.create_date,
                "page_count": novel.page_count,
                "text_length": novel.text_length,
                "total_view": novel.total_view,
                "total_bookmarks": novel.total_bookmarks,
            })
        
        series_detail = {}
        if hasattr(result, 'series_detail'):
            detail = result.series_detail
            series_detail = {
                "id": detail.id,
                "title": detail.title,
                "caption": detail.caption,
                "is_original": detail.is_original if hasattr(detail, 'is_original') else False,
                "is_concluded": detail.is_concluded if hasattr(detail, 'is_concluded') else False,
                "content_count": detail.content_count if hasattr(detail, 'content_count') else 0,
                "total_character_count": detail.total_character_count if hasattr(detail, 'total_character_count') else 0,
            }
        
        return {
            "novels": novels,
            "series_detail": series_detail,
        }
        
    except Exception as e:
        raise Exception(f"获取小说系列详情失败: {str(e)}")


async def novel_detail(params: NovelDetailParams) -> Dict[str, Any]:
    """获取小说详情"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.novel_detail, params.novel_id)
        
        if not hasattr(result, 'novel') or not result.novel:
            raise Exception("小说不存在或已被删除")
        
        novel = result.novel
        
        return {
            "id": novel.id,
            "title": novel.title,
            "caption": novel.caption,
            "user": {
                "id": novel.user.id,
                "name": novel.user.name,
                "account": novel.user.account,
                "profile_image_urls": novel.user.profile_image_urls,
            },
            "tags": [{"name": tag.name, "translated_name": tag.translated_name} for tag in novel.tags],
            "create_date": novel.create_date,
            "page_count": novel.page_count,
            "text_length": novel.text_length,
            "total_view": novel.total_view,
            "total_bookmarks": novel.total_bookmarks,
            "is_bookmarked": novel.is_bookmarked if hasattr(novel, 'is_bookmarked') else False,
            "is_original": novel.is_original if hasattr(novel, 'is_original') else False,
            "image_urls": novel.image_urls if hasattr(novel, 'image_urls') else {},
            "series": {
                "id": novel.series.id,
                "title": novel.series.title,
            } if hasattr(novel, 'series') and novel.series else None,
        }
        
    except Exception as e:
        raise Exception(f"获取小说详情失败: {str(e)}")


async def novel_comments(params: NovelCommentsParams) -> List[Dict[str, Any]]:
    """获取小说评论"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.novel_comments, params.novel_id)
        
        if not hasattr(result, 'comments') or not result.comments:
            return []
        
        comments = []
        for comment in result.comments:
            comments.append({
                "id": comment.id,
                "comment": comment.comment,
                "date": comment.date,
                "user": {
                    "id": comment.user.id,
                    "name": comment.user.name,
                    "account": comment.user.account,
                    "profile_image_urls": comment.user.profile_image_urls,
                },
                "parent_comment": {
                    "id": comment.parent_comment.id,
                    "user": {
                        "id": comment.parent_comment.user.id,
                        "name": comment.parent_comment.user.name,
                    }
                } if hasattr(comment, 'parent_comment') and comment.parent_comment else None,
            })
        
        return comments
        
    except Exception as e:
        raise Exception(f"获取小说评论失败: {str(e)}")


async def illust_new(params: IllustNewParams) -> List[Dict[str, Any]]:
    """获取大家的新作插画"""
    try:
        api = get_api()
        result = await asyncio.to_thread(
            api.illust_new, 
            content_type=params.content_type,
            max_illust_id=params.max_illust_id
        )
        
        if not hasattr(result, 'illusts') or not result.illusts:
            return []
        
        illusts = []
        for illust in result.illusts[:params.limit]:
            illusts.append({
                "id": illust.id,
                "title": illust.title,
                "link": f"https://www.pixiv.net/artworks/{illust.id}",
                "user": {
                    "id": illust.user.id,
                    "name": illust.user.name,
                    "account": illust.user.account,
                },
                "tags": [tag.name for tag in illust.tags],
                "create_date": illust.create_date,
                "page_count": illust.page_count,
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
        raise Exception(f"获取大家的新作插画失败: {str(e)}")


async def novel_new(params: NovelNewParams) -> List[Dict[str, Any]]:
    """获取大家的新作小说"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.novel_new, max_novel_id=params.max_novel_id)
        
        if not hasattr(result, 'novels') or not result.novels:
            return []
        
        novels = []
        for novel in result.novels[:params.limit]:
            novels.append({
                "id": novel.id,
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
                "is_original": novel.is_original if hasattr(novel, 'is_original') else False,
                "image_urls": novel.image_urls if hasattr(novel, 'image_urls') else {},
            })
        
        return novels
        
    except Exception as e:
        raise Exception(f"获取大家的新作小说失败: {str(e)}")


async def showcase_article(params: ShowcaseArticleParams) -> Dict[str, Any]:
    """获取特辑详情"""
    try:
        api = get_api()
        result = await asyncio.to_thread(api.showcase_article, params.showcase_id)
        
        if not hasattr(result, 'showcase_article'):
            raise Exception("特辑不存在")
        
        article = result.showcase_article
        return {
            "id": article.id,
            "title": article.title,
            "pure_title": article.pure_title if hasattr(article, 'pure_title') else "",
            "thumbnail": article.thumbnail if hasattr(article, 'thumbnail') else "",
            "article_url": article.article_url if hasattr(article, 'article_url') else "",
            "publish_date": article.publish_date if hasattr(article, 'publish_date') else "",
            "category": article.category if hasattr(article, 'category') else "",
            "subcategory_label": article.subcategory_label if hasattr(article, 'subcategory_label') else "",
        }
        
    except Exception as e:
        raise Exception(f"获取特辑详情失败: {str(e)}")


# ==================== Tools Registry ====================

TOOLS = [
    # 原有的8个核心工具
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
    
    # 新增的全面API工具
    Tool(
        name="pixiv_user_bookmarks_illust",
        description="获取用户收藏的插画列表",
        inputSchema=UserBookmarksParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_user_bookmarks_novel",
        description="获取用户收藏的小说列表",
        inputSchema=UserBookmarksParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_user_related",
        description="获取与指定用户相关的其他用户推荐",
        inputSchema=UserRelatedParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_illust_follow",
        description="获取关注用户的最新插画作品",
        inputSchema=IllustFollowParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_illust_comments",
        description="获取指定插画的评论列表",
        inputSchema=IllustCommentsParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_illust_related",
        description="获取与指定插画相关的其他插画推荐",
        inputSchema=IllustRelatedParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_illust_recommended",
        description="获取系统推荐的插画列表",
        inputSchema=IllustRecommendedParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_novel_recommended",
        description="获取系统推荐的小说列表",
        inputSchema=NovelRecommendedParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_search_novel",
        description="搜索Pixiv小说。支持按关键词、标签、正文搜索",
        inputSchema=SearchNovelParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_search_user",
        description="搜索Pixiv用户。可根据用户名搜索创作者",
        inputSchema=SearchUserParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_illust_bookmark_detail",
        description="获取指定插画的收藏详情",
        inputSchema=IllustDetailParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_illust_bookmark_add",
        description="添加插画到收藏夹",
        inputSchema=IllustBookmarkParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_illust_bookmark_delete",
        description="从收藏夹中删除插画",
        inputSchema=IllustDetailParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_user_follow_add",
        description="关注指定用户",
        inputSchema=UserFollowParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_user_follow_delete",
        description="取消关注指定用户",
        inputSchema=UserDetailParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_user_bookmark_tags_illust",
        description="获取用户的收藏标签列表",
        inputSchema=UserBookmarkTagsParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_user_following",
        description="获取用户关注的其他用户列表",
        inputSchema=UserFollowingParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_user_follower",
        description="获取用户的粉丝列表",
        inputSchema=UserFollowerParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_user_mypixiv",
        description="获取用户的好P友列表",
        inputSchema=UserMypixivParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_ugoira_metadata",
        description="获取动图(Ugoira)的元数据信息",
        inputSchema=UgoiraMetadataParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_user_novels",
        description="获取指定用户的小说作品列表",
        inputSchema=UserNovelsParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_novel_series",
        description="获取小说系列的详细信息和作品列表",
        inputSchema=NovelSeriesParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_novel_detail",
        description="获取指定小说的详细信息（不包含正文）",
        inputSchema=NovelDetailParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_novel_comments",
        description="获取指定小说的评论列表",
        inputSchema=NovelCommentsParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_illust_new",
        description="获取大家的新作插画列表",
        inputSchema=IllustNewParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_novel_new",
        description="获取大家的新作小说列表",
        inputSchema=NovelNewParams.model_json_schema(),
    ),
    Tool(
        name="pixiv_showcase_article",
        description="获取Pixiv特辑文章的详细信息",
        inputSchema=ShowcaseArticleParams.model_json_schema(),
    ),
    Tool(
        name="get_current_time",
        description="获取当前时间信息，包括当前日期、时区信息以及常用的时间范围建议（如过去两年、过去一年等）",
        inputSchema=GetCurrentTimeParams.model_json_schema(),
    ),
    Tool(
        name="test_date_ranges",
        description="测试不同的日期范围，检查Pixiv API是否对搜索时间范围有限制",
        inputSchema=SearchIllustParams.model_json_schema(),
    ),
]


# ==================== Dispatcher ====================

async def dispatch(name: str, arguments: dict) -> Any:
    """工具调用分发器"""
    try:
        # 原有的8个核心工具
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
        
        # 新增的全面API工具
        elif name == "pixiv_user_bookmarks_illust":
            return await user_bookmarks_illust(UserBookmarksParams(**arguments))
        elif name == "pixiv_user_bookmarks_novel":
            return await user_bookmarks_novel(UserBookmarksParams(**arguments))
        elif name == "pixiv_user_related":
            return await user_related(UserRelatedParams(**arguments))
        elif name == "pixiv_illust_follow":
            return await illust_follow(IllustFollowParams(**arguments))
        elif name == "pixiv_illust_comments":
            return await illust_comments(IllustCommentsParams(**arguments))
        elif name == "pixiv_illust_related":
            return await illust_related(IllustRelatedParams(**arguments))
        elif name == "pixiv_illust_recommended":
            return await illust_recommended(IllustRecommendedParams(**arguments))
        elif name == "pixiv_novel_recommended":
            return await novel_recommended(NovelRecommendedParams(**arguments))
        elif name == "pixiv_search_novel":
            return await search_novel(SearchNovelParams(**arguments))
        elif name == "pixiv_search_user":
            return await search_user(SearchUserParams(**arguments))
        elif name == "pixiv_illust_bookmark_detail":
            return await illust_bookmark_detail(IllustDetailParams(**arguments))
        elif name == "pixiv_illust_bookmark_add":
            return await illust_bookmark_add(IllustBookmarkParams(**arguments))
        elif name == "pixiv_illust_bookmark_delete":
            return await illust_bookmark_delete(IllustDetailParams(**arguments))
        elif name == "pixiv_user_follow_add":
            return await user_follow_add(UserFollowParams(**arguments))
        elif name == "pixiv_user_follow_delete":
            return await user_follow_delete(UserDetailParams(**arguments))
        elif name == "pixiv_user_bookmark_tags_illust":
            return await user_bookmark_tags_illust(UserBookmarkTagsParams(**arguments))
        elif name == "pixiv_user_following":
            return await user_following(UserFollowingParams(**arguments))
        elif name == "pixiv_user_follower":
            return await user_follower(UserFollowerParams(**arguments))
        elif name == "pixiv_user_mypixiv":
            return await user_mypixiv(UserMypixivParams(**arguments))
        elif name == "pixiv_ugoira_metadata":
            return await ugoira_metadata(UgoiraMetadataParams(**arguments))
        elif name == "pixiv_user_novels":
            return await user_novels(UserNovelsParams(**arguments))
        elif name == "pixiv_novel_series":
            return await novel_series(NovelSeriesParams(**arguments))
        elif name == "pixiv_novel_detail":
            return await novel_detail(NovelDetailParams(**arguments))
        elif name == "pixiv_novel_comments":
            return await novel_comments(NovelCommentsParams(**arguments))
        elif name == "pixiv_illust_new":
            return await illust_new(IllustNewParams(**arguments))
        elif name == "pixiv_novel_new":
            return await novel_new(NovelNewParams(**arguments))
        elif name == "pixiv_showcase_article":
            return await showcase_article(ShowcaseArticleParams(**arguments))
        elif name == "get_current_time":
            return await get_current_time(GetCurrentTimeParams(**arguments))
        elif name == "test_date_ranges":
            # 特殊的测试工具，直接调用搜索功能但添加调试信息
            result = await search_illust(SearchIllustParams(**arguments))
            return {
                "test_params": arguments,
                "result_count": len(result) if isinstance(result, list) else 0,
                "first_result_date": result[0]["create_date"] if result and len(result) > 0 else None,
                "last_result_date": result[-1]["create_date"] if result and len(result) > 0 else None,
                "results": result[:3] if result else []  # 只返回前3个结果作为样本
            }
        else:
            raise ValueError(f"未知工具: {name}")
    except Exception as e:
        return {"error": str(e), "tool": name, "arguments": arguments}