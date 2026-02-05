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
import json
import random
import string
import time

app = FastAPI(title="HBUT 教务小程序后端")

# ================= 配置区域 =================

# 允许跨域请求（方便小程序或前端调试）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 临时数据库 (生产环境建议换成 Redis)
FAKE_REDIS = {}

# 关键 URL 配置
LOGIN_URL = "https://auth.hbut.edu.cn/authserver/login"
CAPTCHA_URL = "https://auth.hbut.edu.cn/authserver/getCaptcha.htl"
# 登录成功后的跳转目标（教务系统首页）
JW_HOME_URL = "https://hbut.jw.chaoxing.com/admin/login" 
# 成绩查询 JSON 接口
GRADE_API_URL = "https://hbut.jw.chaoxing.com/admin/xsd/xsdcjcx/xsdQueryXscjList"

# 通用请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": LOGIN_URL
}

# 课程性质代码映射 (从 HTML 源码中提取)
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
    token: str      # 获取验证码时下发的临时 token
    username: str   # 学号
    password: str   # 密码
    captcha: str    # 验证码

class TokenRequest(BaseModel):
    token: str      # 登录成功后下发的 user_token

# ================= 工具函数 =================

def encrypt_password(password: str, salt: str) -> str:
    """
    AES 加密逻辑：复刻学校 encrypt.js 的行为
    Logic: AES(64位随机串 + 密码, Key=Salt, IV=16位随机, Mode=CBC) -> Base64
    """
    try:
        # 1. 生成64位随机字符串 (Nonce)
        random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=64))
        
        # 2. 拼接数据
        text = random_str + password
        
        # 3. 准备 Key 和 IV
        key = salt.encode('utf-8')
        iv = ''.join(random.choices(string.ascii_letters + string.digits, k=16)).encode('utf-8')
        
        # 4. AES 加密 (CBC模式)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted_bytes = cipher.encrypt(pad(text.encode('utf-8'), AES.block_size))
        
        # 5. Base64 编码
        return base64.b64encode(encrypted_bytes).decode('utf-8')
    except Exception as e:
        print(f"加密错误: {e}")
        return None

# ================= API 接口 =================

@app.get("/")
def index():
    return {"msg": "HBUT API Service is running!"}

