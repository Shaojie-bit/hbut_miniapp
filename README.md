# HBUT 教务微信小程序

湖北工业大学教务系统微信小程序，支持成绩查询、课表查看和排名统计功能。

## ✨ 功能特性

- 🔐 **智能登录** - OCR 自动识别验证码，3次失败后手动输入
- 📊 **成绩查询** - 按学期分组展示，支持离线缓存
- 📅 **课表查看** - 周视图课表，支持学期/周次切换
- 🏆 **排名查询** - GPA、专业排名、班级排名一目了然
- 💾 **数据缓存** - 登录凭证和成绩本地缓存，快速加载

## 📁 项目结构

```
hbut/
├── cursor/                    # 后端服务
│   ├── cjcx+pm.py            # FastAPI 后端主程序
│   ├── requirements.txt       # Python 依赖
│   └── 部署指南.md            # 服务器部署文档
│
└── wxxcx/                     # 微信小程序前端
    ├── app.js                 # 小程序入口
    ├── app.json               # 全局配置 (Tab Bar)
    ├── app.wxss               # 全局样式
    ├── utils/
    │   └── config.js          # API 地址配置
    ├── pages/
    │   ├── login/             # 登录页
    │   ├── index/             # 成绩页
    │   └── schedule/          # 课表页
    └── assets/                # 图标资源
```

## 🚀 快速开始

### 后端部署

1. **安装依赖**
   ```bash
   cd cursor
   pip install -r requirements.txt
   ```

2. **运行服务**
   ```bash
   python cjcx+pm.py
   ```
   服务将在 `http://0.0.0.0:8000` 启动

3. **生产部署** - 参考 `部署指南.md`

### 小程序配置

1. **修改 API 地址**  
   编辑 `wxxcx/utils/config.js`：
   ```javascript
   module.exports = {
     BASE_URL: 'https://your-domain.com'  // 替换为你的服务器地址
   };
   ```

2. **导入微信开发者工具**  
   打开微信开发者工具，导入 `wxxcx` 目录

3. **配置服务器域名**  
   在小程序后台「开发设置」中添加服务器域名

## 🔧 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/captcha` | GET | 获取验证码 |
| `/api/login` | POST | 登录 (支持 OCR 自动登录) |
| `/api/grades` | POST | 查询成绩 |
| `/api/timetable` | POST | 查询课表 |
| `/api/rankings` | POST | 查询排名 |

## 📋 技术栈

- **后端**: Python 3.8+, FastAPI, ddddocr, BeautifulSoup4
- **前端**: 微信小程序原生框架 (WXML/WXSS/JS)
- **加密**: AES-CBC (密码加密)

## ⚠️ 注意事项

1. 本项目仅供学习交流使用
2. 请勿用于任何商业用途
3. 登录凭证仅存储于本地，后端不保存密码
4. 生产环境建议使用 Redis 替代内存缓存

## 📄 开源协议

MIT License
