import logging
from typing import Dict
import requests
import os

headers = {
    "Accept": "*/*",
    "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(level=logging.INFO, format='%(levelname)-s %(asctime)-s %(message)s')


def get_price(card_info: Dict[str, str]) -> int:
    price = card_info['data']['products'][0]['salePriceU']
    logging.debug(f'{price}')
    return price//100


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
        return raiting


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
    logging.info(info)
    return info

if __name__ == '__main__':
    get_detail_info(81311458)
