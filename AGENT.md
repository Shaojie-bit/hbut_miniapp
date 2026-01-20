# AGENT.md - AI 助手工作指南

本文档用于指导 AI 助手理解和维护 HBUT 教务微信小程序项目。

---

## 1. 项目核心目标

为湖北工业大学学生提供移动端教务查询服务，核心功能：
- **自动登录** - OCR 识别验证码，失败后回退手动输入
- **防封禁代理** - 通过 Cloudflare Workers 隧道代理访问教务系统，隐藏真实 IP
- **成绩查询** - 按学期分组，支持离线缓存
- **课表查看** - 周视图，支持课程合并显示
- **排名查询** - GPA、专业/班级排名

---

## 2. 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **后端** | Python 3.8+, FastAPI | `backend/cjcx+pm.py` |
| **代理** | Cloudflare Workers | 负责转发请求，解决 IP 封禁问题 (Tunnel Mode) |
| **OCR** | ddddocr | 验证码自动识别 |
| **爬虫** | requests, BeautifulSoup4 | 教务系统数据抓取 |
| **加密** | PyCryptodome (AES-CBC) | 密码加密 |
| **前端** | 微信小程序原生框架 | WXML/WXSS/JS |

---

## 3. 项目目录结构

```
hbut/
├── backend/                      # 【后端】
│   ├── cjcx+pm.py              # 主程序 (所有 API 在此)
│   ├── requirements.txt         # Python 依赖
│   └── nginx-hbut.conf          # Nginx 配置示例
│
├── workers/                      # 【Cloudflare Workers】
│   └── proxy.js                 # 代理脚本 (部署到 Cloudflare)
│
├── wxxcx/                       # 【微信小程序前端】
│   ├── app.js                   # 入口，globalData 定义
│   ├── app.json                 # 页面注册 + TabBar 配置
│   ├── app.wxss                 # 全局 CSS 变量
│   ├── utils/
│   │   └── config.js            # BASE_URL 配置 (指向你的 Python 后端)
│   ├── pages/
│   │   ├── login/               # 登录页 (OCR 自动 + 手动回退)
│   │   ├── index/               # 成绩页 (排名卡片 + 学期分组)
│   │   └── schedule/            # 课表页 (周视图 + 课程合并)
│   └── assets/                  # Tab 图标
```

---

## 4. 编码风格与模式

### 后端 (Python/FastAPI)

- **网络架构**: Python 后端不直接访问学校服务器，而是通过 Cloudflare Worker 代理。
  ```python
  CF_PROXY_URL = "https://hbut-worker.zmj888.asia/"
  # 请求流程: Python -> Cloudflare Worker -> School Server
  ```
- **请求封装**: 使用 `cf_request` 函数统一发送代理请求，自动处理 `headers_list` (解决 Set-Cookie 覆盖问题) 和 `body_base64` (处理验证码图片)。
- **会话管理**: 使用 SQLite (`sessions.db`) 持久化存储用户 Session 和验证码会话。
- **OCR 逻辑**: 优先自动识别，连续失败3次后，生成新的验证码会话供前端手动输入。

### 前端 (微信小程序)

- **API 调用**: Promise 封装 `wx.request`
- **状态管理**: 页面级 `data` + `wx.setStorageSync` 持久化
- **登录交互**: 默认尝试自动登录 -> 失败提示并显示验证码 -> 用户手动输入 -> 重新提交。

---

## 5. 特殊规则 ⚠️

### 必须遵守

1. **登录返回码**:
   - `200` = 成功
   - `429` = OCR 失败，需手动输入验证码 (会自动返回新验证码图片)
   - `401` = 密码错误或会话过期
   - `403` = 请求过于频繁 (限流)

2. **代理通信协议**:
   - Worker 返回的数据必须包含 `headers_list` 数组，而不是单一的 headers 对象，以防止 Set-Cookie 丢失。
   - 二进制数据 (验证码) 必须通过 `body_base64` 字段返回。

3. **URL 编码**:
   - 向 Worker 发送 POST 时的 `body` 必须使用 `urllib.parse.urlencode` 编码，防止 `+` 号等特殊字符被吞。

### 禁止事项

- ❌ 不要跳过 Cloudflare Worker 直接访问学校 IP (会被封禁)。
- ❌ 不要修改 `cf_request` 中的 Cookie 处理逻辑，除非你通过了完整测试。

---

## 6. 常见问题排查

| 现象 | 原因 | 解决 |
|------|------|------|
| 验证码一直提示错误 | Set-Cookie 被覆盖或丢失 | 检查 Worker 是否返回 `headers_list`，后端是否正确解析 |
| 登录返回 404 | Worker 路由没配对 | 检查 Cloudflare Custom Domain 和 Routes |
| 课表/成绩为空 | 代理网络超时或学校系统维护 | 检查 Cloudflare 日志或学校官网状态 |

---

## 7. 关键文件速查

| 需求 | 文件 |
|------|------|
| 修改代理地址 | `backend/cjcx+pm.py` (CF_PROXY_URL) |
| 修改 API 地址 | `wxxcx/utils/config.js` |
| 修改代理脚本 | `workers/proxy.js` |
| 部署指南 | `backend/部署指南.md` |
