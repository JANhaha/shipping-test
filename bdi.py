from selenium import webdriver
from bs4 import BeautifulSoup
import time

print("1. 脚本开始运行")

url = "https://www.balticexchange.com/en/index.html"

driver = webdriver.Chrome()
print("2. 浏览器已启动")

driver.get(url)
print("3. 已打开网页")

time.sleep(5)

soup = BeautifulSoup(driver.page_source, "html.parser")

if soup.title:
    print("网页标题：", soup.title.text)
else:
    print("没有拿到标题")

driver.quit()
print("4. 浏览器已关闭，脚本结束")