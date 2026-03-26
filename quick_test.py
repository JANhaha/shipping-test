"""快速测试 - 直接检查网站HTML"""
import requests
from bs4 import BeautifulSoup

print("\n【快速测试】检查网站实际返回的HTML\n")

# 测试1: Baltic Exchange
print("=" * 60)
print("1. Baltic Exchange")
print("=" * 60)
try:
    response = requests.get("https://www.balticexchange.com/en/index.html", timeout=10)
    print(f"HTTP状态码: {response.status_code}")
    print(f"内容长度: {len(response.text)} 字符")
    print(f"编码: {response.encoding}")
    
    # 检查是否包含指数代码
    text = response.text
    indices = ['BDI', 'BCI', 'BPI', 'BSI', 'BCTI', 'BAI', 'BHSI', 'BLNG', 'BLPG']
    found = [idx for idx in indices if idx in text]
    
    print(f"找到的指数代码: {found}")
    if found:
        # 显示包含BDI的上下文
        idx = text.find('BDI')
        if idx >= 0:
            print(f"BDI上下文: {text[max(0, idx-100):idx+150]}")
    print()
except Exception as e:
    print(f"错误: {e}\n")

# 测试2: Sina Finance
print("=" * 60)
print("2. Sina Finance - USD/CNY")
print("=" * 60)
try:
    response = requests.get("https://finance.sina.com.cn/money/forex/hq/USDCNY.shtml?id=27", timeout=10)
    print(f"HTTP状态码: {response.status_code}")
    print(f"内容长度: {len(response.text)} 字符")
    
    text = response.text
    # 查找金额模式
    import re
    prices = re.findall(r'\d+\.\d{2,4}', text)
    print(f"找到的数值: {prices[:10] if prices else '无'}")
    print()
except Exception as e:
    print(f"错误: {e}\n")

# 测试3: BunkerIndex
print("=" * 60)
print("3. BunkerIndex")
print("=" * 60)
try:
    response = requests.get("https://www.bunkerindex.com/", timeout=10)
    print(f"HTTP状态码: {response.status_code}")
    print(f"内容长度: {len(response.text)} 字符")
    
    text = response.text.lower()
    # 查找港口名
    ports = ['singapore', 'rotterdam', 'dubai', 'houston']
    found = [p for p in ports if p in text]
    print(f"找到的港口: {found}")
    print()
except Exception as e:
    print(f"错误: {e}\n")

# 测试4: BOC
print("=" * 60)
print("4. BOC - 中国银行汇率")
print("=" * 60)
try:
    response = requests.get("https://www.boc.cn/sourcedb/whpj/", timeout=10)
    print(f"HTTP状态码: {response.status_code}")
    print(f"内容长度: {len(response.text)} 字符")
    
    text = response.text
    # 查找美元相关内容
    if '美' in text or 'USD' in text or 'dollar' in text.lower():
        print("✓ 页面包含美元相关内容")
    else:
        print("✗ 页面不包含美元相关内容")
    print()
except Exception as e:
    print(f"错误: {e}\n")

print("快速测试完成\n")
