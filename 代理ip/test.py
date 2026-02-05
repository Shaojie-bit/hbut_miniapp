import requests
import time
import concurrent.futures

# ================= 配置区域 =================
# 1. 代理API地址 (你提供的)
API_URL = 'https://proxy.scdn.io/api/get_proxy.php'

# 2. 目标网站：必须是你们学校教务处！
# 测试百度没意义，因为百度不封IP，但学校防火墙会封。
# 建议填入：教务系统登录页的完整URL
TARGET_URL = 'http://jwxt.hbut.edu.cn/'  

# 3. 超时时间：超过这个秒数没连上算失败
# 免费代理通常很慢，设为 3-5 秒比较合理
TIMEOUT = 3 
# ===========================================

def get_proxies():
    """从API获取代理列表"""
    params = {
        'protocol': 'http', # 如果教务网是HTTPS，这里建议改为 'https'
        'count': 200,
        'country_code': 'CN' # 建议加上CN，只要国内的，国外的访问学校通常很慢
    }
    try:
        print(f"正在从 API 获取代理 IP...")
        response = requests.get(API_URL, params=params, timeout=10, verify=False)
        data = response.json()
        
        if data.get('code') == 200:
            proxy_list = data['data']['proxies']
            print(f"成功获取到 {len(proxy_list)} 个原始代理 IP")
            return proxy_list
        else:
            print("API 返回错误:", data)
            return []
    except Exception as e:
        print(f"获取代理失败: {e}")
        return []

def check_proxy(proxy_ip):
    """测试单个代理IP的质量"""
    # 构造代理字典
    proxies = {
        "http": f"http://{proxy_ip}",
        "https": f"http://{proxy_ip}",
    }
    
    # 模拟浏览器头，防止因没有User-Agent被学校直接拒绝
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    start_time = time.time()
    result = {
        "ip": proxy_ip,
        "status": "失败",
        "latency": 0,
        "msg": ""
    }

    try:
        # 发起请求
        resp = requests.get(TARGET_URL, proxies=proxies, headers=headers, timeout=TIMEOUT)
        
        # 计算耗时
        elapsed = (time.time() - start_time) * 1000 # 转换为毫秒
        result["latency"] = int(elapsed)

        # 判断状态码：只有200才算完全成功
        if resp.status_code == 200:
            result["status"] = "成功"
            result["msg"] = "连接正常"
        else:
            result["status"] = "失败"
            result["msg"] = f"状态码 {resp.status_code}"
            
    except requests.exceptions.ConnectTimeout:
        result["msg"] = "连接超时"
    except requests.exceptions.ProxyError:
        result["msg"] = "代理连接被拒绝"
    except Exception as e:
        result["msg"] = "其他错误"

    return result

def main():
    # 1. 获取IP
    proxies = get_proxies()
    if not proxies:
        return

    print(f"\n开始测试 {len(proxies)} 个代理 (超时设定: {TIMEOUT}秒)...")
    print("-" * 60)
    print(f"{'IP地址':<25} {'状态':<10} {'延迟(ms)':<10} {'详情'}")
    print("-" * 60)

    available_proxies = []

    # 2. 多线程并发测试
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # 提交所有任务
        futures = {executor.submit(check_proxy, ip): ip for ip in proxies}
        
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            
            # 打印结果
            if res["status"] == "成功":
                print(f"\033[92m{res['ip']:<25} {res['status']:<10} {res['latency']:<10} {res['msg']}\033[0m")
                available_proxies.append(res)
            else:
                print(f"\033[91m{res['ip']:<25} {res['status']:<10} ----       {res['msg']}\033[0m")

    print("-" * 60)
    print(f"测试结束。可用代理: {len(available_proxies)} / {len(proxies)}")
    
    # 这里你可以把 available_proxies 保存到数据库或内存中供后续使用
    if available_proxies:
        best_proxy = min(available_proxies, key=lambda x: x['latency'])
        print(f"推荐使用最快代理: {best_proxy['ip']} (延迟 {best_proxy['latency']}ms)")

if __name__ == "__main__":
    main()