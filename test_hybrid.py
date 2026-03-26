#!/usr/bin/env python
"""测试混合数据服务 - 检查三种油是否都能显示"""

import sys
sys.path.insert(0, r'c:\Users\user\Desktop\shipping_project\data')

from data_service_hybrid import HybridDataService
import json

print("\n" + "="*70)
print("【混合数据服务测试】")
print("="*70 + "\n")

service = HybridDataService()

tests = [
    ("Baltic Exchange 指数", lambda: service.get_baltic_indices()),
    ("USD/CNY 外汇", lambda: service.get_forex_closing_price('USDCNY')),
    ("全球港口油价", lambda: service.get_bunker_prices()),
    ("舟山油价 (IFO380, LSMGO, VLSFO)", lambda: service.get_zhoushan_bunker()),
    ("BOC美元汇率", lambda: service.get_boc_usd_rate()),
    ("进口矿指数", lambda: service.get_iron_ore_index()),
    ("原油期货CL", lambda: service.get_crude_futures_price('CL')),
]

results = {
    'success': 0,
    'failed': 0,
    'details': []
}

for test_name, test_func in tests:
    print(f"\n【{test_name}】")
    print("-" * 70)
    try:
        result = test_func()
        
        if result.get('error'):
            print(f"❌ 错误: {result['error']}")
            results['failed'] += 1
            results['details'].append({
                'test': test_name,
                'status': 'error',
                'message': result['error']
            })
        else:
            print(f"✓ 成功!")
            
            # 显示关键信息
            if 'data' in result:
                print(f"  数据项数: {len(result['data'])}")
                if test_name == "舟山油价 (IFO380, LSMGO, VLSFO)":
                    # 对于舟山油价，显示具体的三种油
                    for fuel, price in result.get('prices', {}).items():
                        print(f"    - {fuel}: ${price} USD/MT")
                elif 'count' in result:
                    # 显示前2项
                    for item in result['data'][:2]:
                        if 'code' in item:
                            print(f"    - {item['code']}: {item.get('value', '?')}")
                        elif 'port' in item:
                            print(f"    - {item['port']}: ${item.get('price', '?')}")
            elif 'yesterday_close' in result:
                print(f"  昨日收盘价: {result['yesterday_close']}")
            elif 'mid_rate' in result:
                print(f"  美元中间价: {result['mid_rate']}")
            elif 'today' in result:
                print(f"  今日: {result['today']}")
            elif 'price' in result:
                print(f"  价格: {result['price']}")
            elif 'prices' in result:
                print(f"  油品数: {len(result['prices'])}")
                for fuel, price in result['prices'].items():
                    print(f"    - {fuel}: ${price}")
            
            results['success'] += 1
            results['details'].append({
                'test': test_name,
                'status': 'success'
            })
    except Exception as e:
        print(f"❌ 异常: {e}")
        results['failed'] += 1
        results['details'].append({
            'test': test_name,
            'status': 'exception',
            'message': str(e)
        })

print("\n" + "="*70)
print("【测试总结】")
print("="*70)
print(f"成功: {results['success']}")
print(f"失败: {results['failed']}")
print(f"通过率: {results['success']}/{len(tests)} ({results['success']*100//len(tests)}%)")
print("\n")

service.close()
