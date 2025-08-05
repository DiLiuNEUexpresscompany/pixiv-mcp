# Pixiv MCP Server

一个让客户端（Cherry Studio，Claude Desktop）直接访问Pixiv的MCP服务器。支持搜索插画、获取排行榜、下载图片、阅读小说等功能。

## 功能特性

- **搜索插画**: 支持关键词搜索，多种排序方式
- **排行榜**: 日榜、周榜、月榜，支持多种分类
- **用户信息**: 获取用户详情、作品列表、关注关系
- **小说功能**: 搜索小说、获取正文内容
- **下载功能**: 支持不同质量图片下载
- **流式响应**: HTTP服务器支持实时数据流
- **双API架构**: 标准API + 绕过API，提高访问成功率

## 快速开始

### 1. 安装依赖

```bash
# 克隆项目
git clone https://github.com/your-username/pixiv-mcp.git
cd pixiv-mcp

# 安装依赖
pip install -e .
```

### 2. 配置Token

获取Pixiv refresh token并配置：

```bash
# 获取token（推荐）
python src/token_manager.py
# 选择1 交互式登录 (推荐)
# 或手动设置环境变量
export PIXIV_REFRESH_TOKEN="your_refresh_token_here"
```

### 3. 启动服务器

**HTTP服务器（推荐）**：
```bash
python start_http_server.py \
  --host 0.0.0.0 \
  --port 8080 \
  --workers 1 \
  --reload \
  --log-level info
```

### 4. 在Claude Desktop中使用

更新你的 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "pixiv": {
      "command": "python",
      "args": ["start_http_server.py"],
      "env": {
        "PIXIV_REFRESH_TOKEN": "your_token_here"
      }
    }
  }
}
```

## 使用示例

在Cherry Studio中，你可以直接说：

- "搜索初音未来的插画"
- "获取今日排行榜前10名"
- "下载插画ID 59580629"
- "搜索用户'wlop'的作品"
- "获取小说ID 12345的正文内容"

## 主要工具

### 搜索相关
- `pixiv_search_illust` - 搜索插画
- `pixiv_search_novel` - 搜索小说  
- `pixiv_search_user` - 搜索用户

### 排行榜
- `pixiv_illust_ranking` - 插画排行榜
- `pixiv_novel_ranking` - 小说排行榜

### 详情获取
- `pixiv_illust_detail` - 插画详情
- `pixiv_user_detail` - 用户详情
- `pixiv_novel_detail` - 小说详情
- `novel_text` - 小说正文 （如果无法查看小说正文使用fork安装修改过的 [pixivpy](https://github.com/DiLiuNEUexpresscompany/pixivpy)

### 下载功能
- `pixiv_download_illust` - 下载插画

### 用户作品
- `pixiv_user_illusts` - 用户插画列表
- `pixiv_user_novels` - 用户小说列表

## 网络优化

项目采用双API架构来解决网络访问问题：

- **标准API**: 用于大部分功能
- **绕过API**: 专门用于小说正文获取，绕过GFW和Cloudflare限制


## 开发

### 项目结构
```
pixiv-mcp/
├── src/                    # 核心代码
│   ├── tools.py           # 工具实现
│   ├── http_server.py     # HTTP服务器
│   ├── auth.py            # 认证管理
│   └── token_manager.py   # Token管理
├── examples/              # 使用示例
├── config/               # 配置文件
└── test/                 # 测试文件
```

### 运行测试
```bash
# API基础功能测试
python examples/basic_usage.py
```

## 故障排除

### 常见问题

1. **认证失败**
   - 检查refresh token是否有效
   - 运行 `python -m src.token_manager status` 检查状态

2. **网络连接问题**
   - 尝试配置代理


### 日志查看
```bash
# 启用详细日志
python start_http_server.py --log-level debug
```

## 贡献

欢迎提交Issue和Pull Request！
