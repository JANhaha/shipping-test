"""快速测试数据服务"""
import sys
sys.path.insert(0, r'c:\Users\user\Desktop\shipping_project')

from data.data_service_real_only import RealTimeDataService

def test_service():
    service = RealTimeDataService()
    
    print("\n" + "="*60)
    print("TEST 1: Baltic Exchange Indices")
    print("="*60)
    try:
        result = service.get_baltic_indices()
        if 'error' in result:
            print(f"ERROR: {result['error']}")
        elif 'data' in result:
            print(f"SUCCESS: Found {len(result['data'])} indices")
            for idx in result['data']:
                print(f"  - {idx['code']}: {idx['value']}")
        else:
            print(f"UNKNOWN RESPONSE: {result}")
    except Exception as e:
        print(f"EXCEPTION: {e}")
    
    print("\n" + "="*60)
    print("TEST 2: Forex USD/CNY")
    print("="*60)
    try:
        result = service.get_forex_closing_price('USDCNY')
        if 'error' in result:
            print(f"ERROR: {result['error']}")
        elif 'yesterday_close' in result:
            print(f"SUCCESS: Yesterday close = {result['yesterday_close']}")
        else:
            print(f"UNKNOWN RESPONSE: {result}")
    except Exception as e:
        print(f"EXCEPTION: {e}")
    
    print("\n" + "="*60)
    print("TEST 3: Bunker Prices")
    print("="*60)
    try:
        result = service.get_bunker_prices()
        if 'error' in result:
            print(f"ERROR: {result['error']}")
        elif 'data' in result:
            print(f"SUCCESS: Found {len(result['data'])} ports")
            for port in result['data'][:3]:
                print(f"  - {port['port']}: ${port['price']}")
        else:
            print(f"UNKNOWN RESPONSE: {result}")
    except Exception as e:
        print(f"EXCEPTION: {e}")
    
    print("\n" + "="*60)
    print("TEST 4: BOC USD Rate")
    print("="*60)
    try:
        result = service.get_boc_usd_rate()
        if 'error' in result:
            print(f"ERROR: {result['error']}")
        elif 'mid_rate' in result:
            print(f"SUCCESS: Mid rate = {result['mid_rate']}")
        else:
            print(f"UNKNOWN RESPONSE: {result}")
    except Exception as e:
        print(f"EXCEPTION: {e}")
    
    service.close()
    print("\n" + "="*60)
    print("TESTS COMPLETE")
    print("="*60 + "\n")

if __name__ == '__main__':
    test_service()
