# 阿里云函数计算 (FC) 部署指南

本指南将指导你将改造后的无状态后端部署到阿里云函数计算（Function Compute 3.0）。

## 1. 准备工作

### 1.1 重命名文件 (建议)
为了方便命令执行，建议将 `backend/cjcx+pm.py` 重命名为 `main.py`。
*(以下步骤默认你已经重命名，如果未重命名，请将 `main:app` 替换为 `cjcx+pm:app`)*

### 1.2 创建启动脚本 (bootstrap)
在 `backend` 目录下新建一个名为 `bootstrap` 的文件（**没有后缀名**），内容如下：

```bash
#!/bin/bash
export PORT=9000
python3 -m uvicorn main:app --host 0.0.0.0 --port $PORT
```
*注意：如果是 Windows，请确保该文件的换行符为 LF (Unix风格)，否则运行会报错。*

### 1.3 打包代码
将 `backend` 目录下的所有文件（包括 `main.py`, `requirements.txt`, `bootstrap`）压缩为一个 `code.zip` 压缩包。
**注意**：不要包含文件夹一层，直接选中文件压缩。

## 2. 创建云函数

1.  登录 [阿里云函数计算控制台](https://fcnext.console.aliyun.com/)。
2.  点击 **"创建函数"**。
3.  选择 **"Web 函数"**。
4.  **基本设置**:
    -   函数名称：`hbut-backend` (自定义)
    -   运行环境：`Python 3.10` (建议 3.9 或 3.10)
5.  **代码配置**:
    -   上传方式：**通过 ZIP 包上传**。
    -   上传刚才打包的 `code.zip`。
6.  **启动命令**:
    -   如果你上传了 `bootstrap` 文件，这里可以留空，或者填写：`./bootstrap`
    -   或者直接填写自定义命令：`python3 -m uvicorn main:app --host 0.0.0.0 --port 9000`
7.  **监听端口**: 设置为 `9000`。
8.  **高级配置** (可选但推荐):
    -   **环境变量**:
        -   `AES_SECRET_KEY`: 设置一个复杂的随机字符串（32位以上），用于加密 Token。
    -   **规格**: 建议 `512MB` 或 `1GB` 内存（OCR 库比较吃内存）。
    -   **超时时间**: 建议设置 `60秒` 或更长（教务系统有时候响应慢）。
9.  点击 **"部署"**。

## 3. 依赖安装

由于 `ddddocr` 依赖比较复查，建议使用层 (Layer) 或在在线 IDE 中安装。

**推荐方式：在线安装依赖**
1.  函数创建成功后，进入 **"代码"** 标签页。
2.  点击 **"WebIDE"** 打开在线编辑器。
3.  在 WebIDE 的终端（Terminal）中运行：
    ```bash
    pip install -r requirements.txt -t .
    ```
4.  安装完成后，点击 WebIDE 右上角的 **"部署代码"**。

*注意：`ddddocr` 可能包含二进制文件，如果在 Windows 打包再上传可能导致 Linux 环境下不可用。强烈建议在阿里云 WebIDE 中执行 pip install。*

## 4. 获取公网地址

1.  在 **"触发器管理"** 标签页。
2.  你会看到一个 **"公网访问地址"**。
3.  复制这个地址（例如 `https://hbut-backend-xxxx.cn-hangzhou.fcapp.run`）。

## 5. 小程序配置

1.  打开本地的 `wxxcx/utils/config.js`。
2.  修改 `BASE_URL` 为刚才获取的云函数公网地址。
    ```javascript
    const config = {
        BASE_URL: "https://hbut-backend-xxxx.cn-hangzhou.fcapp.run"
    };
    ```
3.  在微信小程序后台（mp.weixin.qq.com） -> **开发管理** -> **开发设置** -> **服务器域名** 中，将该域名添加到 `request合法域名` 列表中。

## 6. 测试

1.  在微信开发者工具中重新编译。
2.  尝试登录、查询课表。
3.  如果成功，恭喜你！现在你的后端已经拥有海量 IP 池了。
