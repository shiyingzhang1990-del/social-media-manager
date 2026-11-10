# Social Media Manager · 社交媒体统一管理平台

支持微博、微信、抖音、小红书、B站 五个平台，每个平台最多管理 **15个账号**。

## 启动

```bash
cd social-media-manager
bash start.sh
```

打开浏览器访问 **http://127.0.0.1:8765**

## 技术架构

```
backend/          ← FastAPI 后端
  main.py           · 应用入口，路由挂载
  config.py         · 配置
  database.py       · SQLAlchemy + SQLite
  platforms/        · 各平台集成模块
    base.py           · 抽象基类
    weibo.py          · 微博 (Cookie认证)
    wechat.py         · 微信/公众号 (OAuth2)
    douyin.py         · 抖音 (Open API)
    xiaohongshu.py    · 小红书 (Cookie认证)
    bilibili.py       · B站 (Cookie认证)
  api/              · REST API 路由
    accounts.py       · 账号管理
    content.py        · 内容管理 & 发布
    dashboard.py      · 统计数据
  scheduler/        · 定时发布引擎 (APScheduler)
frontend/         ← 纯前端 SPA
  index.html
  css/style.css
  js/               · API 客户端 & 6个视图组件
data/             ← SQLite 数据库 (自动创建)
```

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/health | 健康检查 |
| GET | /api/accounts/platforms | 列出支持的平台 |
| GET/POST | /api/accounts | 列表/创建账号 |
| GET/PUT/DELETE | /api/accounts/{id} | 单个账号 CRUD |
| POST | /api/accounts/{id}/verify | 验证账号有效性 |
| GET/POST | /api/content | 列表/创建内容 |
| POST | /api/content/{id}/publish | 发布内容 |
| POST | /api/content/{id}/schedule | 定时发布 |
| GET | /api/content/schedules/all | 查看定时任务 |
| POST | /api/content/upload | 上传媒体文件 |
| GET | /api/dashboard/stats | 仪表盘统计 |
| GET | /api/dashboard/recent-activity | 最近动态 |

## 各平台认证方式

| 平台 | 认证方式 | 需要提供 |
|------|---------|---------|
| 微博 | Cookie + UID | 浏览器 Cookie (JSON), 用户UID |
| 微信 | OAuth2 App | AppID, AppSecret |
| 抖音 | Open API Token | OpenID, Access Token |
| 小红书 | Cookie | Cookie (JSON), 用户ID |
| B站 | Cookie + CSRF | Cookie (JSON), MID, bili_jct |

## 使用方法

1. 启动后打开 Web 面板
2. 在"账号管理"添加各平台账号凭证
3. 在"内容管理"创建内容或上传媒体
4. 在"发布"页面选择内容和发布目标，立即或定时发布
5. 查看"定时任务"和"发布日志"追踪结果
