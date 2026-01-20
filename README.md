# HBUT 教务微信小程序

湖北工业大学教务系统微信小程序，支持成绩查询、课表查看和排名统计功能。

> **🌟 特别特性**: 内置 Cloudflare 隧道代理方案，彻底解决学校 IP 封禁问题，实现极速稳定的访问体验。

## ✨ 功能特性

- 🛡️ **防封禁** - 采用 Cloudflare Workers 作为出站代理，隐藏服务器真实 IP
- 🔐 **智能登录** - OCR 自动识别验证码，高准确率，失败自动降级手动模式
- 📊 **成绩查询** - 按学期分组展示，支持离线缓存
- 📅 **课表查看** - 周视图课表，支持学期/周次切换
- 🏆 **排名查询** - GPA、专业排名、班级排名一目了然
- 💾 **数据缓存** - 登录凭证和成绩本地缓存，快速加载

## 📁 项目结构

```
hbut/
├── backend/                    # 后端服务
│   ├── cjcx+pm.py            # FastAPI 后端主程序
│   ├── requirements.txt       # Python 依赖
│   └── sessions.db            # SQLite 会话存储 (自动生成)
│
├── workers/                    # 代理服务
│   └── proxy.js               # Cloudflare Worker 脚本
│
└── wxxcx/                     # 微信小程序前端
    ├── app.js                 # 小程序入口
    ├── utils/config.js        # API 地址配置
    └── pages/                 # 各页面源码
```

## 🚀 快速开始

### 1. 部署 Cloudflare Worker (关键)

为了防止 IP 被封，我们首先部署代理服务：
1.  注册 Cloudflare 账号，创建一个新的 Worker。
2.  将 `workers/proxy.js` 的内容复制到 Worker 中并保存。
3.  **强烈建议**: 绑定自定义域名 (如 `hbut-worker.yourdomain.com`) 并在 Routes 中配置路由。

### 2. 后端部署

1.  **安装依赖**
    ```bash
    cd backend
    pip install -r requirements.txt
    ```

2.  **配置代理**
    打开 `backend/cjcx+pm.py`，修改 `CF_PROXY_URL`：
    ```python
    CF_PROXY_URL = "https://hbut-worker.yourdomain.com/"
    ```

3.  **运行服务**
    ```bash
    python cjcx+pm.py
    ```
    服务将在 `http://0.0.0.0:8000` 启动

### 3. 小程序配置

1.  **修改 API 地址**  
    编辑 `wxxcx/utils/config.js`：
    ```javascript
    module.exports = {
      BASE_URL: 'https://your-backend-server.com'  // 你的 Python 后端地址
    };
    ```

2.  **导入开发工具**  
    使用微信开发者工具导入 `wxxcx` 目录即可运行。

## 🔧 API 接口 (后端 -> 代理 -> 学校)

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/captcha` | GET | 手动获取验证码 (走代理) |
| `/api/login` | POST | 登录 (优先 OCR，支持重试) |
| `/api/grades` | POST | 查询成绩 |
| `/api/timetable` | POST | 查询课表 |

## 📋 技术栈

- **基础设施**: Cloudflare Workers (Tunnel Proxy)
- **后端**: Python 3.8+, FastAPI, ddddocr, SQLite
- **前端**: 微信小程序原生框架
- **加密**: AES-CBC + Base64

## ⚠️ 注意事项

1. **Cloudflare 配置**: 务必确保 Worker 的 Custom Domain 和 Routes 配置正确，否则会报 404。
2. **生产环境**: 建议使用 Nginx 反向代理 Python 后端，并配置 SSL 证书。
3. **数据安全**: 本项目仅供学习交流，不保存任何用户敏感数据（密码仅在内存中转发）。

## 📄 开源协议

MIT License
