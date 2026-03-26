"""
航运数据服务模块
用于获取和处理实时航运和金融数据
"""

import requests
from typing import Dict, List, Any
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import json


class ShippingDataService:
    """航运数据服务类"""
    
    def __init__(self):
        """初始化数据服务"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.baltic_url = "https://www.balticexchange.com/en/index.html"
    
    def get_baltic_indices(self) -> List[Dict[str, Any]]:
        """从 Baltic Exchange 官网获取航运指数数据"""
        try:
            response = self.session.get(self.baltic_url, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()
            
            indices_info = {
                'BDI': {'name': 'Baltic Dry Index', 'description': '干散货指数'},
                'BSI': {'name': 'Baltic Handysize Index', 'description': '小型船舶指数'},
                'BCI': {'name': 'Baltic Capesize Index', 'description': '大型干散货指数'},
                'BCTI': {'name': 'Baltic Clean Tanker Index', 'description': '洁净油轮指数'},
                'BPI': {'name': 'Baltic Panamax Index', 'description': '巴拿马型船指数'},
                'BAI': {'name': 'Baltic Tanker Index', 'description': '油轮综合指数'},
                'BHSI': {'name': 'Baltic Handysize Dirty Tanker Index', 'description': '杂质油轮指数'},
                'BLNG': {'name': 'Baltic LNG Index', 'description': '液化天然气指数'},
                'BLPG': {'name': 'Baltic LPG Index', 'description': '液化石油气指数'},
            }
            
            indices = []
            for code, info in indices_info.items():
                pattern = rf'{code}[\s,]*(\d+(?:[,\d]*)*)'
                match = re.search(pattern, page_text)
                
                if match:
                    value_str = match.group(1).replace(',', '')
                    try:
                        value = int(value_str)
                        indices.append({
                            'code': code,
                            'name': info['name'],
                            'description': info['description'],
                            'value': value,
                            'timestamp': datetime.now().isoformat(),
                            'source': 'Baltic Exchange'
                        })
                    except ValueError:
                        pass
            
            return indices
                
        except Exception as e:
            print(f"获取 Baltic Exchange 数据失败: {e}")
            return []
    
    def get_crude_futures(self, code: str) -> Dict[str, Any]:
        """获取原油期货数据（最近5天）"""
        try:
            url = f"https://finance.sina.com.cn/futures/quotes/{code}.shtml"
            response = self.session.get(url, timeout=10)
            response.encoding = 'gbk'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            return {
                'code': code,
                'name': f'原油期货 ({code})',
                'data': [],
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"获取 {code} 数据失败: {e}")
            return {'code': code, 'data': []}
    
    def get_import_iron_ore(self) -> Dict[str, Any]:
        """获取进口矿指数（本日和昨日）"""
        try:
            url = "https://index.mysteel.com/xpic/detail.html?tabName=kuangsi"
            response = self.session.get(url, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            return {
                'name': '进口矿指数',
                'today': None,
                'yesterday': None,
                'timestamp': datetime.now().isoformat(),
                'source': 'MySteel'
            }
        except Exception as e:
            print(f"获取进口矿指数失败: {e}")
            return {}
    
    def get_boc_usd_rate(self) -> Dict[str, Any]:
        """获取美元中行折算价"""
        try:
            url = "https://www.boc.cn/sourcedb/whpj/"
            response = self.session.get(url, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            return {
                'currency': 'USD',
                'rate': None,
                'name': '美元中行折算价',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"获取中行外汇数据失败: {e}")
            return {}
    
    def get_forex_data(self, code: str) -> Dict[str, Any]:
        """获取外汇数据（最近5日）"""
        try:
            url = f"https://finance.sina.com.cn/money/forex/hq/{code}.shtml"
            response = self.session.get(url, timeout=10)
            response.encoding = 'gbk'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            return {
                'code': code,
                'data': [],
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"获取 {code} 外汇数据失败: {e}")
            return {}
    
    def get_bunker_prices(self) -> Dict[str, Any]:
        """获取所有港口油价信息"""
        try:
            url = "https://www.bunkerindex.com/"
            response = self.session.get(url, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            return {
                'ports': [],
                'name': 'Bunker Index 油价',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"获取 Bunker 油价失败: {e}")
            return {}
    
    def get_zhoushan_bunker(self) -> Dict[str, Any]:
        """获取舟山油价（IFO380、LSMGO、VLSFO）"""
        try:
            url = "https://www.zsbunker.cn/bunker_zhoushan.jsp"
            response = self.session.get(url, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            return {
                'location': '舟山',
                'fuels': {
                    'IFO380': None,
                    'LSMGO': None,
                    'VLSFO': None
                },
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"获取舟山油价失败: {e}")
            return {}
    
    def get_all_data(self) -> Dict[str, Any]:
        """获取所有数据"""
        return {
            'baltic_indices': self.get_baltic_indices(),
            'crude_futures_cl': self.get_crude_futures('CL'),
            'crude_futures_oil': self.get_crude_futures('OIL'),
            'import_iron_ore': self.get_import_iron_ore(),
            'boc_usd': self.get_boc_usd_rate(),
            'forex_usd_index': self.get_forex_data('DINIW'),
            'forex_eurcny': self.get_forex_data('EURCNY'),
            'forex_gbpusd': self.get_forex_data('GBPUSD'),
            'forex_usdcny': self.get_forex_data('USDCNY'),
            'forex_usdhkd': self.get_forex_data('USDHKD'),
            'forex_usdjpy': self.get_forex_data('USDJPY'),
            'bunker_prices': self.get_bunker_prices(),
            'zhoushan_bunker': self.get_zhoushan_bunker(),
            'timestamp': datetime.now().isoformat()
        }

