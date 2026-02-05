# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
import uuid
import random
import string
import time
import re
import ddddocr
from PIL import Image
import json

# 修复 Pillow 兼容性
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

app = FastAPI(title="HBUT 教务小程序后端")

# 初始化 OCR
ocr = ddddocr.DdddOcr()

# ================= 配置区域 =================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FAKE_REDIS = {}

# URL 配置
LOGIN_URL = "https://auth.hbut.edu.cn/authserver/login"
CAPTCHA_URL = "https://auth.hbut.edu.cn/authserver/getCaptcha.htl"
JW_HOME_URL = "https://hbut.jw.chaoxing.com/admin/login"
TIMETABLE_PAGE_URL = "https://hbut.jw.chaoxing.com/admin/pkgl/xskb/queryKbForXsd"
TIMETABLE_API_URL = "https://hbut.jw.chaoxing.com/admin/pkgl/xskb/sdpkkbList"
CURRENT_WEEK_API_URL = "https://hbut.jw.chaoxing.com/admin/api/getXlzc"
GRADE_API_URL = "https://hbut.jw.chaoxing.com/admin/xsd/xsdcjcx/xsdQueryXscjList"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": LOGIN_URL
}

KCXZ_MAP = {
    "44": "专业必修", "11": "通识必修", "12": "通识选修",
    "31": "学科基础", "40": "专业核心", "45": "专业选修",
    "50": "基础实践", "51": "专业实践", "52": "综合实践",
    "99": "公共选修", "98": "重修", "16": "限选"
}

# ================= 数据模型 =================
class LoginRequest(BaseModel):
    username: str
    password: str
    token: str = None   
    captcha: str = None 

class TokenRequest(BaseModel):
    token: str

class TimetableRequest(BaseModel):
    token: str
    xnxq: str = "2025-2026-1"

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
        print(f"加密失败: {e}")
        return None

def strip_html(text: str) -> str:
    if not text: return ""
    try:
        return BeautifulSoup(text, "html.parser").get_text(strip=True)
    except:
        return text

def attempt_login(username, password, manual_captcha=None, session_data=None):
    session = requests.Session()
    session.headers.update(HEADERS)
    execution, salt, lt, captcha_code = "", "", "", ""
    snapshot = None

    if manual_captcha and session_data:
        session.cookies.update(session_data['cookies'])
        execution = session_data['execution']
        salt = session_data['salt']
        lt = session_data['lt']
        captcha_code = manual_captcha
    else:
        try:
            resp = session.get(LOGIN_URL, timeout=5)
            soup = BeautifulSoup(resp.text, 'html.parser')
            execution = soup.find('input', {'name': 'execution'})['value']
            salt = soup.find('input', {'id': 'pwdEncryptSalt'})['value']
            lt_tag = soup.find('input', {'name': 'lt'})
            lt = lt_tag['value'] if lt_tag else ""
            
            timestamp = int(time.time() * 1000)
            captcha_resp = session.get(f"{CAPTCHA_URL}?{timestamp}", timeout=5)
            img_bytes = captcha_resp.content
            captcha_code = ocr.classification(img_bytes)
            
            snapshot = {
                "cookies": session.cookies.get_dict(),
                "execution": execution, "salt": salt, "lt": lt,
                "img_b64": base64.b64encode(img_bytes).decode('utf-8')
            }
        except: return False, None, None

    pwd = encrypt_password(password, salt)
    payload = {
        "username": username, "password": pwd, "captcha": captcha_code,
        "_eventId": "submit", "cllt": "userNameLogin", "dllt": "generalLogin",
        "lt": lt, "execution": execution
    }

    try:
        login_resp = session.post(LOGIN_URL, data=payload, allow_redirects=False, timeout=10)
        if login_resp.status_code == 302:
            redirect_url = login_resp.headers.get("Location")
            session.get(redirect_url, allow_redirects=True)
            session.get(JW_HOME_URL)
            
            # 抓取 xhid
            xhid = ""
            try:
                tb_page = session.get(f"{TIMETABLE_PAGE_URL}?xnxq=2025-2026-1", timeout=10)
                soup = BeautifulSoup(tb_page.text, 'html.parser')
                inp = soup.find('input', {'id': 'xhid'})
                if inp: xhid = inp.get('value')
            except: pass

            user_token = str(uuid.uuid4())
            FAKE_REDIS[f"user:{user_token}"] = {
                "cookies": session.cookies.get_dict(),
                "xhid": xhid, "stu_id": username
            }
            return True, user_token, None
        else:
            return False, "AuthFailed", snapshot
    except: return False, "NetworkError", None

# ================= API 接口 =================

