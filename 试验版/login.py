import requests
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
import random
import string

# ================= 配置 =================
LOGIN_URL = "https://auth.hbut.edu.cn/authserver/login"
CAPTCHA_URL = "https://auth.hbut.edu.cn/authserver/getCaptcha.htl"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": LOGIN_URL
}

# ================= 核心加密算法 =================
# 这是针对你学校这种 CAS 系统通用的 AES 加密逻辑
# 逻辑通常是：AES(随机64位字符串 + 密码, Key=Salt, Mode=CBC, IV=随机16位)
def encrypt_password(password, salt):
    try:
        # 1. 生成64位随机字符串 (Nonce)
        random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=64))
        
        # 2. 拼接数据
        text = random_str + password
        
        # 3. 准备 Key 和 IV
        # 注意：这里假设 Salt 直接作为 Key。如果后续报错，可能需要调整 Key 的处理方式
        key = salt.encode('utf-8')
        iv = ''.join(random.choices(string.ascii_letters + string.digits, k=16)).encode('utf-8')
        
        # 4. AES 加密 (CBC模式)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted_bytes = cipher.encrypt(pad(text.encode('utf-8'), AES.block_size))
        
        # 5. Base64 编码 (最终结果)
        result = base64.b64encode(encrypted_bytes).decode('utf-8')
        return result
    except Exception as e:
        print(f"加密过程出错: {e}")
        return None

# ================= 登录流程 =================
def login_hbut(username, password):
    session = requests.Session()
    session.headers.update(HEADERS)

    # 1. 访问首页，获取 Execution 和 Salt
    print("1. 正在获取登录页信息...")
    resp = session.get(LOGIN_URL)
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # 提取关键参数
    try:
        execution = soup.find('input', {'name': 'execution'})['value']
        salt = soup.find('input', {'id': 'pwdEncryptSalt'})['value']
        # 某些学校 lt 是动态的，你的 HTML 里 lt 是空的，但我们还是尝试提取一下以防万一
        lt_tag = soup.find('input', {'name': 'lt'})
        lt = lt_tag['value'] if lt_tag else ""
        
        print(f"   -> 获取成功! Execution: {execution[:10]}... Salt: {salt}")
    except Exception as e:
        print("❌ 无法提取关键参数，页面结构可能变了。", e)
        return False

    # 2. 下载验证码
    print("2. 下载验证码...")
    # 添加时间戳防止缓存
    import time
    timestamp = int(time.time() * 1000)
    resp_captcha = session.get(f"{CAPTCHA_URL}?{timestamp}")
    with open("captcha.jpg", "wb") as f:
        f.write(resp_captcha.content)
    
    captcha_code = input("请输入本地生成的 captcha.jpg 上的验证码: ")

    # 3. 加密密码
    print("3. 正在加密密码...")
    encrypted_pwd = encrypt_password(password, salt)
    if not encrypted_pwd:
        return False

    # 4. 构造表单数据 (完全对应你的 Form Data)
    data = {
        "username": username,
        "password": encrypted_pwd,  # 注意：这里放加密后的
        "captcha": captcha_code,
        "_eventId": "submit",
        "cllt": "userNameLogin",
        "dllt": "generalLogin",
        "lt": lt,
        "execution": execution
    }

    # 5. 发送 POST 请求
    print("4. 发送登录请求...")
    # 禁止自动跳转，以便我们可以检查 302 状态
    login_resp = session.post(LOGIN_URL, data=data, allow_redirects=False)

    # 6. 判断结果
    if login_resp.status_code == 302:
        redirect_url = login_resp.headers.get('Location')
        print(f"🎉 登录成功！跳转地址: {redirect_url}")
        print("Cookies:", session.cookies.get_dict())
        return True
    else:
        print("❌ 登录失败")
        # 如果失败，通常页面会返回错误提示，可以尝试解析一下
        fail_soup = BeautifulSoup(login_resp.text, 'html.parser')
        err_msg = fail_soup.find(id="showErrorTip")
        if err_msg:
            print("错误提示:", err_msg.get_text(strip=True))
        return False

if __name__ == "__main__":
    u = input("学号: ")
    p = input("密码: ")
    login_hbut(u, p)