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
import traceback
import ddddocr
import sqlite3
import json
import os
from PIL import Image
from datetime import datetime, timedelta
from datetime import datetime, timedelta
from threading import Lock
import urllib.parse

# 修复 Pillow 兼容性
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

app = FastAPI(title="HBUT 教务小程序后端")
ocr = ddddocr.DdddOcr(show_ad=False)

# ================= 配置区域 =================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION_EXPIRE_DAYS = 7
LOGIN_RATE_LIMIT_SECONDS = 3
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions.db")
db_lock = Lock()

# Cloudflare Proxy URL (Tunnel Mode)
# 请在 Cloudflare 后台将此域名绑定到 Worker
CF_PROXY_URL = "https://hbut-worker.zmj888.asia/"

# Target URLs
LOGIN_URL = "https://auth.hbut.edu.cn/authserver/login"
CAPTCHA_URL = "https://auth.hbut.edu.cn/authserver/getCaptcha.htl"
JW_HOME_URL = "https://hbut.jw.chaoxing.com/admin/login"
TIMETABLE_PAGE_URL = "https://hbut.jw.chaoxing.com/admin/pkgl/xskb/queryKbForXsd"
TIMETABLE_API_URL = "https://hbut.jw.chaoxing.com/admin/pkgl/xskb/sdpkkbList"
CURRENT_WEEK_API_URL = "https://hbut.jw.chaoxing.com/admin/api/getXlzc"
GRADE_API_URL = "https://hbut.jw.chaoxing.com/admin/xsd/xsdcjcx/xsdQueryXscjList"
RANK_INFO_URL = "https://hbut.jw.chaoxing.com/admin/cjgl/xscjbbdy/printdgxscj"
RANK_PAGE_URL = "https://hbut.jw.chaoxing.com/admin/cjgl/xscjbbdy/getXscjpm"

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

# ================= 代理请求封装 =================
def cf_request(method, url, headers=None, data=None, cookies=None):
    """通过 Cloudflare Worker 代理发送请求 (自定义域名模式)"""
    if headers is None: headers = {}
    if cookies:
        cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        headers["Cookie"] = cookie_str
    
    payload = {
        "target_url": url,
        "method": method,
        "headers": headers,
        "body": None
    }
    
    if data:
        if isinstance(data, dict):
            # FIXED: 使用 urlencode 处理特殊字符 (如 + / =)
            payload["body"] = urllib.parse.urlencode(data)
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            payload["body"] = data

    try:
        # 直接通过域名及HTTPS请求，无需 IP 直连
        res = requests.post(CF_PROXY_URL, json=payload, timeout=15)
        res_json = res.json()
        
        class MockResponse:
            def __init__(self, data):
                self.status_code = data['status']
                self.text = data.get('text', '') # 兼容旧逻辑
                # 优先解析 headers_list (避免 Set-Cookie 丢失)
                self.headers = requests.structures.CaseInsensitiveDict()
                if 'headers_list' in data:
                    for k, v in data['headers_list']:
                        # 处理 Set-Cookie: requests 不支持多值 key，但我们可以特殊处理
                        # 实际上 extract_cookies 需要原始信息。
                        # 我们把它们拼接到 self.headers 中，或者最好直接存一个 raw_list
                        # 这里为了兼容 extract_cookies，我们将 Set-Cookie 用特殊分隔符拼接? 
                        # 不，最好是不覆盖。
                        if k.lower() == 'set-cookie':
                            if 'set-cookie' in self.headers:
                                self.headers['set-cookie'] += '; ' + v # 并不是标准做法，但够用
                            else:
                                self.headers['set-cookie'] = v
                        else:
                            self.headers[k] = v
                else:
                    self.headers = data['headers']

                self.cookies = requests.cookies.RequestsCookieJar()
                
                # 处理 Base64 body (优先使用)
                if 'body_base64' in data and data['body_base64']:
                    try:
                        self.content = base64.b64decode(data['body_base64'])
                        # 如果是文本，尝试更新 text
                        try: self.text = self.content.decode('utf-8')
                        except: pass
                    except:
                        self.content = b""
                else:
                    self.content = data.get('text', '').encode('utf-8')

            def json(self):
                # 优先解析 text, 如果为空则解析 content
                try: return json.loads(self.text)
                except: return json.loads(self.content)
        
        return MockResponse(res_json)
    except Exception as e:
        print(f"[Proxy Error] {e}")
        return None

