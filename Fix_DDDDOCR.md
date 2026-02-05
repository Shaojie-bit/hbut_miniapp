# 解决 `ddddocr` 在阿里云函数计算各种 Import Error 的方案

## 问题原因
`ddddocr` 依赖 `onnxruntime`，而标准版的 `onnxruntime` 包含的 C++ 动态链接库 (`.so` 文件) 需要依赖系统底层的 `glibc` 等库。阿里云函数计算（以及 AWS Lambda）的运行环境（通常是精简版 Linux）可能缺失某些底层依赖，或者 `onnxruntime` 的版本与该环境不兼容，导致 `ImportError: cannot import name 'DdddOcr'` 或 `OSError`。

## 解决方案：降级 `ddddocr` 并固定版本

经过社区验证，在 Serverless 环境下，使用 **旧版本** 的 `ddddocr` 往往更稳定。

### 1. 修改 `requirements.txt`
请将 `ddddocr` 修改为指定版本 `1.4.11` (或者更早的 1.4.7)，并尝试移除 explicit 的 `Pillow` 依赖（ddddocr 会自动安装适合它的 Pillow）。

**建议的 `requirements.txt` 内容：**
```text
fastapi
uvicorn
requests
beautifulsoup4
ddddocr==1.4.11
pycryptodome
pydantic
python-multipart
```

### 2. 清理并重新安装
由于之前的安装可能残留了不兼容的二进制文件，必须彻底清理。

**在阿里云 WebIDE 终端执行以下步骤：**

1.  **清理旧环境**：
    由于我们无法直接删除系统目录，但可以删除当前目录下的 `ddddocr` 和 `onnxruntime` 相关文件夹。
    ```bash
    rm -rf ddddocr* onnxruntime* Pillow* PIL*
    ```

2.  **强制重新安装**：
    ```bash
    pip install -r requirements.txt -t . --upgrade --force-reinstall
    ```

3.  **检查安装结果**：
    安装完成后，在终端里尝试运行一下 python 验证是否报错：
    ```bash
    python3 -c "import ddddocr; print('Success')"
    ```
    如果输出了 `Success`，说明修复成功。

4.  **重新部署**：
    点击右上角 **"部署代码"**。

## 备选方案：使用 `ddddocr` 轻量版
如果上述方法仍然不行，可以尝试安装 `ddddocr` 的轻量化分支（如果有）或者直接改用无 OCR 版本的逻辑先跑通流程（屏蔽 OCR 相关代码），确认其他部分正常。
