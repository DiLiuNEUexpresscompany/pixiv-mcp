"""
Pixiv MCP Server - Enhanced Authentication Module
处理Pixiv API的认证逻辑，集成Playwright OAuth
"""

import os
import sys
import subprocess
import importlib.util
import base64
import hashlib
import secrets
import requests
import time
import re
import getpass
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple


TOKEN_FILE = Path.home() / ".pixiv" / "refresh_token"
USER_CREDENTIALS_FILE = Path.home() / ".pixiv" / "credentials.json"

# Pixiv OAuth 常量
PIXIV_CLIENT_ID = "MOBrBDS8blbauoSck0ZfDbtuzpyT"
PIXIV_CLIENT_SECRET = "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj"
PIXIV_TOKEN_URL = "https://oauth.secure.pixiv.net/auth/token"
REDIRECT_URI = "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback"
USER_AGENT = "PixivAndroidApp/5.0.234 (Android 11; Pixel 5)"


class PixivPlaywrightTokenFetcher:
    """使用Playwright获取Pixiv OAuth Token"""
    
    def __init__(self, username: str, password: str, headless=True):
        self.headless = headless
        self.username = username
        self.password = password
        self.code_verifier = secrets.token_urlsafe(64)
        self.code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(self.code_verifier.encode()).digest()
        ).rstrip(b'=').decode('ascii')

    def get_login_url(self):
        """生成登录URL"""
        return (
            "https://app-api.pixiv.net/web/v1/login?"
            f"code_challenge={self.code_challenge}&"
            "code_challenge_method=S256&client=pixiv-android&"
            f"redirect_uri={REDIRECT_URI}"
        )

    def slow_type(self, page, selector: str, text: str, delay: float = 0.08):
        """缓慢输入文本以避免机器人检测"""
        page.focus(selector)
        for char in text:
            page.keyboard.insert_text(char)
            time.sleep(delay)

    def perform_auto_login(self, page, username: str, password: str):
        """执行自动登录"""
        try:
            # 等待用户名输入框
            page.wait_for_selector("input[autocomplete^='username']", timeout=15000)
            self.slow_type(page, "input[autocomplete^='username']", username)
            page.keyboard.press("Enter")
            print("📧 用户名输入完成")

            # 等待密码输入框
            page.wait_for_selector("input[autocomplete^='current-password']", timeout=15000)
            self.slow_type(page, "input[autocomplete^='current-password']", password)
            page.keyboard.press("Enter")
            print("🔒 密码输入完成")

        except Exception as e:
            print(f"⚠️ 登录输入失败: {e}")
            raise

    def fetch_code(self):
        """获取授权码"""
        try:
            from playwright.sync_api import sync_playwright, TimeoutError
        except ImportError:
            raise ImportError("需要安装playwright: pip install playwright && playwright install")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless, 
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context()
            page = context.new_page()
            cdp_session = context.new_cdp_session(page)
            cdp_session.send("Network.enable")

            print("🚀 打开Pixiv登录页面...")
            page.goto(self.get_login_url())

            captured_code = {"value": None}

            def cleanup_and_return(code):
                """清理资源并返回代码"""
                try:
                    page.close()
                except:
                    pass
                try:
                    context.close()
                except:
                    pass
                try:
                    browser.close()
                except:
                    pass
                return code

            def on_request_will_be_sent(event):
                """监听网络请求以捕获授权码"""
                url = event.get("request", {}).get("url", "")
                check_url = url or event.get("documentURL", "")
                if check_url.startswith("pixiv://account/login"):
                    match = re.search(r"code=([\w-]+)", check_url)
                    if match:
                        captured_code["value"] = match.group(1)
                        print(f"✅ 授权码捕获成功: {captured_code['value']}")
                        page.close()

            cdp_session.on("Network.requestWillBeSent", on_request_will_be_sent)

            # 执行自动登录
            self.perform_auto_login(page, self.username, self.password)

            try:
                page.wait_for_event("close", timeout=100000)  # 增加超时时间
            except TimeoutError:
                print("⌛ 超时：未能捕获授权码")

            return cleanup_and_return(captured_code["value"])

    def exchange_token(self, code: str) -> Dict[str, Any]:
        """将授权码交换为访问令牌"""
        data = {
            "client_id": PIXIV_CLIENT_ID,
            "client_secret": PIXIV_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": self.code_verifier,
            "redirect_uri": REDIRECT_URI,
            "include_policy": "true",
        }
        headers = {"User-Agent": USER_AGENT}
        
        try:
            response = requests.post(PIXIV_TOKEN_URL, data=data, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ 令牌交换失败: {e}")
            return {}

    def get_tokens(self) -> Optional[Tuple[str, str]]:
        """获取访问令牌和刷新令牌"""
        print("🎭 启动Playwright OAuth流程...")
        
        code = self.fetch_code()
        if not code:
            print("❌ 未能获取授权码")
            return None

        print("🔄 交换授权码为令牌...")
        token_info = self.exchange_token(code)
        
        if not token_info:
            print("❌ 令牌交换失败")
            return None

        access_token = token_info.get("access_token")
        refresh_token = token_info.get("refresh_token")
        
        if not refresh_token:
            print("❌ 未获取到刷新令牌")
            return None

        print("✅ OAuth令牌获取成功")
        return access_token, refresh_token


def is_playwright_available() -> bool:
    """检查playwright是否已安装"""
    try:
        import playwright
        return True
    except ImportError:
        return False


def install_playwright() -> bool:
    """安装playwright"""
    print("🔧 正在安装playwright...")
    try:
        # 安装playwright包
        subprocess.run([
            sys.executable, "-m", "pip", "install", "playwright"
        ], check=True, capture_output=True)
        
        # 安装浏览器
        subprocess.run([
            sys.executable, "-m", "playwright", "install", "chromium"
        ], check=True, capture_output=True)
        
        print("✅ playwright安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ playwright安装失败: {e}")
        return False


def is_gppt_available() -> bool:
    """检查gppt是否已安装"""
    try:
        import gppt
        return True
    except ImportError:
        return False


def install_gppt() -> bool:
    """安装gppt工具"""
    print("🔧 正在安装gppt工具...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "gppt"
        ], check=True, capture_output=True)
        print("✅ gppt安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ gppt安装失败: {e}")
        return False


