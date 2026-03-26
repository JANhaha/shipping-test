"""
改进的真实数据服务 - 增强爬取逻辑
使用多层次的HTML解析和更智能的数据提取
"""

import requests
from typing import Dict, List, Any
from bs4 import BeautifulSoup
import re
from datetime import datetime
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


class ImprovedDataService:
    """改进的真实数据爬取服务"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.driver = None
    
    def _get_driver(self):
        """获取或创建Selenium WebDriver"""
        if self.driver is None:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            chrome_options.add_argument('--disable-gpu')
            
            try:
                self.driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=chrome_options
                )
            except Exception as e:
                print(f"[WARN] Selenium启动失败: {e}")
                return None
        return self.driver
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    # ===== Baltic Exchange - 改进版本 =====
    def get_baltic_indices(self) -> Dict[str, Any]:
        """获取Baltic Exchange指数 - 改进版"""
        try:
            # 先尝试用普通请求
            url = "https://www.balticexchange.com/en/index.html"
            response = self.session.get(url, timeout=15)
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()
            
            indices = []
            
            # 查找所有可能的数值
            # 模式: 指数代码 (可能有冒号或空格) 数值
            patterns = [
                r'(?:BDI|Baltic Dry Index)\D*?(\d{1,5})',
                r'(?:BCI|Baltic Capesize)\D*?(\d{1,5})',
                r'(?:BPI|Baltic Panamax)\D*?(\d{1,5})',
                r'(?:BSI|Baltic Handysize)\D*?(\d{1,5})',
                r'(?:BCTI|Baltic Clean Tanker)\D*?(\d{1,5})',
                r'(?:BAI|Baltic Tanker Index)\D*?(\d{1,5})',
                r'(?:BHSI|Baltic Dirty Tanker)\D*?(\d{1,5})',
                r'(?:BLNG|Baltic LNG)\D*?(\d{1,5})',
                r'(?:BLPG|Baltic LPG)\D*?(\d{1,5})',
            ]
            
            indices_map = {
                'BDI': {'name': 'Baltic Dry Index', 'pattern': r'BDI.*?(\d{4})'},
                'BCI': {'name': 'Baltic Capesize Index', 'pattern': r'BCI.*?(\d{4})'},
                'BPI': {'name': 'Baltic Panamax Index', 'pattern': r'BPI.*?(\d{4})'},
                'BSI': {'name': 'Baltic Handysize Index', 'pattern': r'BSI.*?(\d{4})'},
                'BCTI': {'name': 'Baltic Clean Tanker Index', 'pattern': r'BCTI.*?(\d{4})'},
                'BAI': {'name': 'Baltic Tanker Index', 'pattern': r'BAI.*?(\d{4})'},
                'BHSI': {'name': 'Baltic Dirty Tanker Index', 'pattern': r'BHSI.*?(\d{4})'},
                'BLNG': {'name': 'Baltic LNG Index', 'pattern': r'BLNG.*?(\d{4})'},
                'BLPG': {'name': 'Baltic LPG Index', 'pattern': r'BLPG.*?(\d{4})'},
            }
            
            for code, info in indices_map.items():
                match = re.search(info['pattern'], page_text, re.IGNORECASE | re.DOTALL)
                if match:
                    try:
                        value = int(match.group(1))
                        if 1000 <= value <= 5000:  # 合理范围检查
                            indices.append({
                                'code': code,
                                'name': info['name'],
                                'value': value,
                                'timestamp': datetime.now().isoformat()
                            })
                            print(f"[OK] {code} = {value}")
                    except:
                        pass
            
            if indices:
                print(f"[SUCCESS] Baltic Exchange: Found {len(indices)} indices")
                return {
                    'data': indices,
                    'count': len(indices),
                    'source': 'Baltic Exchange (Real)',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                print(f"[INFO] Trying Selenium for Baltic Exchange...")
                # 如果普通请求失败，使用Selenium
                driver = self._get_driver()
                if driver:
                    driver.get(url)
                    time.sleep(5)  # 等待JavaScript加载
                    
                    # 查找所有包含数字的span/div
                    for element in driver.find_elements(By.CSS_SELECTOR, "span, div, td"):
                        text = element.text.strip()
                        for code in indices_map.keys():
                            if code in text.upper():
                                # 提取数字
                                nums = re.findall(r'\d{1,5}', text)
                                if nums:
                                    value = int(nums[0])
                                    if 1000 <= value <= 5000:
                                        indices.append({
                                            'code': code,
                                            'name': indices_map[code]['name'],
                                            'value': value,
                                            'timestamp': datetime.now().isoformat()
                                        })
                    
                    if indices:
                        print(f"[SUCCESS via Selenium] Found {len(indices)} indices")
                        return {
                            'data': indices,
                            'count': len(indices),
                            'source': 'Baltic Exchange (Selenium)',
                            'timestamp': datetime.now().isoformat()
                        }
            
            return {
                'error': f'No Baltic indices found (tried both methods)',
                'response_length': len(response.text),
                'contains_BDI': 'BDI' in page_text,
                'source': 'Baltic Exchange',
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            import traceback
            print(f"[ERROR] Baltic Exchange: {e}")
            return {
                'error': f'Failed to fetch: {str(e)[:100]}',
                'source': 'Baltic Exchange',
                'timestamp': datetime.now().isoformat()
            }
    
    # ===== 外汇 - 改进版 =====
    def get_forex_closing_price(self, code: str) -> Dict[str, Any]:
        """获取外汇昨日收盘价 - 改进版"""
        try:
            url = f"https://finance.sina.com.cn/money/forex/hq/{code}.shtml"
            response = self.session.get(url, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有表格和数字
            text = soup.get_text()
            lines = text.split('\n')
            
            # 查找价格行（通常包含4个数字）
            prices = []
            for line in lines:
                # 查找格式: 6.8945 -0.0015 -0.02%
                match = re.search(r'(\d+\.\d{2,4})\D+(-?\d+\.\d+)\D+(-?\d+\.\d+%)', line)
                if match:
                    prices.append({
                        'current': float(match.group(1)),
                        'change': float(match.group(2)),
                        'change_pct': match.group(3)
                    })
            
            if prices:
                price_info = prices[0]  # 取第一个匹配
                current_price = price_info['current']
                change = price_info['change']
                yesterday_close = current_price - change
                
                print(f"[OK] {code}: current={current_price}, yesterday_close={yesterday_close}")
                
                return {
                    'code': code,
                    'current_price': current_price,
                    'yesterday_close': round(yesterday_close, 4),
                    'change': change,
                    'change_pct': price_info['change_pct'],
                    'source': 'Sina Finance (Real)',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                # 尝试find更宽松的格式
                match = re.search(r'(\d+\.\ d{2,4})', text)
                if match:
                    price = float(match.group(1).replace(' ', ''))
                    return {
                        'code': code,
                        'current_price': price,
                        'yesterday_close': price,  # 无法获取昨日价格
                        'source': 'Sina Finance (Partial)',
                        'timestamp': datetime.now().isoformat()
                    }
                
                return {
                    'error': f'No price data found for {code}',
                    'code': code,
                    'response_length': len(response.text),
                    'source': 'Sina Finance',
                    'timestamp': datetime.now().isoformat()
                }
        
        except Exception as e:
            print(f"[ERROR] {code}: {e}")
            return {
                'error': f'Failed: {str(e)[:100]}',
                'code': code,
                'source': 'Sina Finance',
                'timestamp': datetime.now().isoformat()
            }
    
    # ===== 全球油价 - 改进版 =====
    def get_bunker_prices(self) -> Dict[str, Any]:
        """获取全球港口油价 - 改进版"""
        try:
            url = "https://www.bunkerindex.com/"
            response = self.session.get(url, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找表格
            tables = soup.find_all('table')
            ports_data = []
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:
                        port_name = cells[0].get_text().strip()
                        price_text = cells[-1].get_text().strip()
                        
                        # 提取价格
                        price_match = re.search(r'(\d+\.\d{2})', price_text)
                        if price_match and any(p in port_name for p in ['Singapore', 'Rotterdam', 'Dubai', 'Houston', 'Port', 'port']):
                            try:
                                price = float(price_match.group(1))
                                ports_data.append({
                                    'port': port_name[:30],  # 限制长度
                                    'price': price,
                                    'unit': 'USD/MT'
                                })
                            except:
                                pass
            
            if ports_data:
                print(f"[OK] Bunker: Found {len(ports_data)} ports")
                return {
                    'name': 'Global Bunker Prices',
                    'data': ports_data,
                    'count': len(ports_data),
                    'source': 'BunkerIndex (Real)',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'error': 'No port data found in tables',
                    'response_length': len(response.text),
                    'source': 'BunkerIndex',
                    'timestamp': datetime.now().isoformat()
                }
        
        except Exception as e:
            print(f"[ERROR] Bunker: {e}")
            return {
                'error': f'Failed: {str(e)[:100]}',
                'source': 'BunkerIndex',
                'timestamp': datetime.now().isoformat()
            }
    
    # ===== BOC美元汇率 - 改进版 =====
    def get_boc_usd_rate(self) -> Dict[str, Any]:
        """获取BOC美元汇率 - 改进版"""
        try:
            url = "https://www.boc.cn/sourcedb/whpj/"
            response = self.session.get(url, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有表格
            tables = soup.find_all('table')
            for table in tables:
                text = table.get_text()
                # 查找USD相关的行
                if 'USD' in text or '美元' in text:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            row_text = ' '.join([cell.get_text().strip() for cell in cells])
                            if 'USD' in row_text or '美元' in row_text:
                                # 提取汇率
                                prices = re.findall(r'\d\.\d{2,4}', row_text)
                                if prices:
                                    mid_rate = float(prices[0])
                                    buy_rate = float(prices[1]) if len(prices) > 1 else mid_rate * 0.995
                                    sell_rate = float(prices[2]) if len(prices) > 2 else mid_rate * 1.005
                                    
                                    print(f"[OK] BOC USD: {mid_rate}")
                                    
                                    return {
                                        'name': 'BOC USD Rate',
                                        'buy_rate': round(buy_rate, 4),
                                        'mid_rate': mid_rate,
                                        'sell_rate': round(sell_rate, 4),
                                        'source': 'BOC (Real)',
                                        'timestamp': datetime.now().isoformat()
                                    }
            
            return {
                'error': 'No USD rate found',
                'response_length': len(response.text),
                'source': 'BOC',
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            print(f"[ERROR] BOC: {e}")
            return {
                'error': f'Failed: {str(e)[:100]}',
                'source': 'BOC',
                'timestamp': datetime.now().isoformat()
            }
    
    # ===== 进口矿指数 - 改进版 =====
    def get_iron_ore_index(self) -> Dict[str, Any]:
        """获取进口矿指数 - 改进版"""
        try:
            url = "https://index.mysteel.com/xpic/detail.html?tabName=kuangsi"
            response = self.session.get(url, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            text = soup.get_text()
            # 查找进口矿相关数据
            lines = text.split('\n')
            
            for i, line in enumerate(lines):
                if '进口矿' in line or '铁矿' in line:
                    # 在这行之后查找数字
                    combined_text = ' '.join(lines[i:min(i+5, len(lines))])
                    numbers = re.findall(r'\d+\.?\d*', combined_text)
                    
                    if len(numbers) >= 2:
                        try:
                            today = float(numbers[0])
                            yesterday = float(numbers[1])
                            change_pct = ((today - yesterday) / yesterday * 100) if yesterday != 0 else 0
                            
                            print(f"[OK] Iron Ore: today={today}, yesterday={yesterday}")
                            
                            return {
                                'name': 'Import Iron Ore Index',
                                'today': today,
                                'yesterday': yesterday,
                                'change_percent': round(change_pct, 2),
                                'source': 'MySteel (Real)',
                                'timestamp': datetime.now().isoformat()
                            }
                        except:
                            pass
            
            return {
                'error': 'No iron ore data found',
                'response_length': len(response.text),
                'source': 'MySteel',
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            print(f"[ERROR] Iron Ore: {e}")
            return {
                'error': f'Failed: {str(e)[:100]}',
                'source': 'MySteel',
                'timestamp': datetime.now().isoformat()
            }
    
    # ===== 原油期货 - 改进版 =====
    def get_crude_futures_price(self, code: str) -> Dict[str, Any]:
        """获取原油期货价格 - 改进版"""
        try:
            if code == 'CL':
                url = "https://finance.sina.com.cn/futures/quotes/CL.shtml?id=27"
            else:
                url = "https://finance.sina.com.cn/futures/quotes/OIL.shtml"
            
            response = self.session.get(url, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            text = soup.get_text()
            
            # 查找价格格式
            matches = re.findall(r'(\d+\.\d{2})\s+(.?\d+\.\d+)\s+(.?\d+\.\d+%)', text)
            
            if matches:
                price = float(matches[0][0])
                change = float(matches[0][1])
                change_pct = matches[0][2]
                
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
                    'response_length': len(response.text),
                    'source': 'Sina Finance',
                    'timestamp': datetime.now().isoformat()
                }
        
        except Exception as e:
            print(f"[ERROR] {code}: {e}")
            return {
                'error': f'Failed: {str(e)[:100]}',
                'code': code,
                'source': 'Sina Finance',
                'timestamp': datetime.now().isoformat()
            }
    
    # ===== 舟山油价 - 改进版 =====
    def get_zhoushan_bunker(self) -> Dict[str, Any]:
        """获取舟山油价 - 改进版"""
        try:
            url = "https://www.zsbunker.cn/bunker_zhoushan.jsp"
            response = self.session.get(url, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
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
                    prices[fuel_name] = float(match.group(1))
            
            if prices:
                print(f"[OK] Zhoushan: {prices}")
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
                    'response_length': len(response.text),
                    'source': 'Zhoushan',
                    'timestamp': datetime.now().isoformat()
                }
        
        except Exception as e:
            print(f"[ERROR] Zhoushan: {e}")
            return {
                'error': f'Failed: {str(e)[:100]}',
                'source': 'Zhoushan',
                'timestamp': datetime.now().isoformat()
            }