@app.get("/api/captcha")
def get_captcha():
    # 仅用于手动模式刷新
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        resp = session.get(LOGIN_URL, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        execution = soup.find('input', {'name': 'execution'})['value']
        salt = soup.find('input', {'id': 'pwdEncryptSalt'})['value']
        lt_tag = soup.find('input', {'name': 'lt'})
        lt = lt_tag['value'] if lt_tag else ""

        timestamp = int(time.time() * 1000)
        captcha_resp = session.get(f"{CAPTCHA_URL}?{timestamp}", timeout=5)
        b64_img = base64.b64encode(captcha_resp.content).decode('utf-8')
        
        temp_token = str(uuid.uuid4())
        FAKE_REDIS[f"session:{temp_token}"] = {
            "cookies": session.cookies.get_dict(),
            "execution": execution, "salt": salt, "lt": lt
        }
        return {"code": 200, "data": {"token": temp_token, "image": f"data:image/jpeg;base64,{b64_img}"}}
    except Exception as e:
        return {"code": 500, "msg": str(e)}

@app.post("/api/login")
def login(req: LoginRequest):
    if req.token and req.captcha:
        # 手动模式
        session_data = FAKE_REDIS.get(f"session:{req.token}")
        if not session_data: return {"code": 400, "msg": "验证码过期"}
        success, result, _ = attempt_login(req.username, req.password, req.captcha, session_data)
        if success: return {"code": 200, "user_token": result}
        return {"code": 401, "msg": "验证码或密码错误"}
    else:
        # 自动模式
        last_snap = None
        for i in range(3):
            success, result, snap = attempt_login(req.username, req.password)
            if success: return {"code": 200, "user_token": result}
            if snap: last_snap = snap
            time.sleep(0.5)
        
        if last_snap:
            t_token = str(uuid.uuid4())
            FAKE_REDIS[f"session:{t_token}"] = {
                "cookies": last_snap['cookies'], "execution": last_snap['execution'],
                "salt": last_snap['salt'], "lt": last_snap['lt']
            }
            return {"code": 429, "msg": "自动识别失败，请手动输入", "data": {"token": t_token, "image": f"data:image/jpeg;base64,{last_snap['img_b64']}"}}
        return {"code": 500, "msg": "登录失败"}

@app.post("/api/grades")
def query_grades(req: TokenRequest):
    user_data = FAKE_REDIS.get(f"user:{req.token}")
    if not user_data: return {"code": 401, "msg": "请重新登录"}
    
    session = requests.Session()
    session.headers.update(HEADERS)
    session.cookies.update(user_data['cookies'])
    
    payload = {
        "fxbz": "0", "gridtype": "jqgrid", "page.pn": "1", "page.size": "500",
        "sort": "xnxq", "order": "desc",
        "queryFields": "id,xnxq,kcmc,xf,kcxz,cjfxms,zhcj,xdxz"
    }
    try:
        resp = session.post(GRADE_API_URL, data=payload, timeout=10)
        if "text/html" in resp.headers.get("Content-Type", ""):
            return {"code": 401, "msg": "会话过期"}
            
        res_list = resp.json().get("results", [])
        data = []
        for item in res_list:
            data.append({
                "semester": item.get("xnxq"),
                "name": item.get("kcmc"),
                "credit": item.get("xf"),
                "score": item.get("zhcj"),
                "type": KCXZ_MAP.get(str(item.get("kcxz")), "其他"),
                "is_retake": str(item.get("xdxz")) == "2"
            })
        return {"code": 200, "data": data}
    except Exception as e:
        return {"code": 500, "msg": str(e)}

@app.post("/api/timetable")
def query_timetable(req: TimetableRequest):
    user_data = FAKE_REDIS.get(f"user:{req.token}")
    if not user_data: return {"code": 401, "msg": "请重新登录"}
    xhid = user_data.get("xhid")
    if not xhid: return {"code": 403, "msg": "缺少 xhid"}

    session = requests.Session()
    session.headers.update(HEADERS)
    session.cookies.update(user_data['cookies'])
    
    try:
        # 1. 获取当前周
        current_week = 1 
        try:
            week_resp = session.get(CURRENT_WEEK_API_URL, timeout=5)
            if week_resp.json().get("ret") == 0:
                current_week = int(week_resp.json()['data'].get('xlzc', 1))
        except: pass

        # 2. 获取数据
        params = {"xnxq": req.xnxq, "xhid": xhid, "xqdm": "1", "xskbxslx": "0"}
        resp = session.get(TIMETABLE_API_URL, params=params, timeout=10)
        if "text/html" in resp.headers.get("Content-Type", ""):
            return {"code": 401, "msg": "会话过期"}

        json_data = resp.json()
        raw_list = json_data.get("data", [])
        
        # 3. 预处理
        processed_list = []
        for item in raw_list:
            zcstr = item.get("zcstr", "")
            weeks_list = []
            if zcstr:
                try: weeks_list = [int(x) for x in zcstr.split(",") if x.strip().isdigit()]
                except: pass

            # 平台返回的 djs 是结束节次，不是跨度，需换算：跨度 = 结束节次 - 开始节次 + 1
            start_sec = int(item.get("djc", 1))
            end_sec = int(item.get("djs", start_sec))
            step_span = max(1, end_sec - start_sec + 1)
            
            processed_list.append({
                "name": strip_html(item.get("kcmc")),
                "room": strip_html(item.get("croommc")),
                "teacher": strip_html(item.get("tmc")),
                "weeks_desc": item.get("zc"),       
                "weeks_list": weeks_list,           
                "day": int(item.get("xingqi", 0)),  
                "start": start_sec,   
                "step": step_span,
                "raw_zc": item.get("zc", ""),
                "pkid": item.get("pkid", "")
            })

        # 4. 【核心】合并算法
        processed_list.sort(key=lambda x: (x['day'], x['start']))
        merged_list = []
        
        if processed_list:
            current = processed_list[0]
            for next_item in processed_list[1:]:
                # 判断是否同一门课
                is_same = (
                    current['day'] == next_item['day'] and
                    current['name'] == next_item['name'] and
                    current['teacher'] == next_item['teacher'] and
                    current['room'] == next_item['room'] and
                    current['raw_zc'] == next_item['raw_zc']
                )
                # 判断时间是否连续 (第1节+1 = 第2节)
                is_cont = (current['start'] + current['step']) == next_item['start']
                
                if is_same and is_cont:
                    # 合并：只增加时长
                    current['step'] += next_item['step']
                else:
                    merged_list.append(current)
                    current = next_item
            merged_list.append(current)

        return {
            "code": 200, 
            "data": merged_list, 
            "current_week": current_week,
            "semester": req.xnxq
        }
        
    except Exception as e:
        return {"code": 500, "msg": f"失败: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)