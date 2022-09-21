from cachetools import TTLCache
import logging
from typing import Dict
import requests
import os
from dotenv import load_dotenv
load_dotenv()

headers = {
    "Accept": "*/*",
    "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(level=logging.INFO, format='%(levelname)-s %(asctime)-s %(message)s')
cache = TTLCache(maxsize=10, ttl=360)

def get_price(card_info: Dict[str, str]) -> int:
    try:
        price = card_info['data']['products'][0]['extended']['promoPriceU']
        if 'promoPriceU' in card_info['data']['products'][0]['extended']:
            price = card_info['data']['products'][0]['extended']['promoPriceU']
    except KeyError:
        price = card_info['data']['products'][0]['extended'].get('basicPriceU', card_info['data']['products'][0]['priceU'])

    return price//100


def get_review_count(card_info) -> int:
    review_count = card_info['data']['products'][0]['feedbacks']
    logging.debug(f'{review_count}')
    return review_count

import time

def get_imtId(card_info) -> int:
    return card_info['data']['products'][0]['root']


def get_client_price(card_info) -> int:
    try:
        print(card_info)
        price_after_spp = card_info['data']['products'][0]['extended']['clientPriceU']//100
    except KeyError:
        pass
    try:
        price_after_spp = card_info['data']['products'][0]['salePriceU']//100
    except KeyError:
        return ''
    return price_after_spp


def get_raiting(card_info) -> int:
    imtId = get_imtId(card_info)
    url = 'https://public-feedbacks.wildberries.ru/api/v1/summary/full'
    response = requests.post(url, json={'imtId': imtId, 'skip': 0, 'take': 30})
    if response.status_code == 200:
        raiting = response.json()['valuation']
        logging.debug(f'{imtId}: {raiting}')
        return raiting


def timeit(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        logging.info(f'{func.__name__} took {end-start} seconds')
        return result
    return wrapper

@timeit
def get_spp():
    if 'spp' in cache:
        return cache['spp']
    token = os.environ.get('WILDAUTHNEW_V3')
    
    url = 'https://www.wildberries.ru/webapi/personalinfo'
    response = requests.post(url, headers={'Cookie': f'WILDAUTHNEW_V3={token}'})
    if response.status_code == 200:
        spp = response.json()['value']['personalDiscount']
        cache['spp'] = spp
        return spp
    

def get_detail_info(id):
    spp = get_spp()
    url = f'https://card.wb.ru/cards/detail?spp={spp}&regions=68,64,83,4,38,80,33,70,82,86,30,69,22,66,31,48,1,40&pricemarginCoeff=1.0&reg=1&appType=1&emp=0&locale=ru&lang=ru&curr=rub&couponsGeo=12,7,3,6,18,22,21&dest=-1075831,-79374,-367666,-2133466&nm={id}'
    card_info = requests.get(url).json()
    
    reviews = get_reviews(id)
    info = {
        'articul': id,
        'price': get_price(card_info),
        'client_price': get_client_price(card_info),
        'reviewCount': len(reviews),
        'raiting': round(sum(review['productValuation'] for review in reviews)/len(reviews),2) if reviews else 0,
        'last_review': None,
        'all_reviews': None
    }
    logging.info(info)
    return info


def get_all_feedbacks(rootId):
    skip = 0
    raw_data = {"imtId": rootId, "skip": skip, "take": 30, "order": "dateDesc"}
    all_feedbacks = []
    while True:
        raw_data["skip"] = skip
        response = requests.post("https://public-feedbacks.wildberries.ru/api/v1/summary/full", json=raw_data)
        if response.status_code == 200:
            data = response.json()['feedbacks']
            if data == [] or data is None:
                break
            all_feedbacks.extend(data)
            skip += 30
    return all_feedbacks

def search_rootId(imtId):
    url = (
        "https://card.wb.ru/cards/detail?spp=0&regions=68,64,83,4,38,80,33,70,82,86,75,30,69,22,66,31,48,1,40,71&stores=117673,122258,122259,125238,125239,125240,6159,507,3158,117501,120602,120762,6158,121709,124731,159402,2737,130744,117986,1733,686,132043&pricemarginCoeff=1.0&reg=0&appType=1&emp=0&locale=ru&lang=ru&curr=rub&couponsGeo=12,3,18,15,21&dest=-1029256,-102269,-1278703,-1255563&nm="
        + str(imtId)
        + ";64245978;64245979%27"
    )
    response = requests.get(url=url)
    response_message = response.json()
    for item in response_message["data"]["products"]:
        if item["id"] == imtId:
            rootId = int(item["root"])
    return rootId

def get_reviews(imtId):
    rootId = search_rootId(imtId)
    all_feedbacks = get_all_feedbacks(rootId)
    i = 0
    result = []
    for feedback in all_feedbacks:
        if feedback['productDetails']['nmId']==imtId:
                result.append(feedback)
    return result


if __name__ == '__main__':
    print(get_detail_info(17946742))
    # search_rootId(34778015)
    # for i in range(10):
        
    #     print(get_spp())


