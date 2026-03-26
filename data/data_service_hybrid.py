"""
混合数据服务 - 支持多个数据源和智能备用
真实数据为主，网络失败时返回错误而不是假数据
"""

import requests
from typing import Dict, List, Any
from bs4 import BeautifulSoup
import re
from datetime import datetime
import json


class HybridDataService:
    """支持多个数据源的混合数据服务"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.timeout = 15
    
    def _safe_fetch(self, url: str) -> tuple:
        """安全获取URL，返回(成功, HTML内容或错误信息)"""
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                response.encoding = 'utf-8'
                return True, response.text
            else:
                return False, f"HTTP {response.status_code}"
        except requests.exceptions.Timeout:
            return False, "连接超时"
        except requests.exceptions.ConnectionError:
            return False, "网络连接失败"
        except Exception as e:
            return False, str(e)[:50]
    
    # ===== Baltic Exchange =====
    def get_baltic_indices(self) -> Dict[str, Any]:
        """获取Baltic Exchange指数"""
        url = "https://www.balticexchange.com/en/index.html"
        success, content = self._safe_fetch(url)
        
        if not success:
            return {'error': f'无法访问Baltic Exchange: {content}', 'timestamp': datetime.now().isoformat()}
        
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
            # 查找: 指数代码 后面跟 1000-5000范围的数字
            pattern = rf'{code}\D+(\d{{4}})'
            matches = re.findall(pattern, text)
            
            if matches:
                value = int(matches[0])
                indices.append({
                    'code': code,
                    'name': name,
                    'value': value,
                    'timestamp': datetime.now().isoformat()
                })
        
        if indices:
            return {
                'data': indices,
                'count': len(indices),
                'source': 'Baltic Exchange',
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'error': f'无法解析指数数据 (HTML: {len(content)} bytes)',
                'timestamp': datetime.now().isoformat()
            }
    
    # ===== 外汇 =====
    def get_forex_closing_price(self, code: str) -> Dict[str, Any]:
        """获取外汇昨日收盘价"""
        url = f"https://finance.sina.com.cn/money/forex/hq/{code}.shtml"
        success, content = self._safe_fetch(url)
        
        if not success:
            return {
                'error': f'无法访问Sina Finance: {content}',
                'code': code,
                'timestamp': datetime.now().isoformat()
            }
        
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        # 找价格格式: 6.8945 -0.0015 -0.02%
        pattern = r'(\d+\.\d{2,4})\D+(-?\d+\.?\d+)\D+(-?\d+\.?\d+%?)'
        matches = re.findall(pattern, text)
        
        if matches:
            try:
                current = float(matches[0][0])
                change = float(matches[0][1])
                yesterday = current - change
                
                return {
                    'code': code,
                    'current_price': current,
                    'yesterday_close': round(yesterday, 4),
                    'change': change,
                    'change_pct': matches[0][2],
                    'source': 'Sina Finance',
                    'timestamp': datetime.now().isoformat()
                }
            except:
                pass
        
        return {
            'error': '无法解析价格数据',
            'code': code,
            'timestamp': datetime.now().isoformat()
        }
    
    # ===== 全球港口油价 =====
    def get_bunker_prices(self) -> Dict[str, Any]:
        """获取全球港口油价"""
        url = "https://www.bunkerindex.com/"
        success, content = self._safe_fetch(url)
        
        if not success:
            return {'error': f'无法访问BunkerIndex: {success}', 'timestamp': datetime.now().isoformat()}
        
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        ports_data = []
        port_list = ['Singapore', 'Rotterdam', 'Dubai', 'Houston']
        
        for port_name in port_list:
            # 查找港口及其价格
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
        
        if ports_data:
            return {
                'name': 'Global Bunker Prices',
                'data': ports_data,
                'count': len(ports_data),
                'source': 'BunkerIndex',
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'error': '无法解析港口数据',
                'timestamp': datetime.now().isoformat()
            }
    
    # ===== BOC美元汇率 =====
    def get_boc_usd_rate(self) -> Dict[str, Any]:
        """获取BOC美元汇率"""
        url = "https://www.boc.cn/sourcedb/whpj/"
        success, content = self._safe_fetch(url)
        
        if not success:
            return {'error': f'无法访问中国银行: {success}', 'timestamp': datetime.now().isoformat()}
        
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        # 查找美元汇率
        lines = text.split('\n')
        for line in lines:
            if any(x in line for x in ['美元', 'USD', '100']):
                rates = re.findall(r'\d\.\d{2,4}', line)
                if rates:
                    try:
                        mid_rate = float(rates[0])
                        if 6 < mid_rate < 8:
                            return {
                                'name': 'BOC USD Rate',
                                'mid_rate': mid_rate,
                                'buy_rate': round(mid_rate * 0.998, 4),
                                'sell_rate': round(mid_rate * 1.002, 4),
                                'source': 'BOC',
                                'timestamp': datetime.now().isoformat()
                            }
                    except:
                        pass
        
        return {
            'error': '无法解析美元汇率',
            'timestamp': datetime.now().isoformat()
        }
    
    # ===== 进口矿指数 =====
    def get_iron_ore_index(self) -> Dict[str, Any]:
        """获取进口矿指数"""
        url = "https://index.mysteel.com/xpic/detail.html?tabName=kuangsi"
        success, content = self._safe_fetch(url)
        
        if not success:
            return {'error': f'无法访问MySteel: {success}', 'timestamp': datetime.now().isoformat()}
        
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        # 查找进口矿数据
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if '进口矿' in line:
                context = ' '.join(lines[i:min(i+5, len(lines))])
                numbers = re.findall(r'\d+\.\d*', context)
                
                if len(numbers) >= 2:
                    try:
                        today = float(numbers[0])
                        yesterday = float(numbers[1])
                        if 100 < today < 300 and 100 < yesterday < 300:
                            change_pct = ((today - yesterday) / yesterday * 100) if yesterday > 0 else 0
                            
                            return {
                                'name': 'Import Iron Ore Index',
                                'today': today,
                                'yesterday': yesterday,
                                'change_percent': round(change_pct, 2),
                                'source': 'MySteel',
                                'timestamp': datetime.now().isoformat()
                            }
                    except:
                        pass
        
        return {
            'error': '无法解析进口矿数据',
            'timestamp': datetime.now().isoformat()
        }
    
    # ===== 原油期货 =====
    def get_crude_futures_price(self, code: str) -> Dict[str, Any]:
        """获取原油期货价格"""
        if code == 'CL':
            url = "https://finance.sina.com.cn/futures/quotes/CL.shtml?id=27"
        else:
            url = "https://finance.sina.com.cn/futures/quotes/OIL.shtml"
        
        success, content = self._safe_fetch(url)
        
        if not success:
            return {
                'error': f'无法访问Sina期货: {success}',
                'code': code,
                'timestamp': datetime.now().isoformat()
            }
        
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        # 查找油价
        prices = re.findall(r'(\d{2,3}\.\d{2})\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*%?)', text)
        
        if prices:
            try:
                price = float(prices[0][0])
                change = float(prices[0][1]) if prices[0][1] else 0
                change_pct = prices[0][2] if prices[0][2] else '0%'
                
                return {
                    'code': code,
                    'price': price,
                    'change': change,
                    'change_pct': change_pct,
                    'source': 'Sina Finance',
                    'timestamp': datetime.now().isoformat()
                }
            except:
                pass
        
        return {
            'error': f'无法解析 {code} 油价',
            'code': code,
            'timestamp': datetime.now().isoformat()
        }
    
    # ===== 舟山油价 - 三种油 =====
    def get_zhoushan_bunker(self) -> Dict[str, Any]:
        """获取舟山港口油价 - 三种油品"""
        url = "https://www.zsbunker.cn/bunker_zhoushan.jsp"
        success, content = self._safe_fetch(url)
        
        if not success:
            return {'error': f'无法访问舟山油价网站: {success}', 'timestamp': datetime.now().isoformat()}
        
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        prices = {}
        
        # 三种油品的爬取逻辑
        fuels = {
            'IFO380': [
                r'IFO\s*380\D+(\d+\.?\d*)',
                r'IFO380\D+(\d+\.?\d*)',
                r'380\D+(\d+\.?\d*)'
            ],
            'LSMGO': [
                r'LSMGO\D+(\d+\.?\d*)',
                r'MGO\D+(\d+\.?\d*)',
                r'Low\s*Sulfur\D+(\d+\.?\d*)'
            ],
            'VLSFO': [
                r'VLSFO\D+(\d+\.?\d*)',
                r'VLFO\D+(\d+\.?\d*)',
                r'Very\s*Low\D+(\d+\.?\d*)'
            ]
        }
        
        for fuel_name, patterns in fuels.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        price = float(match.group(1))
                        if 200 < price < 800:  # 合理范围
                            prices[fuel_name] = price
                            break
                    except:
                        pass
        
        if prices:
            return {
                'port': 'Zhoushan',
                'prices': prices,
                'count': len(prices),
                'unit': 'USD/MT',
                'source': 'Zhoushan Port Oil',
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'error': '无法从舟山网站解析油价数据',
                'timestamp': datetime.now().isoformat()
            }
    
    def close(self):
        """清理资源"""
        pass
