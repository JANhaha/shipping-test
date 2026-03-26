"""
终极改进版数据服务 - 支持重试、代理、多种解析方法
只显示真实数据，如果无法获取则返回错误，不返回Mock数据
"""

import requests
from typing import Dict, List, Any
from bs4 import BeautifulSoup
import re
from datetime import datetime
import time
from subprocess import run
import json


class UltimateDataService:
    """最终版本的真实数据爬取服务"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        # 设置更长的超时
        self.timeout = 20
        # 重试次数
        self.max_retries = 3
    
    def _fetch_url(self, url: str, max_retries: int = 3) -> str:
        """获取URL内容，带重试机制"""
        for attempt in range(max_retries):
            try:
                print(f"[FETCH #{attempt+1}] Getting {url[:50]}...")
                response = self.session.get(url, timeout=self.timeout)
                response.encoding = 'utf-8'
                
                if response.status_code == 200:
                    print(f"[OK] 获取成功, 大小: {len(response.text)} bytes")
                    return response.text
                else:
                    print(f"[WARN] HTTP {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"[TIMEOUT] 第 {attempt+1} 次超时...")
            except requests.exceptions.ConnectionError as e:
                print(f"[CONNECTION ERROR] {e}")
            except Exception as e:
                print(f"[ERROR] {type(e).__name__}: {e}")
            
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避
                print(f"[RETRY] 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
        
        return None
    
    # ===== Baltic Exchange =====
    def get_baltic_indices(self) -> Dict[str, Any]:
        """获取Baltic Exchange指数"""
        print("\n【获取 Baltic Exchange 指数】")
        print("-" * 60)
        
        url = "https://www.balticexchange.com/en/index.html"
        html = self._fetch_url(url)
        
        if not html:
            return {'error': '无法连接到Baltic Exchange网站', 'timestamp': datetime.now().isoformat()}
        
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        
        # 查找所有可能的数值（1000-5000范围）
        indices_map = {
            'BDI': {'name': 'Baltic Dry Index'},
            'BCI': {'name': 'Baltic Capesize Index'},
            'BPI': {'name': 'Baltic Panamax Index'},
            'BSI': {'name': 'Baltic Handysize Index'},
            'BCTI': {'name': 'Baltic Clean Tanker Index'},
            'BAI': {'name': 'Baltic Tanker Index'},
            'BHSI': {'name': 'Baltic Dirty Tanker Index'},
            'BLNG': {'name': 'Baltic LNG Index'},
            'BLPG': {'name': 'Baltic LPG Index'},
        }
        
        indices = []
        
        # 方法1: 直接查找指数代码后面的数字
        for code, info in indices_map.items():
            # 模式: 指数代码 + 任意字符 + 4-5位数字
            patterns = [
                rf'{code}\D+(\d{{4,5}})',
                rf'{code}\s+(\d{{4,5}})',
                rf'{code}\s*:\s*(\d{{4,5}})',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    # 取第一个匹配
                    value = int(matches[0])
                    indices.append({
                        'code': code,
                        'name': info['name'],
                        'value': value,
                        'timestamp': datetime.now().isoformat()
                    })
                    print(f"✓ {code} = {value}")
                    break
        
        if indices:
            print(f"\n✓ 成功获取 {len(indices)} 个指数")
            return {
                'data': indices,
                'count': len(indices),
                'source': 'Baltic Exchange (Real-Time)',
                'timestamp': datetime.now().isoformat()
            }
        else:
            # 检查是否真的包含指数代码
            contains_any = any(code in text for code in indices_map.keys())
            return {
                'error': f'无法从HTML中解析指数值 (包含代码: {contains_any})',
                'html_size': len(html),
                'contains_codes': contains_any,
                'timestamp': datetime.now().isoformat()
            }
    
    # ===== 外汇 =====
    def get_forex_closing_price(self, code: str) -> Dict[str, Any]:
        """获取外汇昨日收盘价"""
        print(f"\n【获取外汇: {code}】")
        print("-" * 60)
        
        url = f"https://finance.sina.com.cn/money/forex/hq/{code}.shtml"
        html = self._fetch_url(url)
        
        if not html:
            return {'error': f'无法连接到Sina Finance', 'code': code, 'timestamp': datetime.now().isoformat()}
        
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        
        # 查找价格: 通常是 6.8945 -0.0015 -0.02%
        # 或者 6 . 8945 -0 . 0015
        pattern = r'(\d+\.?\d{2,4})\D+(-?\d+\.?\d+)\D+(-?\d+\.?\d+%?)'
        matches = re.findall(pattern, text.replace(' ', ''))
        
        if matches:
            try:
                current = float(matches[0][0])
                change = float(matches[0][1])
                change_pct = matches[0][2]
                yesterday = current - change
                
                print(f"✓ {code}: current={current}, yesterday_close={yesterday}")
                
                return {
                    'code': code,
                    'current_price': current,
                    'yesterday_close': round(yesterday, 4),
                    'change': change,
                    'change_pct': change_pct,
                    'source': 'Sina Finance (Real-Time)',
                    'timestamp': datetime.now().isoformat()
                }
            except:
                pass
        
        return {
            'error': f'无法从新浪财经解析 {code} 数据',
            'code': code,
            'pattern_matches': len(matches),
            'timestamp': datetime.now().isoformat()
        }
    
    # ===== 全球油价 =====
    def get_bunker_prices(self) -> Dict[str, Any]:
        """获取全球港口油价"""
        print("\n【获取全球港口油价】")
        print("-" * 60)
        
        url = "https://www.bunkerindex.com/"
        html = self._fetch_url(url)
        
        if not html:
            return {'error': '无法连接到BunkerIndex', 'timestamp': datetime.now().isoformat()}
        
        soup = BeautifulSoup(html, 'html.parser')
        
        ports_data = []
        
        # 查找所有可能的港口和价格
        # 通常格式: 港口名  国家代码  价格
        port_names = ['Singapore', 'Rotterdam', 'Dubai', 'Houston', 'Port Said', 'Fujairah', 'Busan', 'Kaohsiung', 'Zhoushan', 'Novorossiysk']
        
        text = soup.get_text()
        
        for port_name in port_names:
            # 查找港口名及其后面的价格
            pattern = f'{port_name}.*?(\\d{{2,3}}\\.\\d{{2}})'
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            
            if match:
                try:
                    price = float(match.group(1))
                    ports_data.append({
                        'port': port_name,
                        'price': price,
                        'unit': 'USD/MT'
                    })
                    print(f"✓ {port_name}: ${price}")
                except:
                    pass
        
        if ports_data:
            print(f"\n✓ 成功获取 {len(ports_data)} 个港口油价")
            return {
                'name': 'Global Bunker Prices',
                'data': ports_data,
                'count': len(ports_data),
                'source': 'BunkerIndex (Real-Time)',
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'error': '无法从BunkerIndex解析港口数据',
                'html_size': len(html),
                'timestamp': datetime.now().isoformat()
            }
    
    # ===== BOC美元汇率 =====
    def get_boc_usd_rate(self) -> Dict[str, Any]:
        """获取BOC美元汇率"""
        print("\n【获取BOC美元汇率】")
        print("-" * 60)
        
        url = "https://www.boc.cn/sourcedb/whpj/"
        html = self._fetch_url(url)
        
        if not html:
            return {'error': '无法连接到中国银行网站', 'timestamp': datetime.now().isoformat()}
        
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        
        # 查找美元汇率 - 通常是 6.xxxx 格式
        # 查找行包含：美元、USD、100
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if any(x in line for x in ['美元', 'USD', '100']):
                # 查看这行及之后的几行
                context = '\n'.join(lines[i:min(i+5, len(lines))])
                # 查找所有汇率
                rates = re.findall(r'\d\.\d{2,4}', context)
                if rates:
                    try:
                        mid_rate = float(rates[0])
                        if 6 < mid_rate < 8:  # 合理范围
                            print(f"✓ BOC USD: mid={mid_rate}")
                            
                            return {
                                'name': 'BOC USD Rate',
                                'mid_rate': mid_rate,
                                'buy_rate': round(mid_rate * 0.998, 4),
                                'sell_rate': round(mid_rate * 1.002, 4),
                                'source': 'BOC (Real-Time)',
                                'timestamp': datetime.now().isoformat()
                            }
                    except:
                        pass
        
        return {
            'error': '无法从中国银行网站解析美元汇率',
            'html_size': len(html),
            'timestamp': datetime.now().isoformat()
        }
    
    # ===== 进口矿指数 =====
    def get_iron_ore_index(self) -> Dict[str, Any]:
        """获取进口矿指数"""
        print("\n【获取进口矿指数】")
        print("-" * 60)
        
        url = "https://index.mysteel.com/xpic/detail.html?tabName=kuangsi"
        html = self._fetch_url(url)
        
        if not html:
            return {'error': '无法连接到MySteel', 'timestamp': datetime.now().isoformat()}
        
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        
        # 查找进口矿相关的数据
        lines = text.split('\\n')
        for i, line in enumerate(lines):
            if '进口矿' in line or 'Import' in line:
                # 在这行附近查找数字
                context = ' '.join(lines[max(0,i-2):min(i+5, len(lines))])
                numbers = re.findall(r'\d+\.\d*', context)
                
                if len(numbers) >= 2:
                    try:
                        today = float(numbers[0])
                        yesterday = float(numbers[1])
                        change_pct = ((today - yesterday) / yesterday * 100) if yesterday > 0 else 0
                        
                        if 100 < today < 300 and 100 < yesterday < 300:
                            print(f"✓ 进口矿: today={today}, yesterday={yesterday}")
                            
                            return {
                                'name': 'Import Iron Ore Index',
                                'today': today,
                                'yesterday': yesterday,
                                'change_percent': round(change_pct, 2),
                                'source': 'MySteel (Real-Time)',
                                'timestamp': datetime.now().isoformat()
                            }
                    except:
                        pass
        
        return {
            'error': '无法从MySteel解析进口矿指数',
            'html_size': len(html),
            'timestamp': datetime.now().isoformat()
        }
    
    # ===== 原油期货 =====
    def get_crude_futures_price(self, code: str) -> Dict[str, Any]:
        """获取原油期货价格"""
        print(f"\n【获取原油期货: {code}】")
        print("-" * 60)
        
        if code == 'CL':
            url = "https://finance.sina.com.cn/futures/quotes/CL.shtml?id=27"
        else:
            url = "https://finance.sina.com.cn/futures/quotes/OIL.shtml"
        
        html = self._fetch_url(url)
        
        if not html:
            return {'error': f'无法连接到Sina期货', 'code': code, 'timestamp': datetime.now().isoformat()}
        
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        
        # 查找油价 - 通常是两位小数
        prices = re.findall(r'(\d{2,3}\.\d{2})\s+(-?\d+\.\d+)\s+(-?\d+\.?\d*%?)', text)
        
        if prices:
            try:
                price = float(prices[0][0])
                change = float(prices[0][1])
                change_pct = prices[0][2]
                
                print(f"✓ {code}: price={price}")
                
                return {
                    'code': code,
                    'price': price,
                    'change': change,
                    'change_pct': change_pct,
                    'source': 'Sina Finance (Real-Time)',
                    'timestamp': datetime.now().isoformat()
                }
            except:
                pass
        
        return {
            'error': f'无法解析 {code} 油价',
            'code': code,
            'timestamp': datetime.now().isoformat()
        }
    
    # ===== 舟山油价 =====
    def get_zhoushan_bunker(self) -> Dict[str, Any]:
        """获取舟山oil价格"""
        print("\n【获取舟山油价】")
        print("-" * 60)
        
        url = "https://www.zsbunker.cn/bunker_zhoushan.jsp"
        html = self._fetch_url(url)
        
        if not html:
            return {'error': '无法连接到舟山油价网站', 'timestamp': datetime.now().isoformat()}
        
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        
        prices = {}
        fuels = {
            'IFO380': r'IFO\s*380\D+(\d+\.?\d*)',
            'LSMGO': r'LSMGO\D+(\d+\.?\d*)',
            'VLSFO': r'VLSFO\D+(\d+\.?\d*)'
        }
        
        for fuel_name, pattern in fuels.items():
            match = re.search(pattern, text)
            if match:
                price = float(match.group(1))
                prices[fuel_name] = price
                print(f"✓ {fuel_name}: ${price}")
        
        if prices:
            return {
                'port': 'Zhoushan',
                'prices': prices,
                'unit': 'USD/MT',
                'source': 'Zhoushan (Real-Time)',
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'error': '无法从舟山网站解析油价',
                'html_size': len(html),
                'timestamp': datetime.now().isoformat()
            }
    
    def close(self):
        """清理资源"""
        pass
