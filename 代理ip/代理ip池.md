# 代理池 API 使用文档

API累计调用次数：**14,639,953** 次

## API 接口说明

本API提供获取高质量代理IP的服务，支持通过协议筛选代理，并可自定义获取数量。

### 接口地址

```
GET https://proxy.scdn.io/api/get_proxy.php
```

### 快速示例

以下是一些常用的API调用示例，点击链接可以直接查看返回结果：

1. 获取1个支持SOCKS4协议的代理：

https://proxy.scdn.io/api/get_proxy.php?protocol=socks4&count=1

2. 获取2个支持HTTP协议的代理：

https://proxy.scdn.io/api/get_proxy.php?protocol=http&count=2

3. 获取20个支持HTTPS协议的代理：

https://proxy.scdn.io/api/get_proxy.php?protocol=https&count=20

4. 获取5个任意类型的代理：

https://proxy.scdn.io/api/get_proxy.php?protocol=all&count=5

5. 获取3个中国的HTTPS代理：

https://proxy.scdn.io/api/get_proxy.php?protocol=https&count=3&country_code=CN

### 请求参数

| 参数名       | 类型    | 必选 | 说明                                                         |
| ------------ | ------- | ---- | ------------------------------------------------------------ |
| protocol     | string  | 否   | 代理协议类型。支持的值：`http`, `https`, `socks4`, `socks5`。 默认为 `all`，获取任意可用协议的代理。 **注意：** 如果一个代理同时支持HTTP和SOCKS5，当您请求`http`时，它也可能被返回。 |
| count        | integer | 否   | 获取代理数量，默认1个，最大20个。                            |
| country_code | string  | 否   | 指定代理的ISO 3166-1国家代码（2位字母）。例如: `CN` (中国), `US` (美国)。 默认为 `all`，获取任意国家的代理。 |

### 返回示例

```
{
    "code": 200,
    "message": "success",
    "data": {
        "proxies": [
            "192.168.1.1:8080",
            "10.0.0.1:3128"
        ],
        "count": 2
    }
}
```

### 示例代码

- ### 示例代码

  - [PHP](https://proxy.scdn.io/api_docs.php#php)
  - [Python](https://proxy.scdn.io/api_docs.php#python)
  - [JavaScript](https://proxy.scdn.io/api_docs.php#javascript)

  ```
  import requests
  
  url = 'https://proxy.scdn.io/api/get_proxy.php'
  params = {
      'protocol': 'http',
      'count': 2
  }
  response = requests.get(url, params=params)
  data = response.json()
  print(data)
  ```