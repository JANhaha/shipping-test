"""
超快速数据服务 - 快速失败，短超时
用于演示和快速测试的实时爬取服务
"""

import requests
from typing import Dict, Any
from bs4 import BeautifulSoup
import re
from datetime import datetime
import threading
import time


class FastDataService:
    """快速失败的数据服务 - 短超时确保不会卡住"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        # 超短超时 - 3秒后失败而不是等待
        self.timeout = 3
        self.cache = {}
        self.cache_time = {}
        self.cache_duration = 300  # 5分钟缓存
    
    def _get_cached(self, key: str) -> Any:
        """获取缓存的数据"""
        if key in self.cache:
            if time.time() - self.cache_time[key] < self.cache_duration:
                return self.cache[key]
            else:
                del self.cache[key]
                del self.cache_time[key]
        return None
    
    def _set_cache(self, key: str, value: Any):
        """缓存数据"""
        self.cache[key] = value
        self.cache_time[key] = time.time()
    
    def _fetch_quick(self, url: str, timeout: int = 3) -> tuple:
        """快速获取URL - 短超时"""
        try:
            response = self.session.get(url, timeout=timeout)
            if response.status_code == 200:
                response.encoding = 'utf-8'
                return True, response.text
            else:
                return False, f"HTTP {response.status_code}"
        except requests.exceptions.Timeout:
            return False, "超时"
        except requests.exceptions.ConnectionError:
            return False, "连接失败"
        except Exception as e:
            return False, str(e)[:30]
    
    # ===== Baltic Exchange =====
    def get_baltic_indices(self) -> Dict[str, Any]:
        """获取Baltic Exchange指数"""
        cache_key = 'baltic'
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        url = "https://www.balticexchange.com/en/index.html"
        success, content = self._fetch_quick(url, timeout=3)
        
        if not success:
            result = {'error': f'无法连接到Baltic Exchange: {content}', 'timestamp': datetime.now().isoformat()}
            self._set_cache(cache_key, result)
            return result
        
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        indices_map = {
            'BDI': 'Baltic Dry Index',
            'BCI': 'Baltic Capesize Index',
            'BPI': 'Baltic Panamax Index',
            'BSI': 'Baltic Handysize Index',
            'BCTI': 'Baltic Clean Tanker Index',
            'BAI': 'Baltic Tanker Index',
            'BHSI': 'Baltic Dirty Tanker Index',
            'BLNG': 'Baltic LNG Index',
            'BLPG': 'Baltic LPG Index',
        }
        
        indices = []
        
        for code, name in indices_map.items():
            # 基础正则表达式
            pattern = rf'{code}\D+(\d{{4}})'
            matches = re.findall(pattern, text, re.IGNORECASE)
            
            if matches:
                try:
                    value = int(matches[0])
                    if 1000 <= value <= 10000:
                        indices.append({
                            'code': code,
                            'name': name,
                            'value': value,
                            'timestamp': datetime.now().isoformat()
                        })
                except:
                    pass
        
        result = {
            'data': indices if indices else [],
            'count': len(indices),
            'error': None if indices else '无法解析指数',
            'source': 'Baltic Exchange',
            'timestamp': datetime.now().isoformat()
        }
        
        self._set_cache(cache_key, result)
        return result
    
    # ===== 外汇 =====
    def get_forex_closing_price(self, code: str) -> Dict[str, Any]:
        """获取外汇昨日收盘价"""
        cache_key = f'forex_{code}'
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        url = f"https://finance.sina.com.cn/money/forex/hq/{code}.shtml"
        success, content = self._fetch_quick(url, timeout=3)
        
        if not success:
            result = {
                'error': f'无法访问Sina Finance',
                'code': code,
                'timestamp': datetime.now().isoformat()
            }
            self._set_cache(cache_key, result)
            return result
        
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        # 查找价格
        pattern = r'(\d+\.\d{2,4})\D+(-?\d+\.\d+)'
        matches = re.findall(pattern, text)
        
        if matches:
            try:
                current = float(matches[0][0])
                change = float(matches[0][1])
                yesterday = current - change
                
                result = {
                    'code': code,
                    'current_price': current,
                    'yesterday_close': round(yesterday, 4),
                    'change': change,
                    'change_pct': '',
                    'source': 'Sina Finance',
                    'timestamp': datetime.now().isoformat()
                }
                
                self._set_cache(cache_key, result)
                return result
            except:
                pass
        
        result = {
            'error': '无法解析价格',
            'code': code,
            'timestamp': datetime.now().isoformat()
        }
        
        self._set_cache(cache_key, result)
        return result
    
    # ===== 全球港口油价 =====
    def get_bunker_prices(self) -> Dict[str, Any]:
        """获取全球港口油价"""
        cache_key = 'bunker'
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        url = "https://www.bunkerindex.com/"
        success, content = self._fetch_quick(url, timeout=3)
        
        if not success:
            result = {'error': f'无法连接到BunkerIndex', 'timestamp': datetime.now().isoformat()}
            self._set_cache(cache_key, result)
            return result
        
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        ports_data = []
        port_list = ['Singapore', 'Rotterdam', 'Dubai', 'Houston']
        
        for port_name in port_list:
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
                except:
                    pass
        
        result = {
            'name': 'Global Bunker Prices',
            'data': ports_data if ports_data else [],
            'count': len(ports_data),
            'error': None if ports_data else '无法解析',
            'source': 'BunkerIndex',
            'timestamp': datetime.now().isoformat()
        }
        
        self._set_cache(cache_key, result)
        return result
    
    # ===== BOC美元汇率 =====
    def get_boc_usd_rate(self) -> Dict[str, Any]:
        """获取BOC美元汇率"""
        cache_key = 'boc'
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        url = "https://www.boc.cn/sourcedb/whpj/"
        success, content = self._fetch_quick(url, timeout=3)
        
        if not success:
            result = {'error': f'无法连接到中国银行', 'timestamp': datetime.now().isoformat()}
            self._set_cache(cache_key, result)
            return result
        
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        # 查找美元汇率
        rates = re.findall(r'\d\.\d{2,4}', text)
        if rates:
            try:
                mid_rate = float(rates[0])
                if 6 < mid_rate < 8:
                    result = {
                        'name': 'BOC USD Rate',
                        'mid_rate': mid_rate,
                        'buy_rate': round(mid_rate * 0.998, 4),
                        'sell_rate': round(mid_rate * 1.002, 4),
                        'source': 'BOC',
                        'timestamp': datetime.now().isoformat()
                    }
                    self._set_cache(cache_key, result)
                    return result
            except:
                pass
        
        result = {'error': '无法解析', 'timestamp': datetime.now().isoformat()}
        self._set_cache(cache_key, result)
        return result
    
    # ===== 进口矿指数 =====
    def get_iron_ore_index(self) -> Dict[str, Any]:
        """获取进口矿指数"""
        cache_key = 'ore'
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        url = "https://index.mysteel.com/xpic/detail.html?tabName=kuangsi"
        success, content = self._fetch_quick(url, timeout=3)
        
        if not success:
            result = {'error': '无法连接', 'timestamp': datetime.now().isoformat()}
            self._set_cache(cache_key, result)
            return result
        
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        # 查找进口矿
        numbers = re.findall(r'\d+\.\d*', text)
        if len(numbers) >= 2:
            try:
                today = float(numbers[0])
                yesterday = float(numbers[1])
                if 100 < today < 300 and 100 < yesterday < 300:
                    change_pct = ((today - yesterday) / yesterday * 100) if yesterday > 0 else 0
                    
                    result = {
                        'name': 'Iron Ore Index',
                        'today': today,
                        'yesterday': yesterday,
                        'change_percent': round(change_pct, 2),
                        'source': 'MySteel',
                        'timestamp': datetime.now().isoformat()
                    }
                    self._set_cache(cache_key, result)
                    return result
            except:
                pass
        
        result = {'error': '无法解析', 'timestamp': datetime.now().isoformat()}
        self._set_cache(cache_key, result)
        return result
    
    # ===== 原油期货 =====
    def get_crude_futures_price(self, code: str) -> Dict[str, Any]:
        """获取原油期货价格"""
        cache_key = f'crude_{code}'
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        if code == 'CL':
            url = "https://finance.sina.com.cn/futures/quotes/CL.shtml"
        else:
            url = "https://finance.sina.com.cn/futures/quotes/OIL.shtml"
        
        success, content = self._fetch_quick(url, timeout=3)
        
        if not success:
            result = {'error': '无法连接', 'code': code, 'timestamp': datetime.now().isoformat()}
            self._set_cache(cache_key, result)
            return result
        
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        prices = re.findall(r'(\d{2,3}\.\d{2})\s+(-?\d+\.\d*)', text)
        
        if prices:
            try:
                price = float(prices[0][0])
                change = float(prices[0][1]) if prices[0][1] else 0
                
                result = {
                    'code': code,
                    'price': price,
                    'change': change,
                    'change_pct': '',
                    'source': 'Sina Finance',
                    'timestamp': datetime.now().isoformat()
                }
                self._set_cache(cache_key, result)
                return result
            except:
                pass
        
        result = {'error': '无法解析', 'code': code, 'timestamp': datetime.now().isoformat()}
        self._set_cache(cache_key, result)
        return result
    
    # ===== 舟山油价 - 三种油 =====
    def get_zhoushan_bunker(self) -> Dict[str, Any]:
        """获取舟山港口油价 - 三种油品: IFO380, LSMGO, VLSFO"""
        cache_key = 'zhoushan'
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        url = "https://www.zsbunker.cn/bunker_zhoushan.jsp"
        success, content = self._fetch_quick(url, timeout=3)
        
        if not success:
            result = {'error': '无法连接', 'timestamp': datetime.now().isoformat()}
            self._set_cache(cache_key, result)
            return result
        
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        prices = {}
        
        # 查找三种油品
        fuels = {
            'IFO380': r'IFO\s*380\D+(\d+\.?\d*)',
            'LSMGO': r'LSMGO\D+(\d+\.?\d*)',
            'VLSFO': r'VLSFO\D+(\d+\.?\d*)'
        }
        
        for fuel_name, pattern in fuels.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    price = float(match.group(1))
                    if 200 < price < 800:
                        prices[fuel_name] = price
                except:
                    pass
        
        result = {
            'port': 'Zhoushan',
            'prices': prices if prices else {},
            'count': len(prices),
            'unit': 'USD/MT',
            'error': None if prices else '无法解析',
            'source': 'Zhoushan',
            'timestamp': datetime.now().isoformat()
        }
        
        self._set_cache(cache_key, result)
        return result
    
    def close(self):
        """清理资源"""
        pass
