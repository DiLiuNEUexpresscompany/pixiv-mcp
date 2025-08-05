"""
Pixiv MCP Server - Simplified Authentication Module
简化的Pixiv认证模块，使用Playwright进行手动登录
"""

import os
import sys
import subprocess
import base64
import hashlib
import secrets
import requests
import time
import re
import getpass
import json
from pathlib import Path
from typing import Optional, Dict, Any
from playwright.sync_api import sync_playwright, TimeoutError


# 获取项目根目录：从src/auth.py -> src -> 项目根目录  
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env"  # 新的存储位置

# Pixiv OAuth 常量
PIXIV_CLIENT_ID = "MOBrBDS8blbauoSck0ZfDbtuzpyT"
PIXIV_CLIENT_SECRET = "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj"
PIXIV_TOKEN_URL = "https://oauth.secure.pixiv.net/auth/token"
REDIRECT_URI = "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback"
USER_AGENT = "PixivAndroidApp/5.0.234 (Android 11; Pixel 5)"


class PixivTokenFetcher:
    """使用Playwright获取Pixiv OAuth Token - 简化版本"""
    
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
            page.wait_for_selector("input[autocomplete^='username']", timeout=15000)
            self.slow_type(page, "input[autocomplete^='username']", username)
            page.keyboard.press("Enter")
            print("📧 Username input completed (slow typing mode)")

            page.wait_for_selector("input[autocomplete^='current-password']", timeout=15000)
            self.slow_type(page, "input[autocomplete^='current-password']", password)
            page.keyboard.press("Enter")
            print("🔒 Password input completed (slow typing mode)")

        except TimeoutError:
            print("⚠️ Login input fields not found. Please check the page structure or network connectivity.")

    def fetch_code(self):
        """获取授权码"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless, args=["--disable-blink-features=AutomationControlled"])
            context = browser.new_context()
            page = context.new_page()
            cdp_session = context.new_cdp_session(page)
            cdp_session.send("Network.enable")

            print("🚀 Opening Pixiv login page...")
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
                        print("✅ Code captured via CDP:", captured_code["value"], flush=True)
                        # Trick: close page to interrupt wait loop
                        page.close()

            cdp_session.on("Network.requestWillBeSent", on_request_will_be_sent)

            self.perform_auto_login(page, self.username, self.password)

            try:
                page.wait_for_event("close", timeout=100000)  # 100秒超时，更合理
            except TimeoutError:
                print("⌛ Timeout: Code not captured.")

            return cleanup_and_return(captured_code["value"])

    def exchange_token(self, code):
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
        response = requests.post(PIXIV_TOKEN_URL, data=data, headers=headers)
        return response.json()

    def get_tokens(self):
        """获取访问令牌和刷新令牌"""
        print("🎭 启动Playwright OAuth流程...")
        
        code = self.fetch_code()
        if code:
            print("✅ Authorization code successfully obtained:", code)
            token_info = self.exchange_token(code)
            if token_info.get("refresh_token"):
                print("✅ OAuth令牌获取成功")
                return token_info.get("access_token"), token_info.get("refresh_token")
        
        print("❌ Failed to retrieve authorization code. Please verify the login process.")
        return None


# ==================== 简化的认证接口 ====================

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


def get_token(username: str = None, password: str = None, headless: bool = True) -> Optional[str]:
    """获取Pixiv token - 唯一入口"""
    try:
        if not username or not password:
            print("请提供Pixiv账号信息来获取token")
            username = input("请输入Pixiv用户名/邮箱: ").strip()
            password = getpass.getpass("请输入Pixiv密码: ").strip()
        
        if not username or not password:
            print("❌ 用户名或密码不能为空")
            return None
        
        # 检查playwright是否可用
        if not is_playwright_available():
            print("❌ 需要安装playwright: pip install playwright && playwright install")
            install_choice = input("是否自动安装? (y/n): ").lower().strip()
            if install_choice in ['y', 'yes']:
                if not install_playwright():
                    return None
            else:
                return None
        
        fetcher = PixivTokenFetcher(username, password, headless)
        result = fetcher.get_tokens()
        
        if result:
            access_token, refresh_token = result
            return refresh_token
        else:
            print("❌ Token获取失败")
            return None
            
    except Exception as e:
        print(f"❌ 获取token失败: {e}")
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
    """自动设置token - 简化版本"""
    print("🚀 自动获取Pixiv token...")
    
    # 简单直接的流程：只使用Playwright
    if not is_playwright_available():
        print("❌ 需要安装playwright")
        install_choice = input("是否自动安装playwright? (y/n): ").lower().strip()
        if install_choice in ['y', 'yes']:
            if not install_playwright():
                return None
        else:
            print("请手动安装: pip install playwright && playwright install")
            return None
    
    return get_token()


def ensure_refresh_token() -> None:
    """确保refresh token已配置"""
    try:
        token = get_refresh_token()
        if token and validate_token_format(token):
            return
    except ValueError:
        pass
    
    # 提示用户手动配置
    print("❌ Pixiv refresh token未配置！")
    print("由于Pixiv需要二步验证和图片验证码，请使用交互式登录获取token：")
    print("  python -m pixiv_mcp.token_manager login")
    print(f"Token将保存到项目目录下的.env文件中: {ENV_FILE}")
    sys.exit(1)


def read_env_file() -> Dict[str, str]:
    """读取.env文件"""
    env_vars = {}
    if ENV_FILE.exists():
        try:
            with open(ENV_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        except Exception as e:
            print(f"⚠️  读取.env文件失败: {e}")
    return env_vars


def write_env_file(env_vars: Dict[str, str]) -> None:
    """写入.env文件"""
    try:
        lines = []
        if ENV_FILE.exists():
            # 保留现有的其他环境变量
            with open(ENV_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, _ = line.split('=', 1)
                        if key.strip() not in env_vars:
                            lines.append(line)
                    elif not line or line.startswith('#'):
                        lines.append(line)
        
        # 添加新的环境变量
        for key, value in env_vars.items():
            lines.append(f"{key}={value}")
        
        with open(ENV_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        
        # 设置文件权限
        ENV_FILE.chmod(0o600)
        
    except Exception as e:
        print(f"❌ 写入.env文件失败: {e}")
        raise


def get_refresh_token() -> str:
    """获取refresh token"""
    # 1. 优先从系统环境变量获取
    if token := os.getenv("PIXIV_REFRESH_TOKEN"):
        return token.strip()
    
    # 2. 从.env文件获取
    env_vars = read_env_file()
    if "PIXIV_REFRESH_TOKEN" in env_vars:
        return env_vars["PIXIV_REFRESH_TOKEN"].strip()
    
    
    raise ValueError("未找到Pixiv refresh token")


def setup_token_file(token: str) -> None:
    """设置token到.env文件"""
    env_vars = {"PIXIV_REFRESH_TOKEN": token.strip()}
    write_env_file(env_vars)
    print(f"✅ Token已保存到: {ENV_FILE}")
    print(f"💡 环境变量格式: PIXIV_REFRESH_TOKEN={token.strip()[:20]}...")


def validate_token_format(token: str) -> bool:
    """验证token格式（基本检查）"""
    if not token or len(token) < 20:
        return False
    # 基本的token格式检查
    return True


def clear_saved_credentials() -> None:
    """清除保存的凭据"""
    try:
        # 清除.env文件中的token
        if ENV_FILE.exists():
            env_vars = read_env_file()
            if "PIXIV_REFRESH_TOKEN" in env_vars:
                del env_vars["PIXIV_REFRESH_TOKEN"]
                write_env_file(env_vars)
                print("✅ 已清除.env文件中的token")
        
    except Exception as e:
        print(f"⚠️  清除token失败: {e}")


def token_status() -> Dict[str, Any]:
    """检查token状态"""
    env_vars = read_env_file()
    
    status = {
        "env_token_exists": bool(os.getenv("PIXIV_REFRESH_TOKEN")),
        "env_file_token_exists": "PIXIV_REFRESH_TOKEN" in env_vars,
        "playwright_available": is_playwright_available(),
    }
    
    # 检查.env文件中的token
    if status["env_file_token_exists"]:
        try:
            token = env_vars["PIXIV_REFRESH_TOKEN"]
            status["env_file_token_valid"] = validate_token_format(token)
            status["env_file_token_length"] = len(token)
        except:
            status["env_file_token_valid"] = False
    
    
    return status