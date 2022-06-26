from cmath import inf, log
import logging
from ssl import get_default_verify_paths
from typing import Dict
from bs4 import BeautifulSoup
from pyasn1_modules.rfc2459 import DistributionPoint
from requests import request
import requests
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
# import pandas
# from pandas import ExcelWriter
# import openpyxl
from selenium.webdriver.firefox.options import Options
import time
# from bs4 import BeautifulSoup
from selenium import webdriver
import os
from logging.handlers import RotatingFileHandler
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from sympy import re
from cookie import COOKIE

headers = {
    "Accept": "*/*",
    "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logging.getLogger()
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)


def get_html(url):
    options = Options()
    options.headless = True
    caps = DesiredCapabilities().FIREFOX
    caps["pageLoadStrategy"] = "eager"

    firefoxProfile = webdriver.FirefoxProfile()
    firefoxProfile.set_preference('permissions.default.stylesheet', 2)
    firefoxProfile.set_preference('permissions.default.image', 2)
    firefoxProfile.set_preference('dom.ipc.plugins.enabled.libflashplayer.so','false')
    firefoxProfile.set_preference("http.response.timeout", 10)
    firefoxProfile.set_preference("dom.max_script_run_time", 10)

    driver = webdriver.Firefox(options=options, desired_capabilities=caps, firefox_profile=firefoxProfile)
    driver.get('https://www.wildberries.ru/')

    try:
        driver.set_window_size(1920, 1080)
        driver.set_page_load_timeout(30)

        driver.get(url)
        driver.delete_cookie('__wbl')
        for coc in COOKIE['spb']:
            coc['sameSite'] = 'Strict'
            
            driver.add_cookie(coc)
        driver.get(url)
        # with open('coockit.json')
        # print(driver.get_cookies())
        SCROLL_PAUSE_TIME = 4
    
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(20):
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
        soup = BeautifulSoup(html, 'lxml')
    except Exception as e:
        driver.close()
        time.sleep(10)
        raise e
    driver.close()
    return html


def get_pages(html):
    soup = BeautifulSoup(html, 'lxml')
    try:
        good_count = soup.find(
            'span', class_='goods-count').get_text(strip=True).replace("\xa0", '').split()[0]
        pages = int(good_count) // 100 + 1
    except:
        pages = 1
    return pages


def get_price_for_visa_and_MC(html):
    soup = BeautifulSoup(html, 'lxml')
    price_with_tags = soup.find('span', class_='price-block__final-price')
    price_with_r = price_with_tags.get_text().replace("\xa0", '')
    price = price_with_r.replace('₽', '')
    return price.strip()


def get_price_for_mir_and_Gpay(html):
    soup = BeautifulSoup(html, 'lxml')
    price = soup.select('meta[itemprop="price"]')[0].get('content')

    return int(float(price))


def get_raiting(html):
    soup = BeautifulSoup(html, 'lxml')
    raiting = soup.find('span', class_='user-scores__score')
    if raiting is None:
        return 0
    rt = raiting.get_text().replace('.', ',')
    return rt


def get_review_count(html):
    soup = BeautifulSoup(html, 'lxml')
    try:
        rc = soup.find('span', class_='same-part-kt__count-review').get_text()
        rc  = ' '.join(word for word in rc.split()[:-1])
    except:
        rc = 0
    return rc


def get_all_reviews(html):
    soup = BeautifulSoup(html, 'lxml')
    feedbacks = soup.find_all('li', class_='comments__item feedback')
    info = []
    for feedback in feedbacks:
        review_date = feedback.find('span', class_='feedback__date').get('content')
        review_rating = feedback.find('span', class_='feedback__rating').get('class')[-1][-1]
        review_text = feedback.find('p', class_='feedback__text').get_text()
        info.append({
            'hash': hash(review_text),
            'review_date': review_date,
            'review_rating': review_rating,
            'review_text': review_text
        })
    return info
 
def get_last_review(html):
    last_review_rating = last_review_date = 0
    soup = BeautifulSoup(html, 'lxml')
    last_feedback = soup.find('li', class_='comments__item feedback')
    try:
        last_review_date = soup.find('span', class_='feedback__date').get('content')
        last_review_rating = soup.find('span', class_='feedback__rating').get('class')[-1][-1]
        feedback_reply = last_feedback.find('div', class_='feedback__sellers-reply')

        return {
            'raiting': last_review_rating,
            'date': last_review_date,
            'feedback_reply': True if feedback_reply else False
        }
    except:
        return {
            'raiting': None,
            'date': last_review_date,
        }

def get_detail_info(id):
    detailURL = f'https://www.wildberries.ru/catalog/{id}/detail.aspx?targetUrl=SP'
    html = get_html(detailURL)
    info = {
        'articul': id,
        'price': get_price_for_visa_and_MC(html),
        'reviewCount': get_review_count(html),
        'raiting': get_raiting(html),
        'last_review': get_last_review(html),
        'all_reviews': get_all_reviews(html)
    }
    logging.debug(info)
    return info


def get_price(card_info: Dict[str, str] ) -> int:
    price = card_info['data']['products'][0]['salePriceU']
    logging.debug(f'{price}')
    return price

def get_review_count(card_info) -> int:
    review_count = card_info['data']['products'][0]['feedbacks']
    logging.debug(f'{review_count}')
    return review_count


def get_imtId(card_info) -> int:
    return card_info['data']['products'][0]['root']


def get_raiting(card_info) -> int:
    imtId = get_imtId(card_info)
    url = 'https://public-feedbacks.wildberries.ru/api/v1/summary/full'
    response = requests.post(url, json={'imtId': imtId, 'skip': 0, 'take': 30})
    if response.status_code == 200:
        raiting = response.json()['valuation']
        logging.debug(f'{imtId}: {raiting}')


def get_detail_info(id):
    url = f'https://card.wb.ru/cards/detail?spp=19&regions=68,64,83,4,38,80,33,70,82,86,30,69,22,66,31,48,1,40&pricemarginCoeff=1.0&reg=1&appType=1&emp=0&locale=ru&lang=ru&curr=rub&couponsGeo=12,7,3,6,18,22,21&dest=-1075831,-79374,-367666,-2133466&nm={id}'
    card_info = requests.get(url).json()

    info = {
        'articul': id,
        'price': get_price(card_info),
        'reviewCount': get_review_count(card_info),
        'raiting': get_raiting(card_info),
        'last_review': None,
        'all_reviews': None
    }
    logging.debug(info)
    return info
    
if __name__ == '__main__':
    print(get_detail_info(41928972))

