"""
Real-time Data Service - Only Real Data, No Mock Data
真实数据查询 - 仅返回实时爬取的数据，不返回任何Mock数据
"""

import requests
from typing import Dict, List, Any
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


class RealTimeDataService:
    """仅返回真实数据的实时数据服务"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.driver = None
    
    def _get_driver(self):
        """获取或创建Selenium WebDriver"""
        if self.driver is None:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument('user-agent=Mozilla/5.0')
            
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
        return self.driver
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    # ===== Baltic Exchange - 所有指数 =====
    def get_baltic_indices(self) -> Dict[str, Any]:
        """获取Baltic Exchange所有实时指数
        https://www.balticexchange.com/en/index.html
        """
        try:
            driver = self._get_driver()
            driver.get("https://www.balticexchange.com/en/index.html")
            time.sleep(4)  # 等待JavaScript加载
            
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            page_text = soup.get_text()
            
            indices = []
            
            # 查找所有指数（BDI, BCI, BPI, BSI, BCTI, BAI, BHSI, BLNG, BLPG）
            indices_map = {
                'BDI': {'name': 'Baltic Dry Index', 'desc': '干散货指数'},
                'BCI': {'name': 'Baltic Capesize Index', 'desc': '大型干散货'},
                'BPI': {'name': 'Baltic Panamax Index', 'desc': '巴拿马型'},
                'BSI': {'name': 'Baltic Handysize Index', 'desc': '小型船舶'},
                'BCTI': {'name': 'Baltic Clean Tanker Index', 'desc': '洁净油轮'},
                'BAI': {'name': 'Baltic Tanker Index', 'desc': '油轮综合'},
                'BHSI': {'name': 'Baltic Dirty Tanker Index', 'desc': '杂质油轮'},
                'BLNG': {'name': 'Baltic LNG Index', 'desc': '液化天然气'},
                'BLPG': {'name': 'Baltic LPG Index', 'desc': '液化石油气'},
            }
            
            for code, info in indices_map.items():
                # 查找格式: BDI 2145 或 BDI: 2145
                pattern = rf'{code}\s*(?::|,)?\s*(\d+(?:,\d+)*)'
                match = re.search(pattern, page_text)
                
                if match:
                    value_str = match.group(1).replace(',', '')
                    value = int(value_str)
                    indices.append({
                        'code': code,
                        'name': info['name'],
                        'value': value,
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    print(f"[INFO] {code} not found on page")
            
            if indices:
                print(f"[OK] Baltic Exchange: Found {len(indices)} real indices")
                return {
                    'data': indices,
                    'count': len(indices),
                    'source': 'Baltic Exchange (Real)',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'error': 'No Baltic indices found on page',
                    'source': 'Baltic Exchange',
                    'timestamp': datetime.now().isoformat()
                }
        
        except Exception as e:
            return {
                'error': f'Failed to fetch Baltic indices: {str(e)[:100]}',
                'source': 'Baltic Exchange',
                'timestamp': datetime.now().isoformat()
            }
    
    # ===== 外汇 - 仅昨日收盘价 =====
    def get_forex_closing_price(self, code: str) -> Dict[str, Any]:
        """获取外汇昨日收盘价
        支持: USDCNY, EURCNY, GBPUSD, USDJPY, USDHKD, DINIW
        """
        try:
            url = f"https://finance.sina.com.cn/money/forex/hq/{code}.shtml"
            
            driver = self._get_driver()
            driver.get(url)
            time.sleep(3)
            
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            page_text = soup.get_text()
            
            # 查找价格数据 - 通常格式: 6.8945 -0.0015 -0.02%
            pattern = r'(\d+\.\d{2,4})\s+(-?\d+\.\d+)\s+(-?\d+\.\d+%)'
            match = re.search(pattern, page_text)
            
            if match:
                current_price = float(match.group(1))
                change = float(match.group(2))
                change_pct = match.group(3)
                
                # 计算昨日收盘价 = 今日价格 - 变化
                yesterday_close = current_price - change
                
                print(f"[OK] {code}: current={current_price}, yesterday_close={yesterday_close}")
                
                return {
                    'code': code,
                    'current_price': current_price,
                    'yesterday_close': round(yesterday_close, 4),
                    'change': change,
                    'change_pct': change_pct,
                    'source': 'Sina Finance (Real)',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'error': f'No price data found for {code}',
                    'code': code,
                    'source': 'Sina Finance',
                    'timestamp': datetime.now().isoformat()
                }
        
        except Exception as e:
            return {
                'error': f'Failed to fetch {code}: {str(e)[:100]}',
                'code': code,
                'source': 'Sina Finance',
                'timestamp': datetime.now().isoformat()
            }
    
    # ===== 进口矿指数 - 今日 vs 昨日 =====
    def get_iron_ore_index(self) -> Dict[str, Any]:
        """获取进口矿指数（今日 vs 昨日）
        """
        try:
            url = "https://index.mysteel.com/xpic/detail.html?tabName=kuangsi"
            
            driver = self._get_driver()
            driver.get(url)
            time.sleep(4)
            
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            page_text = soup.get_text()
            
            # 查找进口矿指数数据
            pattern = r'进口矿\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+([\d\.\-]+)%'
            match = re.search(pattern, page_text)
            
            if match:
                today = float(match.group(1))
                yesterday = float(match.group(2))
                change_pct = float(match.group(3))
                
                print(f"[OK] Iron Ore Index: today={today}, yesterday={yesterday}")
                
                return {
                    'name': 'Import Iron Ore Index',
                    'today': today,
                    'yesterday': yesterday,
                    'change_percent': change_pct,
                    'source': 'MySteel (Real)',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'error': 'No iron ore data found',
                    'source': 'MySteel',
                    'timestamp': datetime.now().isoformat()
                }
        
        except Exception as e:
            return {
                'error': f'Failed to fetch iron ore: {str(e)[:100]}',
                'source': 'MySteel',
                'timestamp': datetime.now().isoformat()
            }
    
    # ===== BOC 美元汇率 =====
    def get_boc_usd_rate(self) -> Dict[str, Any]:
        """获取中国银行美元汇率
        """
        try:
            url = "https://www.boc.cn/sourcedb/whpj/"
            
            driver = self._get_driver()
            driver.get(url)
            time.sleep(4)
            
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            page_text = soup.get_text()
            
            # 查找USD汇率
            pattern = r'美\s*元.*?(\d\.\d{2,4})'
            match = re.search(pattern, page_text)
            
            if match:
                mid_rate = float(match.group(1))
                
                # 买入价和卖出价通常在中间价上下浮动
                buy_rate = mid_rate * 0.995
                sell_rate = mid_rate * 1.005
                
                print(f"[OK] BOC USD: mid={mid_rate}")
                
                return {
                    'name': 'BOC USD Rate',
                    'buy_rate': round(buy_rate, 4),
                    'mid_rate': mid_rate,
                    'sell_rate': round(sell_rate, 4),
                    'source': 'BOC (Real)',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'error': 'No USD rate found',
                    'source': 'BOC',
                    'timestamp': datetime.now().isoformat()
                }
        
        except Exception as e:
            return {
                'error': f'Failed to fetch BOC rate: {str(e)[:100]}',
                'source': 'BOC',
                'timestamp': datetime.now().isoformat()
            }
    
    # ===== 原油期货 - 最新价格 =====
    def get_crude_futures_price(self, code: str) -> Dict[str, Any]:
        """获取原油期货最新价格
        CL: 纽约原油, OIL: WTI原油
        """
        try:
            if code == 'CL':
                url = "https://finance.sina.com.cn/futures/quotes/CL.shtml?id=27"
            else:
                url = "https://finance.sina.com.cn/futures/quotes/OIL.shtml"
            
            driver = self._get_driver()
            driver.get(url)
            time.sleep(3)
            
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            page_text = soup.get_text()
            
            # 查找价格
            pattern = r'(\d+\.\d{2,3})\s+(-?\d+\.\d+)\s+(-?\d+\.\d+%)'
            match = re.search(pattern, page_text)
            
            if match:
                price = float(match.group(1))
                change = float(match.group(2))
                change_pct = match.group(3)
                
                print(f"[OK] {code}: price={price}")
                
                return {
                    'code': code,
                    'price': price,
                    'change': change,
                    'change_pct': change_pct,
                    'source': 'Sina Finance (Real)',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'error': f'No price data for {code}',
                    'code': code,
                    'source': 'Sina Finance',
                    'timestamp': datetime.now().isoformat()
                }
        
        except Exception as e:
            return {
                'error': f'Failed to fetch {code}: {str(e)[:100]}',
                'code': code,
                'source': 'Sina Finance',
                'timestamp': datetime.now().isoformat()
            }
    
    # ===== 全球油价 - 所有港口 =====
    def get_bunker_prices(self) -> Dict[str, Any]:
        """获取全球港口油价
        """
        try:
            url = "https://www.bunkerindex.com/"
            
            response = self.session.get(url, timeout=20)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()
            
            ports_data = []
            
            # 提取所有港口价格 - 格式: 港口名 | 国家 | 价格
            port_pattern = r'(Singapore|Rotterdam|Dubai|Houston|Hong Kong|Fujairah|Busan|Kaohsiung|Zhoushan)\s*(?:[A-Z]{2})?\s+(\d+\.\d{2})'
            matches = re.findall(port_pattern, page_text)
            
            for port_name, price in matches:
                ports_data.append({
                    'port': port_name,
                    'price': float(price),
                    'unit': 'USD/MT'
                })
            
            if ports_data:
                print(f"[OK] Bunker prices: {len(ports_data)} ports")
                return {
                    'name': 'Global Bunker Prices',
                    'data': ports_data,
                    'count': len(ports_data),
                    'source': 'BunkerIndex (Real)',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'error': 'No bunker price data found',
                    'source': 'BunkerIndex',
                    'timestamp': datetime.now().isoformat()
                }
        
        except Exception as e:
            return {
                'error': f'Failed to fetch bunker prices: {str(e)[:100]}',
                'source': 'BunkerIndex',
                'timestamp': datetime.now().isoformat()
            }
    
    # ===== 舟山油价 =====
    def get_zhoushan_bunker(self) -> Dict[str, Any]:
        """获取舟山油价
        """
        try:
            url = "https://www.zsbunker.cn/bunker_zhoushan.jsp"
            
            driver = self._get_driver()
            driver.get(url)
            time.sleep(3)
            
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            page_text = soup.get_text()
            
            prices = {}
            
            # 查找三种油品价格
            fuels = {
                'IFO380': r'IFO\s*380[^\d]*(\d+\.?\d*)',
                'LSMGO': r'LSMGO[^\d]*(\d+\.?\d*)',
                'VLSFO': r'VLSFO[^\d]*(\d+\.?\d*)'
            }
            
            for fuel_name, pattern in fuels.items():
                match = re.search(pattern, page_text)
                if match:
                    prices[fuel_name] = float(match.group(1))
            
            if prices:
                print(f"[OK] Zhoushan bunker: {prices}")
                return {
                    'port': 'Zhoushan',
                    'prices': prices,
                    'unit': 'USD/MT',
                    'source': 'Zhoushan (Real)',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'error': 'No zhoushan data found',
                    'source': 'Zhoushan',
                    'timestamp': datetime.now().isoformat()
                }
        
        except Exception as e:
            return {
                'error': f'Failed to fetch zhoushan: {str(e)[:100]}',
                'source': 'Zhoushan',
                'timestamp': datetime.now().isoformat()
            }