@app.get("/api/captcha")
def get_captcha():
    """
    第一步：获取验证码
    返回：token (用于后续登录), image (Base64图片)
    """
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        # 1. 访问首页获取 Execution 和 Salt
        resp = session.get(LOGIN_URL, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        execution_tag = soup.find('input', {'name': 'execution'})
        salt_tag = soup.find('input', {'id': 'pwdEncryptSalt'})
        lt_tag = soup.find('input', {'name': 'lt'})
        
        if not execution_tag or not salt_tag:
            raise HTTPException(status_code=500, detail="无法解析教务系统页面，可能系统已更新")

        execution = execution_tag['value']
        salt = salt_tag['value']
        lt = lt_tag['value'] if lt_tag else ""

        # 2. 下载验证码
        timestamp = int(time.time() * 1000)
        captcha_resp = session.get(f"{CAPTCHA_URL}?{timestamp}", timeout=5)
        
        # 3. 图片转 Base64
        b64_img = base64.b64encode(captcha_resp.content).decode('utf-8')
        img_src = f"data:image/jpeg;base64,{b64_img}"

        # 4. 暂存 Session 数据 (关联到一个临时 Token)
        temp_token = str(uuid.uuid4())
        session_data = {
            "cookies": session.cookies.get_dict(),
            "execution": execution,
            "salt": salt,
            "lt": lt
        }
        
        # 存入 "Redis" (5分钟有效)
        FAKE_REDIS[f"session:{temp_token}"] = session_data

        return {
            "code": 200,
            "data": {
                "token": temp_token,
                "image": img_src
            }
        }
    except Exception as e:
        print(f"Error in captcha: {e}")
        return {"code": 500, "msg": "教务系统连接超时或异常"}

@app.post("/api/login")
def login(req: LoginRequest):
    """
    第二步：提交登录
    返回：user_token (用于后续查成绩)
    """
    # 1. 取回 Session
    raw_data = FAKE_REDIS.get(f"session:{req.token}")
    if not raw_data:
        return {"code": 400, "msg": "验证码过期，请刷新"}
    
    # 2. 恢复 requests.Session
    session = requests.Session()
    session.headers.update(HEADERS)
    session.cookies.update(raw_data['cookies'])
    
    # 3. 密码加密
    encrypted_pwd = encrypt_password(req.password, raw_data['salt'])
    if not encrypted_pwd:
        return {"code": 500, "msg": "加密算法异常"}

    # 4. 构造表单
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
        # 5. 提交登录 (禁止自动跳转，以便捕获 302)
        login_resp = session.post(LOGIN_URL, data=payload, allow_redirects=False, timeout=15)
        
        if login_resp.status_code == 302:
            redirect_location = login_resp.headers.get("Location")
            print(f"Auth Success. Redirecting to: {redirect_location}")
            
            # 【关键步骤】手动跟随跳转，激活目标域名(hbut.jw.chaoxing.com)的 Cookie
            # 这一步非常重要，否则后续查成绩会报 401
            session.get(redirect_location, allow_redirects=True)
            
            # 再访问一次教务首页，确保 Cookie 完整
            session.get(JW_HOME_URL)
            
            # 6. 生成用户持久 Token
            user_token = str(uuid.uuid4())
            
            # 保存最终的 Cookie (此时应包含 auth 和 jw.chaoxing 两个域名的 cookie)
            FAKE_REDIS[f"user:{user_token}"] = session.cookies.get_dict()
            
            # 清理临时的验证码 session
            if f"session:{req.token}" in FAKE_REDIS:
                del FAKE_REDIS[f"session:{req.token}"]

            return {"code": 200, "msg": "登录成功", "user_token": user_token}
        
        else:
            # 登录失败，尝试解析错误信息
            err_msg = "账号或密码错误"
            soup = BeautifulSoup(login_resp.text, 'html.parser')
            tip_span = soup.find(id="showErrorTip")
            if tip_span:
                err_msg = tip_span.get_text(strip=True)
            return {"code": 401, "msg": err_msg}

    except Exception as e:
        print(f"Login error: {e}")
        return {"code": 500, "msg": "登录过程发生网络错误"}

@app.post("/api/grades")
def query_grades(req: TokenRequest):
    """
    第三步：查询成绩
    直接调用 JSON 接口，无需解析 HTML
    """
    user_token = req.token
    cookies = FAKE_REDIS.get(f"user:{user_token}")
    
    if not cookies:
        return {"code": 401, "msg": "登录已失效"}
    
    session = requests.Session()
    session.headers.update(HEADERS)
    session.cookies.update(cookies)
    
    payload = {
        "fxbz": "0",
        "gridtype": "jqgrid",
        "page.pn": "1",          # 修改：page -> page.pn
        "page.size": "1000",     # 修改：rows -> page.size (设为1000确保拿到所有)
        "sort": "xnxq",
        "order": "desc",
        "queryFields": "id,xnxq,kcmc,xf,kcxz,kclx,ksxs,kcgs,xdxz,kclb,cjfxms,zhcj,hdxf,tscjzwmc,sfbk,cjlrjsxm,kcsx,fxcj,dztmlfjcj,"
    }
    
    try:
        # 发送请求
        resp = session.post(GRADE_API_URL, data=payload, timeout=10)
        
        # 检查是否 Session 失效 (被重定向回登录页)
        if "text/html" in resp.headers.get("Content-Type", ""):
            return {"code": 401, "msg": "会话已过期，请重新登录"}
            
        data_json = resp.json()
        raw_list = data_json.get("results", [])
        
        # 数据清洗
        clean_grades = []
        for item in raw_list:
            # 转换课程性质代码
            kcxz_code = str(item.get("kcxz", ""))
            kcxz_name = KCXZ_MAP.get(kcxz_code, "其他课程")
            
            # 判断是否重修 (xdxz=2)
            is_retake = (str(item.get("xdxz")) == "2")
            
            clean_grades.append({
                "semester": item.get("xnxq"),    # 学期
                "course_name": item.get("kcmc"), # 课程名
                "credit": item.get("xf"),        # 学分
                "score": item.get("zhcj"),       # 成绩
                "type": kcxz_name,               # 性质
                "is_retake": is_retake           # 是否重修
            })
            
        return {
            "code": 200,
            "total": len(clean_grades),
            "data": clean_grades
        }
        
    except Exception as e:
        print(f"Grade query error: {e}")
        return {"code": 500, "msg": "查询成绩失败"}

if __name__ == "__main__":
    import uvicorn
    # 启动服务：host="0.0.0.0" 允许外网访问
    uvicorn.run(app, host="0.0.0.0", port=8000)