def get_token_with_playwright(username: str = None, password: str = None, headless: bool = True) -> Optional[str]:
    """使用Playwright获取token"""
    try:
        if not username or not password:
            print("需要提供Pixiv账号信息来自动获取token")
            username = input("请输入Pixiv用户名/邮箱: ").strip()
            password = getpass.getpass("请输入Pixiv密码: ").strip()
        
        if not username or not password:
            print("❌ 用户名或密码不能为空")
            return None
        
        fetcher = PixivPlaywrightTokenFetcher(username, password, headless)
        result = fetcher.get_tokens()
        
        if result:
            access_token, refresh_token = result
            print("✅ Token获取成功")
            
            # 可选：保存用户凭据
            save_credentials = input("是否保存登录凭据以便下次自动登录? (y/n): ").lower().strip()
            if save_credentials in ['y', 'yes']:
                save_user_credentials(username, password)
            
            return refresh_token
        else:
            print("❌ Token获取失败")
            return None
            
    except Exception as e:
        print(f"❌ Playwright获取token失败: {e}")
        return None


def get_token_with_gppt(username: str = None, password: str = None, headless: bool = True) -> Optional[str]:
    """使用gppt自动获取token"""
    try:
        from gppt import GetPixivToken
        
        print("🔐 正在使用gppt自动获取Pixiv token...")
        
        if not username or not password:
            print("需要提供Pixiv账号信息来自动获取token")
            username = input("请输入Pixiv用户名/邮箱: ").strip()
            password = getpass.getpass("请输入Pixiv密码: ").strip()
        
        if not username or not password:
            print("❌ 用户名或密码不能为空")
            return None
        
        # 使用gppt获取token
        g = GetPixivToken(headless=headless)
        result = g.login(username=username, password=password)
        
        if result and "refresh_token" in result:
            refresh_token = result["refresh_token"]
            print("✅ Token获取成功")
            
            # 可选：保存用户凭据
            save_credentials = input("是否保存登录凭据以便下次自动登录? (y/n): ").lower().strip()
            if save_credentials in ['y', 'yes']:
                save_user_credentials(username, password)
            
            return refresh_token
        else:
            print("❌ Token获取失败")
            return None
            
    except Exception as e:
        print(f"❌ gppt获取token失败: {e}")
        return None


