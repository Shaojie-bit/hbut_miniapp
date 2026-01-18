# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
import uuid
import json
import random
import string
import time
import traceback
import re
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hbut_api.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="HBUT 教务小程序后端")

# 静态文件服务（用于提供前端 HTML）
# 如果 HTML 文件在同一目录下，则挂载静态文件
static_dir = os.path.dirname(os.path.abspath(__file__))
html_file = os.path.join(static_dir, "debug+pm.html")
if os.path.exists(html_file):
    @app.get("/")
    def index_page():
        """返回前端页面"""
        return FileResponse(html_file)

# ================= 配置区域 =================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FAKE_REDIS = {}

# 关键 URL 配置
LOGIN_URL = "https://auth.hbut.edu.cn/authserver/login"
CAPTCHA_URL = "https://auth.hbut.edu.cn/authserver/getCaptcha.htl"
JW_HOME_URL = "https://hbut.jw.chaoxing.com/admin/login" 
GRADE_API_URL = "https://hbut.jw.chaoxing.com/admin/xsd/xsdcjcx/xsdQueryXscjList"
RANK_INFO_URL = "https://hbut.jw.chaoxing.com/admin/cjgl/xscjbbdy/printdgxscj"
RANK_PAGE_URL = "https://hbut.jw.chaoxing.com/admin/cjgl/xscjbbdy/getXscjpm"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": LOGIN_URL
}

KCXZ_MAP = {
    "44": "专业必修课", "11": "通识教育必修课", "12": "通识教育选修课",
    "31": "学科基础课", "40": "专业核心课", "45": "专业选修课",
    "50": "基础实践", "51": "专业实践", "52": "综合实践",
    "53": "其他实践", "54": "短学期实践", "99": "公共选修课",
    "32": "工程基础课", "98": "重修课", "43": "专业基础课",
    "16": "限定性选修课"
}

# ================= 数据模型 =================

class LoginRequest(BaseModel):
    token: str
    username: str
    password: str
    captcha: str

class TokenRequest(BaseModel):
    token: str

class RankingRequest(BaseModel):
    token: str
    username: str
    semester: str

# ================= 工具函数 =================

def encrypt_password(password: str, salt: str) -> str:
    try:
        random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=64))
        text = random_str + password
        key = salt.encode('utf-8')
        iv = ''.join(random.choices(string.ascii_letters + string.digits, k=16)).encode('utf-8')
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return base64.b64encode(cipher.encrypt(pad(text.encode('utf-8'), AES.block_size))).decode('utf-8')
    except Exception as e:
        logger.error(f"加密错误: {e}", exc_info=True)
        return None

# ================= API 接口 =================

@app.get("/")
def index():
    return {"msg": "HBUT API Service is running!"}

