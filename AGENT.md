# AGENT.md - AI 助手工作指南

本文档用于指导 AI 助手理解和维护 HBUT 教务微信小程序项目。

---

## 1. 项目核心目标

为湖北工业大学学生提供移动端教务查询服务，核心功能：
- **自动登录** - OCR 识别验证码，失败后回退手动输入
- **成绩查询** - 按学期分组，支持离线缓存
- **课表查看** - 周视图，支持课程合并显示
- **排名查询** - GPA、专业/班级排名

---

## 2. 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **后端** | Python 3.8+, FastAPI | `cursor/cjcx+pm.py` |
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
├── wxxcx/                       # 【微信小程序前端】
│   ├── app.js                   # 入口，globalData 定义
│   ├── app.json                 # 页面注册 + TabBar 配置
│   ├── app.wxss                 # 全局 CSS 变量
│   ├── utils/
│   │   └── config.js            # BASE_URL 配置 (重要!)
│   ├── pages/
│   │   ├── login/               # 登录页 (OCR 自动 + 手动回退)
│   │   ├── index/               # 成绩页 (排名卡片 + 学期分组)
│   │   └── schedule/            # 课表页 (周视图 + 课程合并)
│   └── assets/                  # Tab 图标
│
└── 没用了/                      # 【已弃用的调试文件】
    ├── cjcx.py                  # 旧版后端 (仅供参考)
    └── index.html               # 本地调试 HTML
```

---

## 4. 编码风格与模式

### 后端 (Python/FastAPI)

- **会话管理**: 使用内存字典 `FAKE_REDIS` 存储 session
  ```python
  FAKE_REDIS[f"user:{token}"] = {"cookies": ..., "xhid": ..., "stu_id": ...}
  ```
- **API 响应格式**: 统一返回 `{"code": 200/401/500, "data": ..., "msg": ...}`
- **错误处理**: 直接返回错误码，不抛异常
  ```python
  if not user_data: return {"code": 401, "msg": "请重新登录"}
  ```
- **HTML 解析**: `BeautifulSoup` + `.find()` 方式提取字段

### 前端 (微信小程序)

- **API 调用**: Promise 封装 `wx.request`
  ```javascript
  const res = await new Promise((resolve, reject) => {
      wx.request({ url, method, data, success: resolve, fail: reject });
  });
  ```
- **状态管理**: 页面级 `data` + `wx.setStorageSync` 持久化
- **Token 存储**: `wx.getStorageSync('user_token')`
- **页面跳转**: TabBar 页用 `wx.switchTab`，非 Tab 页用 `wx.redirectTo`

### 课程合并算法

后端和前端各有一次合并：
1. **后端合并** (`cjcx+pm.py`): 按 `raw_zc` (周次描述) 合并
2. **前端合并** (`schedule.js`): 按当前周筛选后再合并（解决不同周次范围的课程）

---

## 5. 特殊规则 ⚠️

### 必须遵守

1. **登录返回码**:
   - `200` = 成功
   - `429` = OCR 失败，需手动输入验证码
   - `401` = 密码错误或会话过期

2. **成绩字段名**: 后端必须返回 `course_name`，前端 `index.wxml` 依赖此字段

3. **课表 djs 字段**: 教务系统返回的 `djs` 是**结束节次**，不是持续时长
   ```python
   step_span = max(1, end_sec - start_sec + 1)  # 正确
   step = djs  # 错误!
   ```

4. **xhid 提取**: 必须访问 `?xnxq=2025-2026-1` 参数才能获取 xhid

### 禁止事项

- ❌ 不要使用 `wx.reLaunch` 跳转到 TabBar 页面（会报错）
- ❌ 不要在后端存储明文密码
- ❌ 不要修改 `FAKE_REDIS` 的 key 格式 (`user:xxx`, `session:xxx`)

### 推荐

- ✅ 修改后端后务必重启服务
- ✅ 前端调试时清除小程序缓存
- ✅ 生产环境将 `FAKE_REDIS` 替换为 Redis

---

## 6. 常见问题排查

| 现象 | 原因 | 解决 |
|------|------|------|
| 课表显示"登录过期" | `xhid` 未正确提取 | 检查 `TIMETABLE_PAGE_URL` 和参数 |
| 成绩无课程名 | 后端返回 `name` 而非 `course_name` | 修改后端字段名 |
| 登录后跳回登录页 | Token 未保存或被清除 | 检查 `wx.setStorageSync` |
| 课程卡片未合并 | 前端合并算法缺失 | 检查 `filterCoursesForWeek` |

---

## 7. 关键文件速查

| 需求 | 文件 |
|------|------|
| 修改 API 地址 | `wxxcx/utils/config.js` |
| 添加新 API | `cursor/cjcx+pm.py` |
| 修改登录逻辑 | `wxxcx/pages/login/login.js` |
| 修改课表 UI | `wxxcx/pages/schedule/schedule.wxml` |
| 修改成绩 UI | `wxxcx/pages/index/index.wxml` |
| 修改 Tab 配置 | `wxxcx/app.json` |