def save_user_credentials(username: str, password: str) -> None:
    """保存用户凭据（简单加密）"""
    try:
        # 简单的Base64编码（注意：这不是安全的加密）
        credentials = {
            "username": base64.b64encode(username.encode()).decode(),
            "password": base64.b64encode(password.encode()).decode()
        }
        
        USER_CREDENTIALS_FILE.parent.mkdir(exist_ok=True)
        with open(USER_CREDENTIALS_FILE, 'w') as f:
            json.dump(credentials, f)
        USER_CREDENTIALS_FILE.chmod(0o600)
        
        print(f"✅ 凭据已保存到: {USER_CREDENTIALS_FILE}")
        
    except Exception as e:
        print(f"⚠️  保存凭据失败: {e}")


def load_user_credentials() -> Optional[tuple]:
    """加载保存的用户凭据"""
    try:
        if not USER_CREDENTIALS_FILE.exists():
            return None
        
        with open(USER_CREDENTIALS_FILE, 'r') as f:
            credentials = json.load(f)
        
        username = base64.b64decode(credentials["username"]).decode()
        password = base64.b64decode(credentials["password"]).decode()
        
        return username, password
        
    except Exception as e:
        print(f"⚠️  加载凭据失败: {e}")
        return None


def refresh_existing_token(refresh_token: str) -> Optional[str]:
    """刷新现有token"""
    try:
        print("🔄 正在刷新token...")
        
        data = {
            "client_id": PIXIV_CLIENT_ID,
            "client_secret": PIXIV_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "include_policy": "true",
        }
        headers = {"User-Agent": USER_AGENT}
        
        response = requests.post(PIXIV_TOKEN_URL, data=data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        new_refresh_token = result.get("refresh_token")
        
        if new_refresh_token:
            print("✅ Token刷新成功")
            return new_refresh_token
        else:
            print("❌ Token刷新失败：响应中无refresh_token")
            return None
        
    except Exception as e:
        print(f"❌ Token刷新失败: {e}")
        return None


def auto_setup_token() -> Optional[str]:
    """自动设置token的完整流程"""
    print("🚀 开始自动token配置流程...")
    
    # 1. 检查playwright是否可用
    playwright_available = is_playwright_available()
    gppt_available = is_gppt_available()
    
    if not playwright_available and not gppt_available:
        print("❌ 未检测到playwright或gppt工具")
        print("选择安装:")
        print("1. Playwright (推荐) - 更稳定可靠")
        print("2. gppt - 轻量级但可能被限制")
        
        choice = input("请选择要安装的工具 (1-2): ").strip()
        
        if choice == "1":
            if not install_playwright():
                return None
            playwright_available = True
        elif choice == "2":
            if not install_gppt():
                return None
            gppt_available = True
        else:
            print("❌ 无效选择")
            return None
    
    # 2. 检查是否有保存的凭据
    credentials = load_user_credentials()
    if credentials:
        username, password = credentials
        use_saved = input(f"检测到保存的账号 {username[:3]}***，是否使用? (y/n): ").lower().strip()
        if use_saved in ['y', 'yes']:
            # 优先使用playwright
            if playwright_available:
                return get_token_with_playwright(username, password)
            elif gppt_available:
                return get_token_with_gppt(username, password)
    
    # 3. 选择获取方式
    print("\n选择token获取方式:")
    methods = []
    
    if playwright_available:
        methods.append("1. Playwright自动获取 (推荐) - 使用官方OAuth流程")
    if gppt_available:
        methods.append("2. gppt自动获取 - 使用账号密码自动登录")
    
    methods.extend([
        f"{len(methods) + 1}. 交互式获取 - 打开浏览器手动登录",
        f"{len(methods) + 2}. 手动输入 - 直接输入已有token"
    ])
    
    for method in methods:
        print(method)
    
    choice = input(f"请选择 (1-{len(methods)}): ").strip()
    
    if choice == "1" and playwright_available:
        return get_token_with_playwright()
    
    elif (choice == "1" and not playwright_available and gppt_available) or (choice == "2" and gppt_available):
        return get_token_with_gppt()
    
    elif choice == str(len(methods) - 1):  # 交互式获取
        # 优先使用playwright的交互式模式
        if playwright_available:
            return get_token_with_playwright(headless=False)
        elif gppt_available:
            try:
                from gppt import GetPixivToken
                print("🔐 正在启动交互式登录...")
                g = GetPixivToken(headless=False)
                result = g.login()
                if result and "refresh_token" in result:
                    print("✅ Token获取成功")
                    return result["refresh_token"]
            except Exception as e:
                print(f"❌ 交互式登录失败: {e}")
                return None
    
    elif choice == str(len(methods)):  # 手动输入
        token = input("请输入refresh token: ").strip()
        if validate_token_format(token):
            return token
        else:
            print("❌ Token格式不正确")
            return None
    
    else:
        print("❌ 无效选择")
        return None


def ensure_refresh_token() -> None:
    """确保refresh token已配置，支持自动获取"""
    # 1. 检查环境变量
    if os.getenv("PIXIV_REFRESH_TOKEN"):
        return
    
    # 2. 检查token文件
    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text().strip()
        if token and validate_token_format(token):
            return
        else:
            print("⚠️  检测到无效的token文件")
    
    # 3. 尝试自动配置
    print("❌ Pixiv refresh token未配置！")
    auto_setup = input("是否自动配置token? (y/n): ").lower().strip()
    
    if auto_setup in ['y', 'yes', '']:
        token = auto_setup_token()
        if token:
            setup_token_file(token)
            print("✅ Token配置完成")
            return
    
    # 4. 手动配置说明
    print(
        "\n手动配置方法:\n"
        "1. 设置环境变量: export PIXIV_REFRESH_TOKEN='your_token'\n"
        "2. 创建文件: ~/.pixiv/refresh_token 并写入token\n"
        "3. 使用playwright: pip install playwright && python -m pixiv_mcp.token_manager auto\n"
        "4. 使用gppt工具: pip install gppt && python -m pixiv_mcp.token_manager auto\n"
        "\n"
        "获取token方法: https://github.com/eggplants/get-pixivpy-token",
        file=sys.stderr,
    )
    sys.exit(1)


def get_refresh_token() -> str:
    """获取refresh token"""
    # 优先从环境变量获取
    if token := os.getenv("PIXIV_REFRESH_TOKEN"):
        return token.strip()
    
    # 从文件获取
    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text().strip()
        if token:
            return token
    
    raise ValueError("未找到Pixiv refresh token")


def setup_token_file(token: str) -> None:
    """设置token文件（用于初始化）"""
    TOKEN_FILE.parent.mkdir(exist_ok=True)
    TOKEN_FILE.write_text(token.strip())
    TOKEN_FILE.chmod(0o600)  # 仅当前用户可读写
    print(f"✅ Token已保存到: {TOKEN_FILE}")


def validate_token_format(token: str) -> bool:
    """验证token格式（基本检查）"""
    if not token or len(token) < 20:
        return False
    # 基本的token格式检查
    return True


def clear_saved_credentials() -> None:
    """清除保存的凭据"""
    try:
        if USER_CREDENTIALS_FILE.exists():
            USER_CREDENTIALS_FILE.unlink()
            print("✅ 已清除保存的凭据")
        
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
            print("✅ 已清除保存的token")
            
    except Exception as e:
        print(f"⚠️  清除文件失败: {e}")


def token_status() -> Dict[str, Any]:
    """检查token状态"""
    status = {
        "env_token_exists": bool(os.getenv("PIXIV_REFRESH_TOKEN")),
        "file_token_exists": TOKEN_FILE.exists(),
        "credentials_saved": USER_CREDENTIALS_FILE.exists(),
        "playwright_available": is_playwright_available(),
        "gppt_available": is_gppt_available(),
    }
    
    if status["file_token_exists"]:
        try:
            token = TOKEN_FILE.read_text().strip()
            status["file_token_valid"] = validate_token_format(token)
            status["file_token_length"] = len(token)
        except:
            status["file_token_valid"] = False
    
    return status