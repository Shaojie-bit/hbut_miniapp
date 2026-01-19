# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException
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

app = FastAPI(title="HBUT 教务小程序后端")

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

# [关键] 课表HTML页面，用于抓取 xhid
TIMETABLE_PAGE_URL = "https://hbut.jw.chaoxing.com/admin/pkgl/xskb/queryKbForXsd"
# 课表数据接口
TIMETABLE_API_URL = "https://hbut.jw.chaoxing.com/admin/pkgl/xskb/sdpkkbList"
# [新增] 获取当前周次接口
CURRENT_WEEK_API_URL = "https://hbut.jw.chaoxing.com/admin/api/getXlzc"
# 成绩接口
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
    token: str
    username: str
    password: str
    captcha: str

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

# ================= API 接口 =================

@app.get("/api/captcha")
def get_captcha():
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
        return {"code": 500, "msg": f"验证码获取失败: {str(e)}"}

@app.post("/api/login")
def login(req: LoginRequest):
    raw_data = FAKE_REDIS.get(f"session:{req.token}")
    if not raw_data: return {"code": 400, "msg": "验证码过期"}
    
    session = requests.Session()
    session.headers.update(HEADERS)
    session.cookies.update(raw_data['cookies'])
    
    pwd = encrypt_password(req.password, raw_data['salt'])
    payload = {
        "username": req.username, "password": pwd, "captcha": req.captcha,
        "_eventId": "submit", "cllt": "userNameLogin", "dllt": "generalLogin",
        "lt": raw_data['lt'], "execution": raw_data['execution']
    }
    
    try:
        login_resp = session.post(LOGIN_URL, data=payload, allow_redirects=False, timeout=15)
        
        if login_resp.status_code == 302:
            redirect_url = login_resp.headers.get("Location")
            session.get(redirect_url, allow_redirects=True)
            session.get(JW_HOME_URL)
            
            # [核心步骤] 提取 xhid
            print("正在自动提取 xhid...")
            xhid = ""
            try:
                # 必须带 xnxq，否则可能跳错
                tb_page = session.get(f"{TIMETABLE_PAGE_URL}?xnxq=2025-2026-1", timeout=10)
                soup = BeautifulSoup(tb_page.text, 'html.parser')
                xhid_input = soup.find('input', {'id': 'xhid'})
                if xhid_input and xhid_input.get('value'):
                    xhid = xhid_input.get('value')
                    print(f"成功提取 xhid: {xhid[:15]}...")
                else:
                    print("警告：未在页面找到 xhid")
            except Exception as e:
                print(f"提取 xhid 异常: {e}")
            
            user_token = str(uuid.uuid4())
            FAKE_REDIS[f"user:{user_token}"] = {
                "cookies": session.cookies.get_dict(),
                "xhid": xhid,
                "stu_id": req.username
            }
            del FAKE_REDIS[f"session:{req.token}"]
            return {"code": 200, "msg": "登录成功", "user_token": user_token}
        else:
            return {"code": 401, "msg": "账号或密码错误"}
    except Exception as e:
        return {"code": 500, "msg": f"登录异常: {str(e)}"}

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
    if not xhid: return {"code": 403, "msg": "缺少 xhid，请重新登录"}

    session = requests.Session()
    session.headers.update(HEADERS)
    session.cookies.update(user_data['cookies'])
    
    try:
        # 1. 获取当前周次
        current_week = 1 # 默认值
        try:
            week_resp = session.get(CURRENT_WEEK_API_URL, timeout=5)
            week_json = week_resp.json()
            # 返回结构参考: {"ret": 0, "msg": "ok", "data": {"xlzc": 19}}
            if week_json.get("ret") == 0:
                current_week = int(week_json['data'].get('xlzc', 1))
        except Exception as e:
            print(f"获取当前周次失败: {e}")

        # 2. 获取全部课表
        params = {"xnxq": req.xnxq, "xhid": xhid, "xqdm": "1", "xskbxslx": "0"}
        resp = session.get(TIMETABLE_API_URL, params=params, timeout=10)
        json_data = resp.json()
        
        if json_data.get("ret") != 0:
             return {"code": 500, "msg": json_data.get("msg", "接口错误")}
             
        raw_list = json_data.get("data", [])
        clean_list = []
        
        for item in raw_list:
            # 解析周次字符串 "1,2,3,4,7,8" -> [1,2,3,4,7,8]
            zcstr = item.get("zcstr", "")
            weeks_list = []
            if zcstr:
                try:
                    weeks_list = [int(x) for x in zcstr.split(",") if x.strip().isdigit()]
                except:
                    pass

            clean_list.append({
                "name": strip_html(item.get("kcmc")),
                "room": strip_html(item.get("croommc")),
                "teacher": strip_html(item.get("tmc")),
                "weeks_desc": item.get("zc"),       # 显示用 "1-5,7-10周"
                "weeks_list": weeks_list,           # 逻辑用 [1,2,3,4,7,8,9,10]
                "day": int(item.get("xingqi", 0)),  # 星期几
                "start": int(item.get("djc", 1)),   # 开始节
                "step": int(item.get("djs", 1)),    # 跨度
                "credit": item.get("xf")
            })
            
        return {
            "code": 200, 
            "data": clean_list, 
            "current_week": current_week,
            "semester": req.xnxq
        }
        
    except Exception as e:
        return {"code": 500, "msg": f"失败: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)