import requests
from bs4 import BeautifulSoup
# import pandas
# from pandas import ExcelWriter
# import openpyxl
import lxml
from urllib.request import Request, urlopen
import re,csv
from selenium.webdriver.firefox.options import Options
import time
# from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

headers = {
    "Accept": "*/*",
    "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0",
}

def get_html(url):
    options = Options()
    options.headless = False
    driver = webdriver.Firefox(options=options)
    driver.get(url)
    SCROLL_PAUSE_TIME = 3

    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Wait to load page
        time.sleep(SCROLL_PAUSE_TIME)

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    html = driver.page_source
    driver.close()
    return html

def get_pages(html):
    soup = BeautifulSoup(html, 'lxml')
    try:
        good_count = soup.find('span', class_='goods-count').get_text(strip=True).replace("\xa0", '').split()[0]
        print(good_count)
        pages = int(good_count) // 100 + 1
    except:
        pages = 1
    return pages

def get_price_for_visa_and_MC(html):
    soup = BeautifulSoup(html, 'lxml')
    price_with_tags = soup.find('span', class_='price-block__final-price')
    price_with_r = price_with_tags.get_text().replace("\xa0", '')
    price = price_with_r.replace('₽', '')
    return (float(price))

def get_price_for_mir_and_Gpay(html):
    soup = BeautifulSoup(html, 'lxml')
    price = soup.select('meta[itemprop="price"]')[0].get('content')

    return int(float(price))

def get_raiting(html):
    soup = BeautifulSoup(html, 'lxml')
    raiting = soup.find('span', class_='user-scores__score')
    if raiting is None: 
        return 0
    return raiting.get_text()

def get_review_count(html):
    soup = BeautifulSoup(html, 'lxml')
    review_count = soup.select('meta[itemprop="reviewCount"]')
    if len(review_count) == 0:
        return 0
    return review_count[0].get('content')
def get_detail_info(id):
    detailURL = f'https://www.wildberries.ru/catalog/{id}/detail.aspx?targetUrl=SP'
    html = get_html(detailURL)
    info = {
        'articul': id,
        'price': get_price_for_visa_and_MC(html),
        # 'price_for_mir': get_price_for_mir_and_Gpay(html),
        'reviewCount': get_review_count(html),
        'raiting': get_raiting(html)
    }
    return info