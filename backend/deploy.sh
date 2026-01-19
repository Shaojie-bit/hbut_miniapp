#!/bin/bash
# HBUT API 快速部署脚本
# 使用方法: bash deploy.sh

echo "=========================================="
echo "HBUT 教务系统 API 部署脚本"
echo "=========================================="

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

# 项目路径
PROJECT_DIR="/www/wwwroot/hbut.zmj888.asia"
SERVICE_FILE="/etc/systemd/system/hbut-api.service"

# 检测 Python 路径
echo "正在检测 Python 路径..."
if [ -f "/www/server/python/py3.11/bin/python3" ]; then
    PYTHON_PATH="/www/server/python/py3.11/bin"
elif [ -f "/usr/bin/python3" ]; then
    PYTHON_PATH="/usr/bin"
else
    echo "错误: 未找到 Python3，请先安装 Python"
    exit 1
fi

echo "Python 路径: $PYTHON_PATH"

# 检查项目目录
if [ ! -d "$PROJECT_DIR" ]; then
    echo "错误: 项目目录不存在: $PROJECT_DIR"
    echo "请先在宝塔面板创建网站"
    exit 1
fi

# 进入项目目录
cd "$PROJECT_DIR" || exit 1

# 检查必要文件
if [ ! -f "cjcx+pm.py" ]; then
    echo "错误: 未找到 cjcx+pm.py"
    exit 1
fi

if [ ! -f "requirements.txt" ]; then
    echo "错误: 未找到 requirements.txt"
    exit 1
fi

# 安装依赖
echo "正在安装 Python 依赖..."
"$PYTHON_PATH/pip3" install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "错误: 依赖安装失败"
    exit 1
fi

# 创建 systemd 服务文件
echo "正在创建 systemd 服务文件..."
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=HBUT 教务系统 API 服务
After=network.target

[Service]
Type=simple
User=www
Group=www
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PYTHON_PATH:/usr/local/bin:/usr/bin:/bin"
ExecStart=$PYTHON_PATH/uvicorn cjcx+pm:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 设置文件权限
chown www:www "$PROJECT_DIR" -R
chmod 755 "$PROJECT_DIR" -R

# 重新加载 systemd
echo "正在重新加载 systemd..."
systemctl daemon-reload

# 启动服务
echo "正在启动服务..."
systemctl enable hbut-api
systemctl start hbut-api

# 等待服务启动
sleep 3

# 检查服务状态
if systemctl is-active --quiet hbut-api; then
    echo "=========================================="
    echo "✅ 部署成功！"
    echo "=========================================="
    echo "服务状态:"
    systemctl status hbut-api --no-pager -l
    echo ""
    echo "常用命令:"
    echo "  查看状态: sudo systemctl status hbut-api"
    echo "  查看日志: sudo journalctl -u hbut-api -f"
    echo "  重启服务: sudo systemctl restart hbut-api"
    echo "  停止服务: sudo systemctl stop hbut-api"
    echo ""
    echo "请确保已在宝塔面板配置 Nginx 反向代理！"
else
    echo "=========================================="
    echo "❌ 服务启动失败"
    echo "=========================================="
    echo "请查看日志: sudo journalctl -u hbut-api -n 50"
    exit 1
fi

