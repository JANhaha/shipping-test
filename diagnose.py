"""诊断脚本 - 测试每个数据源的实际输出"""
import sys
import json
sys.path.insert(0, r'c:\Users\user\Desktop\shipping_project\data')

from data_service_real_only import RealTimeDataService
import time

service = RealTimeDataService()

print("\n" + "="*70)
print("【诊断测试】实时数据爬取系统")
print("="*70 + "\n")

# 测试1: Baltic Exchange
print("【测试1】Baltic Exchange Indices")
print("-" * 70)
try:
    start = time.time()
    result = service.get_baltic_indices()
    elapsed = time.time() - start
    
    print(f"耗时: {elapsed:.2f}秒")
    print(f"返回结构: {list(result.keys())}")
    
    if 'error' in result and result['error']:
        print(f"❌ 错误: {result['error']}")
    elif 'data' in result:
        data = result['data']
        print(f"✓ 找到 {len(data)} 个指数")
        if data:
            print("   数据样本:")
            for idx in data[:3]:
                print(f"   - {idx.get('code', '?')} = {idx.get('value', '?')}")
    else:
        print(f"❓ 未知响应: {result}")
        
except Exception as e:
    print(f"❌ 异常: {str(e)[:200]}")

print()

# 测试2: Forex USD/CNY
print("【测试2】外汇汇率 - USD/CNY (昨日收盘价)")
print("-" * 70)
try:
    start = time.time()
    result = service.get_forex_closing_price('USDCNY')
    elapsed = time.time() - start
    
    print(f"耗时: {elapsed:.2f}秒")
    print(f"返回字段: {list(result.keys())}")
    
    if 'error' in result and result['error']:
        print(f"❌ 错误: {result['error']}")
    elif 'yesterday_close' in result:
        print(f"✓ 昨日收盘价: {result['yesterday_close']}")
        print(f"  当前价格: {result.get('current_price', 'N/A')}")
        print(f"  变化: {result.get('change', 'N/A')}")
    else:
        print(f"❓ 未知响应: {result}")
        
except Exception as e:
    print(f"❌ 异常: {str(e)[:200]}")

print()

# 测试3: Bunker Prices
print("【测试3】全球港口油价 (BunkerIndex)")
print("-" * 70)
try:
    start = time.time()
    result = service.get_bunker_prices()
    elapsed = time.time() - start
    
    print(f"耗时: {elapsed:.2f}秒")
    print(f"返回字段: {list(result.keys())}")
    
    if 'error' in result and result['error']:
        print(f"❌ 错误: {result['error']}")
    elif 'data' in result:
        data = result['data']
        print(f"✓ 找到 {len(data)} 个港口")
        if data:
            print("   港口数据:")
            for port in data[:5]:
                print(f"   - {port.get('port', '?')}: ${port.get('price', '?')}")
    else:
        print(f"❓ 未知响应: {result}")
        
except Exception as e:
    print(f"❌ 异常: {str(e)[:200]}")

print()

# 测试4: BOC USD Rate
print("【测试4】中国银行美元汇率")
print("-" * 70)
try:
    start = time.time()
    result = service.get_boc_usd_rate()
    elapsed = time.time() - start
    
    print(f"耗时: {elapsed:.2f}秒")
    print(f"返回字段: {list(result.keys())}")
    
    if 'error' in result and result['error']:
        print(f"❌ 错误: {result['error']}")
    elif 'mid_rate' in result:
        print(f"✓ 中间价: {result.get('mid_rate', 'N/A')}")
        print(f"  买入价: {result.get('buy_rate', 'N/A')}")
        print(f"  卖出价: {result.get('sell_rate', 'N/A')}")
    else:
        print(f"❓ 未知响应: {result}")
        
except Exception as e:
    print(f"❌ 异常: {str(e)[:200]}")

print()

# 测试5: Iron Ore
print("【测试5】进口矿指数")
print("-" * 70)
try:
    start = time.time()
    result = service.get_iron_ore_index()
    elapsed = time.time() - start
    
    print(f"耗时: {elapsed:.2f}秒")
    print(f"返回字段: {list(result.keys())}")
    
    if 'error' in result and result['error']:
        print(f"❌ 错误: {result['error']}")
    elif 'today' in result:
        print(f"✓ 今日: {result.get('today', 'N/A')}")
        print(f"  昨日: {result.get('yesterday', 'N/A')}")
        print(f"  变化: {result.get('change_percent', 'N/A')}%")
    else:
        print(f"❓ 未知响应: {result}")
        
except Exception as e:
    print(f"❌ 异常: {str(e)[:200]}")

print()

# 测试6: 舟山油价
print("【测试6】舟山港油价")
print("-" * 70)
try:
    start = time.time()
    result = service.get_zhoushan_bunker()
    elapsed = time.time() - start
    
    print(f"耗时: {elapsed:.2f}秒")
    print(f"返回字段: {list(result.keys())}")
    
    if 'error' in result and result['error']:
        print(f"❌ 错误: {result['error']}")
    elif 'prices' in result:
        prices = result['prices']
        print(f"✓ 找到 {len(prices)} 种油品:")
        for fuel, price in prices.items():
            print(f"   - {fuel}: ${price} USD/MT")
    else:
        print(f"❓ 未知响应: {result}")
        
except Exception as e:
    print(f"❌ 异常: {str(e)[:200]}")

print()

# 测试7: 原油期货
print("【测试7】原油期货 - CL (WTI)")
print("-" * 70)
try:
    start = time.time()
    result = service.get_crude_futures_price('CL')
    elapsed = time.time() - start
    
    print(f"耗时: {elapsed:.2f}秒")
    print(f"返回字段: {list(result.keys())}")
    
    if 'error' in result and result['error']:
        print(f"❌ 错误: {result['error']}")
    elif 'price' in result:
        print(f"✓ 价格: {result.get('price', 'N/A')}")
        print(f"  变化: {result.get('change', 'N/A')}")
        print(f"  涨幅: {result.get('change_pct', 'N/A')}")
    else:
        print(f"❓ 未知响应: {result}")
        
except Exception as e:
    print(f"❌ 异常: {str(e)[:200]}")

print()
print("="*70)
print("诊断完成")
print("="*70)

service.close()
