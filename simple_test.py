#!/usr/bin/env python
"""简单测试 - 不使用Selenium，只测试HTTP请求"""

import requests
from bs4 import BeautifulSoup
import re
import json

print("\n【简单HTTP测试】\n")

# 测试1: Baltic Exchange
print("="*60)
print("测试1: Baltic Exchange")
print("="*60)
try:
    r = requests.get("https://www.balticexchange.com/en/index.html", timeout=10)
    print(f"状态: {r.status_code}")
    print(f"长度: {len(r.text)} chars")
    
    # 查找指数
    indices = ['BDI', 'BCI', 'BPI']
    found = [idx for idx in indices if idx in r.text]
    print(f"找到的指数代码: {found}")
    
    if 'BDI' in r.text:
        idx = r.text.find('BDI')
        snippet = r.text[max(0,idx-50):idx+100]
        print(f"BDI 上下文:")
        print(f"  {snippet[:150]}")
    print()
except requests.exceptions.RequestException as e:
    print(f"错误: {type(e).__name__}: {e}")
    print()

# 测试2: Bunker Index
print("="*60)
print("测试2: BunkerIndex (最可能成功)")
print("="*60)
try:
    r = requests.get("https://www.bunkerindex.com/", timeout=10)
    print(f"状态: {r.status_code}")
    print(f"长度: {len(r.text)} chars")
    
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # 查找所有表格
    tables = soup.find_all('table')
    print(f"找到 {len(tables)} 个表格")
    
    # 查找港口
    ports = ['Singapore', 'Rotterdam', 'Dubai', 'Houston']
    found_ports = []
    text = soup.get_text().lower()
    for port in ports:
        if port.lower() in text:
            found_ports.append(port)
    
    print(f"找到的港口: {found_ports}")
    
    # 查找价格
    prices = re.findall(r'\d{2,3}\.\d{2}', soup.get_text())
    if prices:
        print(f"找到的价格 (前5个): {prices[:5]}")
    print()
except requests.exceptions.RequestException as e:
    print(f"错误: {type(e).__name__}: {e}")
    print()

# 测试3: Sina Forex
print("="*60)
print("测试3: Sina Finance - USD/CNY")
print("="*60)
try:
    r = requests.get("https://finance.sina.com.cn/money/forex/hq/USDCNY.shtml", timeout=10)
    print(f"状态: {r.status_code}")
    print(f"长度: {len(r.text)} chars")
    
    # 查找价格格式
    prices = re.findall(r'\d+\.\d{2,4}', r.text)
    if prices:
        print(f"找到的数值 (前10个): {prices[:10]}")
    else:
        print("未找到价格")
    print()
except requests.exceptions.RequestException as e:
    print(f"错误: {type(e).__name__}: {e}")
    print()

print("="*60)
print("测试完成")
print("="*60 + "\n")
