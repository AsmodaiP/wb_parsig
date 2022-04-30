

import json
from logging.handlers import RotatingFileHandler
import logging
from operator import add
import os.path
from googleapiclient.discovery import build
from google.oauth2 import service_account
from parsing import get_detail_info
import datetime as dt
import telebot
from dotenv import load_dotenv
import string 

import sys
import __main__

load_dotenv()
#получаем имя клиента капсом
client = os.path.splitext (os.path.basename (sys.argv [0]))[0].split('_')[0].upper()

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
ID_FOR_NOTIFICATION = os.environ['ID_FOR_NOTIFICATION'].split(',')
TOKEN_FOR_REVIEWS = os.environ['TOKEN_FOR_REVIEWS']
ID_FOR_REVIEWS = os.environ['ID_FOR_REVIEWS']
SPREADSHEET_ID = None
RANGE_NAME = os.environ['RANGE_NAME']

bot = telebot.TeleBot(TELEGRAM_TOKEN)
bot_for_reviews=telebot.TeleBot(TOKEN_FOR_REVIEWS)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'credentials_service.json')
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

INDEX_OF_FIRST = 1
START_POSITION_FOR_PLACE = 17


log_dir = os.path.join(BASE_DIR, 'logs/')
log_file = os.path.join(BASE_DIR, 'logs/parsing.log')
console_handler = logging.StreamHandler()
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=100000,
    backupCount=3,
    encoding='utf-8'
)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(message)s',
    handlers=(
        file_handler,
        console_handler
    )
)


def get_body(range_name, i, info, prev_price):
    if info['price'] == '':
        info['raiting'] = 'Нет в наличии'
        info['price']=' Нет в наличии'
    
    prev_price = prev_price.strip().replace(' ', '').replace(' ', '')
    info['price'] = info['price'].strip().replace(' ', '').replace(' ', '')
    if info['price'] == '':
        info['raiting'] = 'Нет в наличии'
        info['price']=' Нет в наличии'

    prev_price = ''.join([x if x in string.printable else '' for x in prev_price])
    info['price'] = ''.join([x if x in string.printable else '' for x in info['price']])
    body = {
    'valueInputOption': 'USER_ENTERED',
    'data': [
        {'range': f'{range_name}!J{i}', 'values': [[info['price']]]},
        {'range': f'{range_name}!L{i}:M{i}', 'values': [
            [info['raiting'], info['reviewCount']]]},
            {'range': f'{range_name}!B{i}', 'values': [[dt.datetime.now().strftime("%H:%M  %d.%m.%y")]]}
    ]
    }
    if info['price'] != 'Нет в наличии'  and info['price'].strip() != prev_price.strip():
        body['data'] +=  {'range': f'{range_name}!I{i}', 'values': [[f'{prev_price} {dt.datetime.now().strftime("%H:%M  %d.%m")}']]},
    return body

def update_sheet(spreadsheet_id, range_name, check_review=False, add_reviews=False):
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id,
                                range=range_name, majorDimension='ROWS').execute()
    values = result.get('values', [])
    if not values:
        print('No data found.')
    else:
        i = INDEX_OF_FIRST
        for row in values:
            try:
                articulus = row[7]
                if articulus.isdigit():
                    logging.info(
                        f'Получение детальной информации для {row[4]}, {articulus}')
                    info = get_detail_info(articulus)
                    if check_review:
                        check_last_review(articulus, info['last_review'], row[6])
                    if add_reviews:
                        update_all_reviews(articulus, reviews=info['all_reviews'], spreadsheet_id=spreadsheet_id)
                    body = get_body(range_name, i, info, prev_price=row[9])


                    sheet.values().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
                    bot.send_message(295481377, f'Товар [«{row[4]}»](https://www.wildberries.ru/catalog/{articulus}/detail.aspx?targetUrl=SP) \n Цена - {info["price"]} ,\n Рейтинг - {info["raiting"]}', parse_mode='Markdown')
            except Exception as e:
                logging.info(f'С {articulus} что-то не так')
                logging.error('ошибка', exc_info=e)
            i += 1

def update_all_reviews(article, reviews, spreadsheet_id):
    range_name = 'Отзывы'
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id,
                                range=f'{range_name}!E:E', majorDimension='ROWS').execute()
    values = result.get('values', [])
    position_for_place = len(values)+1
    all_review_text = [value[0] for value in values]

    body_data = []
    for review in reviews:
        if review['review_text'] in all_review_text:
            continue
        body_data.append(
            [
                {'range': f'{range_name}!A{position_for_place}', 'values': [[review['hash']]]},
                {'range': f'{range_name}!C{position_for_place}', 'values': [[article]]},
                {'range': f'{range_name}!B{position_for_place}', 'values': [[review['review_date']]]},
                {'range': f'{range_name}!D{position_for_place}', 'values': [[review['review_rating']]]},
                {'range': f'{range_name}!E{position_for_place}', 'values': [[review['review_text']]]},
            ]
        )
        position_for_place+=1
    body = {
    'valueInputOption': 'USER_ENTERED',
    'data': body_data
    }
    sheet.values().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()



def convert_to_column_letter(column_number):
    column_letter = ''
    while column_number != 0:
        c = ((column_number-1) % 26)
        column_letter = chr(c+65)+column_letter
        column_number = (column_number-c)//26
    return column_letter


def check_sheet_exitst_by_title(title):
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()
    sheet_metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheets = sheet_metadata.get('sheets', '')
    for item in sheets:
        if item.get("properties").get('title') == title:
            return True
        return False

def check_last_review(articul, review, name):
    
    if review['raiting'] is None:
        return
    with open('reviews.json', 'r') as f:
        reviews = json.load(f)
        if articul in reviews:
            last_date = reviews[articul]['date']
            if int(review['raiting']) < 4 and review['date'] != last_date:
                print(review)
                bot_for_reviews.send_message(
                    ID_FOR_REVIEWS,
                    f'Негативный неотвеченный отзыв ({review["raiting"]} звезды) на товар [«{name}»](https://www.wildberries.ru/catalog/{articul}/detail.aspx?targetUrl=SP)',
                    disable_web_page_preview=True,
                    parse_mode='Markdown')
        elif int(review['raiting'])< 4:
            bot_for_reviews.send_message(
                ID_FOR_REVIEWS,
                f'Негативный неотвеченный отзыв ({review["raiting"]} звезды) на товар [«{name}»](https://www.wildberries.ru/catalog/{articul}/detail.aspx?targetUrl=SP)',
                disable_web_page_preview=True,
                parse_mode='Markdown')
        reviews[articul] = review
    with open('reviews.json', 'w') as f:
        json.dump(reviews, f, indent=4)
if __name__ == '__main__':
    
    bot_for_reviews.send_message(1126541068, '22')
    pass
