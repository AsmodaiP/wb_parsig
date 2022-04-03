import logging
from bs4 import BeautifulSoup
from pyasn1_modules.rfc2459 import DistributionPoint
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

headers = {
    "Accept": "*/*",
    "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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
    try:
        driver.set_window_size(1920, 1080)
        driver.set_page_load_timeout(30)
        driver.get(url)
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
    review_count = soup.select('meta[itemprop="reviewCount"]')
    if len(review_count) == 0:
        return 0
    rc = review_count[0].get('content')
    return rc


def get_detail_info(id):
    detailURL = f'https://www.wildberries.ru/catalog/{id}/detail.aspx?targetUrl=SP'
    html = get_html(detailURL)
    info = {
        'articul': id,
        'price': get_price_for_visa_and_MC(html),
        'reviewCount': get_review_count(html),
        'raiting': get_raiting(html),
        'last_review': get_last_review(html)
    }
    logging.info(info)
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

if __name__ == '__main__':
    get_detail_info(38678060)
    # get_last_review