@app.get("/api/captcha")
def get_captcha():
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        resp = session.get(LOGIN_URL, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        execution_tag = soup.find('input', {'name': 'execution'})
        salt_tag = soup.find('input', {'id': 'pwdEncryptSalt'})
        lt_tag = soup.find('input', {'name': 'lt'})
        
        execution = execution_tag['value'] if execution_tag else ""
        salt = salt_tag['value'] if salt_tag else ""
        lt = lt_tag['value'] if lt_tag else ""

        timestamp = int(time.time() * 1000)
        captcha_resp = session.get(f"{CAPTCHA_URL}?{timestamp}", timeout=5)
        b64_img = base64.b64encode(captcha_resp.content).decode('utf-8')
        img_src = f"data:image/jpeg;base64,{b64_img}"

        temp_token = str(uuid.uuid4())
        session_data = {
            "cookies": session.cookies.get_dict(),
            "execution": execution,
            "salt": salt,
            "lt": lt
        }
        FAKE_REDIS[f"session:{temp_token}"] = session_data

        return {"code": 200, "data": {"token": temp_token, "image": img_src}}
    except Exception as e:
        logger.error(f"验证码获取错误: {e}", exc_info=True)
        return {"code": 500, "msg": "教务系统连接超时或异常"}

@app.post("/api/login")
def login(req: LoginRequest):
    raw_data = FAKE_REDIS.get(f"session:{req.token}")
    if not raw_data:
        return {"code": 400, "msg": "验证码过期，请刷新"}
    
    session = requests.Session()
    session.headers.update(HEADERS)
    session.cookies.update(raw_data['cookies'])
    
    encrypted_pwd = encrypt_password(req.password, raw_data['salt'])
    if not encrypted_pwd:
        return {"code": 500, "msg": "加密算法异常"}

    payload = {
        "username": req.username,
        "password": encrypted_pwd,
        "captcha": req.captcha,
        "_eventId": "submit",
        "cllt": "userNameLogin",
        "dllt": "generalLogin",
        "lt": raw_data['lt'],
        "execution": raw_data['execution']
    }

    try:
        login_resp = session.post(LOGIN_URL, data=payload, allow_redirects=False, timeout=15)
        
        if login_resp.status_code == 302:
            redirect_location = login_resp.headers.get("Location")
            logger.info(f"认证成功，重定向到: {redirect_location}")
            
            # 激活跨域 Session
            session.get(redirect_location, allow_redirects=True)
            session.get(JW_HOME_URL)
            
            user_token = str(uuid.uuid4())
            FAKE_REDIS[f"user:{user_token}"] = session.cookies.get_dict()
            
            if f"session:{req.token}" in FAKE_REDIS:
                del FAKE_REDIS[f"session:{req.token}"]

            return {"code": 200, "msg": "登录成功", "user_token": user_token}
        else:
            return {"code": 401, "msg": "账号或密码错误"}

    except Exception as e:
        logger.error(f"登录错误: {e}", exc_info=True)
        return {"code": 500, "msg": "登录过程发生网络错误"}

@app.post("/api/grades")
def query_grades(req: TokenRequest):
    user_token = req.token
    cookies = FAKE_REDIS.get(f"user:{user_token}")
    
    if not cookies:
        return {"code": 401, "msg": "登录已失效"}
    
    session = requests.Session()
    session.headers.update(HEADERS)
    session.cookies.update(cookies)
    
    # 强制设置 page.size 为 500，确保一次拉取所有成绩
    payload = {
        "fxbz": "0",
        "gridtype": "jqgrid",
        "page.pn": "1",
        "page.size": "500", 
        "sort": "xnxq",
        "order": "desc",
        "queryFields": "id,xnxq,kcmc,xf,kcxz,kclx,ksxs,kcgs,xdxz,kclb,cjfxms,zhcj,hdxf,tscjzwmc,sfbk,cjlrjsxm,kcsx,fxcj,dztmlfjcj,"
    }
    
    try:
        resp = session.post(GRADE_API_URL, data=payload, timeout=10)
        
        if "text/html" in resp.headers.get("Content-Type", ""):
            return {"code": 401, "msg": "会话已过期，请重新登录"}
            
        data_json = resp.json()
        raw_list = data_json.get("results", [])
        
        clean_grades = []
        for item in raw_list:
            kcxz_code = str(item.get("kcxz", ""))
            kcxz_name = KCXZ_MAP.get(kcxz_code, "其他课程")
            is_retake = (str(item.get("xdxz")) == "2")
            
            clean_grades.append({
                "semester": item.get("xnxq"),
                "course_name": item.get("kcmc"),
                "credit": item.get("xf"),
                "score": item.get("zhcj"),
                "type": kcxz_name,
                "is_retake": is_retake
            })
            
        return {"code": 200, "total": len(clean_grades), "data": clean_grades}
        
    except Exception as e:
        logger.error(f"成绩查询错误: {e}", exc_info=True)
        return {"code": 500, "msg": "查询成绩失败"}

@app.post("/api/rankings")
def get_rankings(req: RankingRequest):
    """
    根据截图优化的排名解析逻辑：
    1. 使用正则在全文中提取 GPA 和平均分。
    2. 遍历表格行，寻找第一列为 "平均学分绩点" 的行来提取排名。
    """
    user_token = req.token
    cookies = FAKE_REDIS.get(f"user:{user_token}")
    
    if not cookies:
        return {"code": 401, "msg": "登录已失效"}
    
    session = requests.Session()
    session.headers.update(HEADERS)
    session.cookies.update(cookies)

    try:
        # Step 1: 查年级信息
        logger.info(f"获取年级信息: {req.username}")
        info_resp = session.post(RANK_INFO_URL, data={"xsxh": req.username}, timeout=5)
        info_json = info_resp.json()
        
        if info_json.get("ret") != 0 or not info_json.get("data", {}).get("records"):
            return {"code": 404, "msg": "未找到学生信息"}
            
        student_info = info_json["data"]["records"][0]
        sznj = student_info["sznj"]
        
        # Step 2: 拉取 HTML
        target_semester = req.semester if req.semester != "all" else ""
        params = {
            "xh": req.username,
            "sznj": sznj,
            "xnxq": target_semester
        }
        
        logger.info(f"拉取排名HTML: {params}")
        html_resp = session.get(RANK_PAGE_URL, params=params, timeout=10)
        html_text = html_resp.text
        
        # Step 3: 解析 HTML
        soup = BeautifulSoup(html_text, 'html.parser')
        
        res = {
            "gpa": "无",           # 平均学分绩点
            "class_rank": "无",    # 班级排名
            "major_rank": "无",    # 专业排名
            "avg_score": "无",     # 平均成绩
            "fail_count": "0"      # 不及格 (备用，虽然截图没显示但保留逻辑)
        }

        # --- A. 提取顶部摘要信息 (正则提取) ---
        # 截图顶部显示： "平均学分绩点： 3.6152"  "算术平均分： 87.8"
        # 使用正则在整个网页文本中搜索，忽略空格和中英文冒号
        all_text = soup.get_text()
        
        gpa_match = re.search(r"平均学分绩点\s*[：:]\s*([0-9.]+)", all_text)
        if gpa_match:
            res["gpa"] = gpa_match.group(1)
            
        avg_match = re.search(r"算术平均分\s*[：:]\s*([0-9.]+)", all_text)
        if avg_match:
            res["avg_score"] = avg_match.group(1)

        # --- B. 提取底部表格排名 ---
        # 截图显示表格头：[排名方式, 学院(年级), 专业, 班级]
        # 目标行内容：[平均学分绩点, 40/352, 14/123, 4/41]
        
        rows = soup.find_all("tr")
        for tr in rows:
            cells = tr.find_all("td")
            if not cells: continue
            
            # 获取该行所有单元格的纯文本
            cell_texts = [td.get_text(strip=True) for td in cells]
            
            # 判断第一列是否是“平均学分绩点”
            if len(cell_texts) >= 4 and cell_texts[0] == "平均学分绩点":
                # 这一行就是我们要找的 GPA 排名行
                # [0]: 平均学分绩点
                # [1]: 学院排名 (40/352)
                # [2]: 专业排名 (14/123)
                # [3]: 班级排名 (4/41)
                res["major_rank"] = cell_texts[2]
                res["class_rank"] = cell_texts[3]
                
                # 如果你想看算术平均分的排名，可以在这里扩展，但通常只看绩点排名
                break

        logger.info(f"解析成功: GPA={res['gpa']}, Rank={res['major_rank']}")
        return {"code": 200, "data": res}

    except Exception as e:
        logger.error(f"排名获取错误: {e}", exc_info=True)
        return {"code": 500, "msg": "排名获取失败"}

if __name__ == "__main__":
    import uvicorn
    # 生产环境配置：使用 workers 提高性能，绑定到所有接口
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info",
        access_log=True
    )