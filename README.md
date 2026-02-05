# HBUT 教务助手小程序 (HBUT MiniApp)

这是一个基于微信小程序 + Python Serverless 后端的教务查询工具，专为湖北工业大学 (HBUT) 学生设计。支持查询课表、成绩、GPA 排名等功能。

## 🚀 项目特色
*   **抗封锁设计**：后端部署在阿里云函数计算 (FC)，利用云厂商海量动态IP池，有效防止因高频访问教务系统导致的IP封禁。
*   **无状态架构**：后端不依赖数据库或 Redis，Session 信息通过 AES 加密存储在 Token 中，无需维护数据库服务器，零成本维护。
*   **自动识别验证码**：集成 `ddddocr` 深度学习模型，自动识别登录验证码，失败时自动回退到手动输入模式。

## 🛠 架构说明
*   **前端 (Frontend)**: 微信小程序 (原生开发)
    *   目录: `wxxcx/`
    *   主要功能: 用户交互、数据渲染、本地 Token 存储。
*   **后端 (Backend)**: Python FastAPI
    *   目录: `backend/`
    *   主要功能: 模拟登录教务系统、爬取 HTML/JSON 数据、解析并没有结构化数据。
    *   **核心逻辑**: `backend/main.py`

## 📦 部署指南

### 后端部署 (阿里云函数计算)
详细步骤请参阅项目根目录下的 [FC_Deploy_Guide.md](./FC_Deploy_Guide.md)。

简述：
1.  修改 `backend/main.py` 中的 `AES_SECRET_KEY` 环境变量（可选）。
2.  将 `backend` 目录下所有文件打包为 `code.zip`。
3.  在阿里云 FC控制台 创建 **Python 3.10** 函数，上传代码。
4.  在 WebIDE 中执行 `pip install -r requirements.txt -t .` 安装依赖。
    *   *注意：必须使用 `ddddocr==1.4.11` 以兼容 Serverless 环境。*
5.  获取公网访问地址。

### 前端配置
1.  打开 `wxxcx/utils/config.js`。
2.  将 `BASE_URL` 修改为你部署好的云函数公网地址。
    ```javascript
    const config = {
      BASE_URL: "https://你的云函数地址.fcapp.run"
    };
    ```
3.  在微信小程序后台添加 request 合法域名。

## 📝 常见问题 (FAQ)

**Q: 登录失败，提示 400 Bad Request？**  
A: 通常是因为云函数触发器开启了“需要认证”。请在阿里云控制台 -> 触发器配置中，将认证方式改为**“无需认证”**。

**Q: 报错 `ImportError: cannot import name 'DdddOcr'`？**  
A: `ddddocr` 最新版与云环境不兼容。请确保 `requirements.txt` 中指定了 `ddddocr==1.4.11`，并彻底清理旧依赖后重新安装。

**Q: 需要购买 Redis 吗？**  
A: 不需要。本项目采用 Token 加密存储状态的方案，完全免费且无状态。

## 📄 许可证
MIT License
