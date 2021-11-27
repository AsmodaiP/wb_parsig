import logging
from bs4 import BeautifulSoup
# import pandas
# from pandas import ExcelWriter
# import openpyxl
from selenium.webdriver.firefox.options import Options
import time
# from bs4 import BeautifulSoup
from selenium import webdriver
import os
from logging.handlers import RotatingFileHandler

headers = {
    "Accept": "*/*",
    "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# log_dir = os.path.join(BASE_DIR, 'logs/')
# log_file = os.path.join(BASE_DIR, 'logs/parsing.log')
# console_handler = logging.StreamHandler()
# file_handler = RotatingFileHandler(
#     log_file,
#     maxBytes=100000,
#     backupCount=3,
#     encoding='utf-8'
# )
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s, %(levelname)s, %(message)s',
#     handlers=(
#         file_handler,
#         console_handler
#     )
# )


def get_html(url):
    options = Options()
    options.headless = False
    driver = webdriver.Firefox(options=options)
    driver.get(url)
    SCROLL_PAUSE_TIME = 4

    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        # Scroll down to bottom
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")

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
        good_count = soup.find(
            'span', class_='goods-count').get_text(strip=True).replace("\xa0", '').split()[0]
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
    logging.info(f'Price = {price}')
    return price


def get_price_for_mir_and_Gpay(html):
    soup = BeautifulSoup(html, 'lxml')
    price = soup.select('meta[itemprop="price"]')[0].get('content')

    return int(float(price))


def get_raiting(html):
    soup = BeautifulSoup(html, 'lxml')
    raiting = soup.find('span', class_='user-scores__score')
    if raiting is None:
        logging.info('Raiting = 0')
        return 0
    rt = raiting.get_text().replace('.', ',')
    logging.info(f'Raiting = {rt}')
    return rt


def get_review_count(html):
    soup = BeautifulSoup(html, 'lxml')
    review_count = soup.select('meta[itemprop="reviewCount"]')
    if len(review_count) == 0:
        logging.info('Rewiew count = 0')
        return 0
    rc = review_count[0].get('content')
    logging.info(f'Rewiew count = {rc}')
    return rc


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