# ================= SQLite 会话管理 =================
def init_db():
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS user_sessions (
            token TEXT PRIMARY KEY,
            stu_id TEXT,
            cookies TEXT,
            xhid TEXT,
            created_at TEXT,
            expires_at TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS captcha_sessions (
            token TEXT PRIMARY KEY,
            cookies TEXT,
            execution TEXT,
            salt TEXT,
            lt TEXT,
            created_at TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS login_rate_limit (
            stu_id TEXT PRIMARY KEY,
            last_attempt TEXT
        )''')
        conn.commit()
        conn.close()

def save_user_session(token, stu_id, cookies, xhid):
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        now = datetime.now()
        expires = now + timedelta(days=SESSION_EXPIRE_DAYS)
        c.execute('''INSERT OR REPLACE INTO user_sessions VALUES (?, ?, ?, ?, ?, ?)''',
                  (token, stu_id, json.dumps(cookies), xhid, now.isoformat(), expires.isoformat()))
        conn.commit()
        conn.close()

def get_user_session(token):
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT stu_id, cookies, xhid, expires_at FROM user_sessions WHERE token = ?', (token,))
        row = c.fetchone()
        conn.close()
        if row and datetime.now() < datetime.fromisoformat(row[3]):
            return {"stu_id": row[0], "cookies": json.loads(row[1]), "xhid": row[2]}
    return None

def delete_user_session(token):
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('DELETE FROM user_sessions WHERE token = ?', (token,))
        conn.commit()
        conn.close()

def save_captcha_session(token, cookies, execution, salt, lt, img_b64):
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO captcha_sessions VALUES (?, ?, ?, ?, ?, ?)''',
                  (token, json.dumps(cookies), execution, salt, lt, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    return {"token": token, "image": f"data:image/jpeg;base64,{img_b64}"}

def get_captcha_session(token):
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT cookies, execution, salt, lt, created_at FROM captcha_sessions WHERE token = ?', (token,))
        row = c.fetchone()
        conn.close()
        if row and datetime.now() - datetime.fromisoformat(row[4]) < timedelta(minutes=5):
            return {"cookies": json.loads(row[0]), "execution": row[1], "salt": row[2], "lt": row[3]}
    return None

def delete_captcha_session(token):
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('DELETE FROM captcha_sessions WHERE token = ?', (token,))
        conn.commit()
        conn.close()

def check_rate_limit(stu_id):
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT last_attempt FROM login_rate_limit WHERE stu_id = ?', (stu_id,))
        row = c.fetchone()
        conn.close()
        if row:
            last = datetime.fromisoformat(row[0])
            elapsed = (datetime.now() - last).total_seconds()
            if elapsed < LOGIN_RATE_LIMIT_SECONDS:
                return False, int(LOGIN_RATE_LIMIT_SECONDS - elapsed)
    return True, 0

def update_rate_limit(stu_id):
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO login_rate_limit VALUES (?, ?)''',
                  (stu_id, datetime.now().isoformat()))
        conn.commit()
        conn.close()

init_db()

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

class RankingRequest(BaseModel):
    token: str
    username: str
    semester: str

# ================= 业务逻辑 =================
def encrypt_password(password: str, salt: str) -> str:
    try:
        random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=64))
        text = random_str + password
        key = salt.encode('utf-8')
        iv = ''.join(random.choices(string.ascii_letters + string.digits, k=16)).encode('utf-8')
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return base64.b64encode(cipher.encrypt(pad(text.encode('utf-8'), AES.block_size))).decode('utf-8')
    except: return None

def strip_html(text: str) -> str:
    try: return BeautifulSoup(text, "html.parser").get_text(strip=True)
    except: return text or ""

# 提取 Cookie 辅助
def extract_cookies(headers, existing_cookies):
    set_cookie = headers.get('set-cookie')
    if set_cookie:
        # 简单处理：仅提取 key=value，忽略 Path, HttpOnly 等属性
        # 注意：这里假设 Set-Cookie 格式较为标准，且 requests 可能合并了多个 Set-Cookie
        # 更严谨的做法是解析每个 Cookie，这里先过滤掉常见属性
        ignore_keys = {'path', 'domain', 'expires', 'max-age', 'secure', 'httponly', 'samesite'}
        
        # Requests 的 headers 是 CaseInsensitiveDict，但 value 是字符串
        # Cloudflare Worker 返回的 headers 可能是普通 dict
        if isinstance(set_cookie, list):
            parts = set_cookie
        else:
            # 应对 Cloudflare Worker 可能的合并行为 (comma separated)
            # 以及手动拼接的 semicolon separated
            # 这是一个启发式分割，针对 JSESSIONID 和 route=xxx
            parts = re.split(r'[;,]\s*', set_cookie)
            
        for part in parts:
            if '=' in part:
                try:
                    k, v = part.split('=', 1)
                    k = k.strip()
                    v = v.strip()
                    if k.lower() not in ignore_keys:
                        existing_cookies[k] = v
                except: pass
    return existing_cookies

def attempt_login_proxy(username, password, manual_captcha=None, session_data=None):
    """通过代理登录"""
    cookies = {}
    execution, salt, lt, captcha_code = "", "", "", ""
    snapshot = None
    
    current_headers = HEADERS.copy()

    if manual_captcha and session_data:
        print(f"[Login] 手动模式: {username}")
        cookies = session_data['cookies']
        execution = session_data['execution']
        salt = session_data['salt']
        lt = session_data['lt']
        captcha_code = manual_captcha
    else:
        try:
            print(f"[Login Debug] Step 1: GET Login Page")
            resp = cf_request("GET", LOGIN_URL, headers=current_headers, cookies=cookies)
            if not resp or resp.status_code != 200:
                print(f"[Login] 页面获取失败: {resp.status_code if resp else 'None'}")
                return False, "NETWORK_ERROR", None
            
            cookies = extract_cookies(resp.headers, cookies)
            print(f"[Login Debug] Page Cookies: {cookies}")
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            execution_tag = soup.find('input', {'name': 'execution'})
            salt_tag = soup.find('input', {'id': 'pwdEncryptSalt'})
            
            if not execution_tag:
                return False, "PAGE_CHANGED", None
            
            execution = execution_tag['value']
            salt = salt_tag['value']
            lt_tag = soup.find('input', {'name': 'lt'})
            lt = lt_tag['value'] if lt_tag else ""
            
            timestamp = int(time.time() * 1000)
            print(f"[Login Debug] Step 2: GET Captcha")
            captcha_resp = cf_request("GET", f"{CAPTCHA_URL}?{timestamp}", headers=current_headers, cookies=cookies)
            cookies = extract_cookies(captcha_resp.headers, cookies)
            print(f"[Login Debug] Captcha Cookies: {cookies}")
            
            # img_bytes = captcha_resp.text.encode('latin1') # OLD ERROR
            img_bytes = captcha_resp.content # NEW: 直接使用二进制数据
            captcha_code = ocr.classification(img_bytes)
            print(f"[Login] OCR: {captcha_code}")
            
            snapshot = {
                "cookies": cookies,
                "execution": execution, "salt": salt, "lt": lt,
                "img_b64": base64.b64encode(img_bytes).decode('utf-8')
            }
        except Exception as e:
            traceback.print_exc()
            return False, "NETWORK_ERROR", None

    pwd = encrypt_password(password, salt)
    if not pwd: return False, "ENCRYPT_ERROR", None
    
    payload = {
        "username": username, "password": pwd, "captcha": captcha_code,
        "_eventId": "submit", "cllt": "userNameLogin", "dllt": "generalLogin",
        "lt": lt, "execution": execution
    }

    try:
        print(f"[Login] Proxy POST -> {LOGIN_URL}")
        # print(f"[Login Debug] POST Payload: {payload}")
        print(f"[Login Debug] POST Cookies: {cookies}")
        
        login_resp = cf_request("POST", LOGIN_URL, headers=current_headers, data=payload, cookies=cookies)
        cookies = extract_cookies(login_resp.headers, cookies)
        
        if login_resp.status_code == 302:
            # ... success redirection ...
            redirect_url = login_resp.headers.get("Location") or login_resp.headers.get("location")
            print(f"[Login] Redirect -> {redirect_url}")
            cf_request("GET", redirect_url, headers=current_headers, cookies=cookies)
            cf_request("GET", JW_HOME_URL, headers=current_headers, cookies=cookies)
            
            xhid = ""
            try:
                tb_page = cf_request("GET", f"{TIMETABLE_PAGE_URL}?xnxq=2025-2026-1", headers=current_headers, cookies=cookies)
                soup = BeautifulSoup(tb_page.text, 'html.parser')
                inp = soup.find('input', {'id': 'xhid'})
                if inp: xhid = inp.get('value')
            except: pass

            user_token = str(uuid.uuid4())
            save_user_session(user_token, username, cookies, xhid)
            return True, user_token, None
        else:
            soup = BeautifulSoup(login_resp.text, 'html.parser')
            error_span = soup.find('span', {'id': 'errorMsg'}) or soup.find('span', {'id': 'msg'})
            msg = error_span.get_text(strip=True) if error_span else "验证码错误"
            
            # Save failure page for debugging
            try:
                with open("/tmp/login_fail.html", "w", encoding="utf-8") as f:
                    f.write(login_resp.text)
                print(f"[Login Debug] Failed. Msg: {msg}. Saved to /tmp/login_fail.html")
            except: pass
            
            return False, msg, snapshot
    except: return False, "NETWORK_ERROR", None


# ================= API =================

def fetch_new_captcha_session():
    """获取全新的验证码会话"""
    try:
        current_headers = HEADERS.copy()
        # 1. 获取登录页 (Session Init)
        print("[Captcha] Init new session...")
        resp = cf_request("GET", LOGIN_URL, headers=current_headers)
        if not resp or resp.status_code != 200:
            return None, "服务不可用"
        
        cookies = extract_cookies(resp.headers, {})
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        execution_tag = soup.find('input', {'name': 'execution'})
        salt_tag = soup.find('input', {'id': 'pwdEncryptSalt'})
        
        if not execution_tag:
            return None, "页面结构变化"
            
        execution = execution_tag['value']
        salt = salt_tag['value']
        lt_tag = soup.find('input', {'name': 'lt'})
        lt = lt_tag['value'] if lt_tag else ""
        
        # 2. 获取验证码
        timestamp = int(time.time() * 1000)
        captcha_resp = cf_request("GET", f"{CAPTCHA_URL}?{timestamp}", headers=current_headers, cookies=cookies)
        cookies = extract_cookies(captcha_resp.headers, cookies)
        
        img_bytes = captcha_resp.content
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        
        # 3. 保存会话
        token = str(uuid.uuid4())
        data = save_captcha_session(token, cookies, execution, salt, lt, img_b64)
        return data, None
    except Exception as e:
        traceback.print_exc()
        return None, "系统错误"

@app.get("/api/captcha")
def api_captcha():
    """手动刷新验证码接口"""
    data, err = fetch_new_captcha_session()
    if data:
        return {"code": 200, "data": data}
    return {"code": 500, "msg": err}

@app.post("/api/login")
def api_login(req: LoginRequest):
    allowed, wait = check_rate_limit(req.username)
    if not allowed: return {"code": 403, "msg": f"请求太频繁，请等待 {wait} 秒"} # Fix frontend crash (429->403)
    update_rate_limit(req.username)

    if req.token and req.captcha:
        # 手动模式提交
        session_data = get_captcha_session(req.token)
        if not session_data: return {"code": 400, "msg": "验证码过期，请刷新"}
        delete_captcha_session(req.token)
        success, res, _ = attempt_login_proxy(req.username, req.password, req.captcha, session_data)
        if success: return {"code": 200, "user_token": res}
        return {"code": 401, "msg": res}
    else:
        # 自动模式
        last_snap = None # Keep track but prefer fresh session on fail
        
        for i in range(3):
            success, res, snap = attempt_login_proxy(req.username, req.password)
            if success: return {"code": 200, "user_token": res}
            # 如果是网络错误，可能根本没拿到 snap
            # 如果是验证码错误，snap 是有的
        
        # 所有重试都失败了，获取一个全新的验证码给用户手动输入
        # 不使用 last_snap，因为那个验证码已经被尝试过且失效了
        print("[Login] Auto login failed. Fetching fresh captcha for manual input.")
        data, err = fetch_new_captcha_session()
        if data:
            return {"code": 429, "msg": "自动识别失败，请手动输入", "data": data}
            
        return {"code": 500, "msg": "登录失败，且无法获取验证码"}

@app.post("/api/grades")
def query_grades(req: TokenRequest):
    user_data = get_user_session(req.token)
    if not user_data: return {"code": 401, "msg": "请重新登录"}
    
    cookies = user_data['cookies']
    current_headers = HEADERS.copy()
    
    payload = {
        "fxbz": "0", "gridtype": "jqgrid", "page.pn": "1", "page.size": "500",
        "sort": "xnxq", "order": "desc",
        "queryFields": "id,xnxq,kcmc,xf,kcxz,cjfxms,zhcj,xdxz"
    }
    
    try:
        resp = cf_request("POST", GRADE_API_URL, headers=current_headers, data=payload, cookies=cookies)
        
        if not resp:
            return {"code": 500, "msg": "代理请求失败"}
            
        if "text/html" in resp.headers.get("Content-Type", ""):
            delete_user_session(req.token)
            return {"code": 401, "msg": "会话过期"}
            
        res_list = resp.json().get("results", [])
        data = []
        for item in res_list:
            data.append({
                "semester": item.get("xnxq"),
                "course_name": item.get("kcmc"),
                "credit": item.get("xf"),
                "score": item.get("zhcj"),
                "type": KCXZ_MAP.get(str(item.get("kcxz")), "其他"),
                "is_retake": str(item.get("xdxz")) == "2"
            })
        return {"code": 200, "data": data}
    except Exception as e:
        return {"code": 500, "msg": str(e)}

@app.post("/api/rankings")
def get_rankings(req: RankingRequest):
    user_data = get_user_session(req.token)
    if not user_data: return {"code": 401, "msg": "登录已失效"}
    
    cookies = user_data['cookies']
    current_headers = HEADERS.copy()

    try:
        info_resp = cf_request("POST", RANK_INFO_URL, headers=current_headers, data={"xsxh": req.username}, cookies=cookies)
        if not info_resp: return {"code": 500, "msg": "代理请求失败"}
        
        info_json = info_resp.json()
        
        if info_json.get("ret") != 0 or not info_json.get("data", {}).get("records"):
            return {"code": 404, "msg": "未找到学生信息"}
            
        student_info = info_json["data"]["records"][0]
        sznj = student_info["sznj"]
        
        target_semester = req.semester if req.semester != "all" else ""
        params = f"?xh={req.username}&sznj={sznj}&xnxq={target_semester}"
        full_rank_url = RANK_PAGE_URL + params
        
        html_resp = cf_request("GET", full_rank_url, headers=current_headers, cookies=cookies)
        if not html_resp: return {"code": 500, "msg": "代理请求失败"}
        
        soup = BeautifulSoup(html_resp.text, 'html.parser')
        
        res = {"gpa": "无", "class_rank": "无", "major_rank": "无", "avg_score": "无", "fail_count": "0"}

        all_text = soup.get_text()
        gpa_match = re.search(r"平均学分绩点\s*[：:]\s*([0-9.]+)", all_text)
        if gpa_match: res["gpa"] = gpa_match.group(1)
        avg_match = re.search(r"算术平均分\s*[：:]\s*([0-9.]+)", all_text)
        if avg_match: res["avg_score"] = avg_match.group(1)

        rows = soup.find_all("tr")
        for tr in rows:
            cells = tr.find_all("td")
            if not cells: continue
            cell_texts = [td.get_text(strip=True) for td in cells]
            if len(cell_texts) >= 4 and cell_texts[0] == "平均学分绩点":
                res["major_rank"] = cell_texts[2]
                res["class_rank"] = cell_texts[3]
                break

        return {"code": 200, "data": res}
    except Exception as e:
        traceback.print_exc()
        return {"code": 500, "msg": "排名获取失败"}

@app.post("/api/timetable")
def query_timetable(req: TimetableRequest):
    user_data = get_user_session(req.token)
    if not user_data: return {"code": 401, "msg": "请重新登录"}
    xhid = user_data.get("xhid")
    if not xhid: return {"code": 403, "msg": "缺少 xhid"}

    cookies = user_data['cookies']
    current_headers = HEADERS.copy()
    
    try:
        current_week = 1 
        try:
            week_resp = cf_request("GET", CURRENT_WEEK_API_URL, headers=current_headers, cookies=cookies)
            if week_resp and week_resp.json().get("ret") == 0:
                current_week = int(week_resp.json()['data'].get('xlzc', 1))
        except: pass

        params = f"?xnxq={req.xnxq}&xhid={xhid}&xqdm=1&xskbxslx=0"
        full_tb_url = TIMETABLE_API_URL + params
        
        resp = cf_request("GET", full_tb_url, headers=current_headers, cookies=cookies)
        
        if not resp: return {"code": 500, "msg": "代理请求失败"}

        if "text/html" in resp.headers.get("Content-Type", ""):
            delete_user_session(req.token)
            return {"code": 401, "msg": "会话过期"}

        json_data = resp.json()
        raw_list = json_data.get("data", [])
        
        processed_list = []
        for item in raw_list:
            zcstr = item.get("zcstr", "")
            weeks_list = []
            if zcstr:
                try: weeks_list = [int(x) for x in zcstr.split(",") if x.strip().isdigit()]
                except: pass

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

        processed_list.sort(key=lambda x: (x['day'], x['start']))
        merged_list = []
        
        if processed_list:
            current = processed_list[0]
            for next_item in processed_list[1:]:
                is_same = (
                    current['day'] == next_item['day'] and
                    current['name'] == next_item['name'] and
                    current['teacher'] == next_item['teacher'] and
                    current['room'] == next_item['room'] and
                    current['raw_zc'] == next_item['raw_zc']
                )
                is_cont = (current['start'] + current['step']) == next_item['start']
                
                if is_same and is_cont:
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