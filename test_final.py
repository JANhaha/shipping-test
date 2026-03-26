#!/usr/bin/env python
"""测试最终版本的数据服务"""

import sys
sys.path.insert(0, r'c:\Users\user\Desktop\shipping_project\data')

from data_service_final import UltimateDataService

print("\n" + "="*70)
print("【测试终极数据服务】")
print("="*70 + "\n")

service = UltimateDataService()

# 测试1
print("\n【TEST 1】Baltic Exchange")
result = service.get_baltic_indices()
if result.get('data'):
    print(f"✓ 成功！找到 {len(result['data'])} 个指数")
    for idx in result['data'][:3]:
        print(f"  - {idx['code']}: {idx['value']}")
else:
    print(f"✗ 失败: {result.get('error', '未知错误')}")

# 测试2
print("\n【TEST 2】外汇 USD/CNY")
result = service.get_forex_closing_price('USDCNY')
if result.get('yesterday_close'):
    print(f"✓ 成功! 昨日收盘价: {result['yesterday_close']}")
else:
    print(f"✗ 失败: {result.get('error', '未知错误')}")

# 测试3
print("\n【TEST 3】全球港口油价")
result = service.get_bunker_prices()
if result.get('data'):
    print(f"✓ 成功! 找到 {len(result['data'])} 个港口")
    for port in result['data'][:3]:
        print(f"  - {port['port']}: ${port['price']}")
else:
    print(f"✗ 失败: {result.get('error', '未知错误')}")

# 测试4
print("\n【TEST 4】舟山油价 (三种油)")
result = service.get_zhoushan_bunker()
if result.get('prices'):
    print(f"✓ 成功! 找到 {len(result['prices'])} 种油")
    for fuel, price in result['prices'].items():
        print(f"  - {fuel}: ${price} USD/MT")
else:
    print(f"✗ 失败: {result.get('error', '未知错误')}")

print("\n" + "="*70)
print("测试完成")
print("="*70 + "\n")
