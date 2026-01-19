# Gunicorn 配置文件
# 用于宝塔面板 Python 项目管理器

import multiprocessing

# 服务器socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker 进程
workers = multiprocessing.cpu_count() * 2 + 1  # 根据 CPU 核心数自动设置
worker_class = "uvicorn.workers.UvicornWorker"  # 使用 uvicorn worker
worker_connections = 1000
timeout = 60
keepalive = 2

# 日志
accesslog = "-"  # 输出到标准输出
errorlog = "-"   # 输出到标准错误
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# 进程命名
proc_name = "hbut-api"

# 服务器钩子
def on_starting(server):
    server.log.info("HBUT API 服务正在启动...")

def on_reload(server):
    server.log.info("HBUT API 服务正在重新加载...")

def when_ready(server):
    server.log.info("HBUT API 服务已就绪，监听在 %s", server.address)

def on_exit(server):
    server.log.info("HBUT API 服务正在关闭...")

