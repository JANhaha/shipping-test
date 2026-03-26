#!/usr/bin/env python
"""直接测试Flask API端点"""

import requests
import json

print("\n【测试Flask API端点】\n")

base_url = "http://localhost:5000/api"

tests = [
    ("健康检查", f"{base_url}/health"),
    ("Baltic Exchange", f"{base_url}/baltic-indices"),
    ("舟山油价", f"{base_url}/zhoushan-bunker"),
    ("Bunker油价", f"{base_url}/bunker-prices"),
    ("USD/CNY", f"{base_url}/forex/usdcny"),
]

for name, url in tests:
    print(f"【{name}】")
    print(f"POST: {url}")
    try:
        response = requests.get(url, timeout=30)
        print(f"状态: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if 'error' in data and data['error']:
                print(f"❌ API返回错误: {data['error'][:100]}")
            elif 'data' in data:
                print(f"✓ 返回数据，项数: {len(data['data'])}")
                if len(data['data']) > 0:
                    first_item = data['data'][0]
                    print(f"  样品: {str(first_item)[:100]}")
            elif 'prices' in data:
                print(f"✓ 返回油价数据:")
                for fuel, price in data['prices'].items():
                    print(f"  - {fuel}: ${price}")
            else:
                print(f"✓ 返回数据: {str(data)[:100]}")
        else:
            print(f"❌ HTTP状态码: {response.status_code}")
            print(f"  响应: {response.text[:100]}")
    except requests.exceptions.ConnectionError:
        print(f"❌ 连接失败 - Flask可能未运行")
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时")
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    print()
