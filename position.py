from logging.handlers import RotatingFileHandler
import logging
import os.path
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from google.oauth2 import service_account
import datetime as dt
import telebot
from dotenv import load_dotenv
import sys
from user_agent import generate_user_agent
import asyncio
import aiohttp
import json


load_dotenv()

load_dotenv()


client = os.path.splitext(os.path.basename(sys.argv[0]))[
    0].split('_')[0].upper()

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
ID_FOR_NOTIFICATION = os.environ['ID_FOR_NOTIFICATION'].split(',')
# #берем соответвтующей id в .env
SPREADSHEET_ID = None
RANGE_NAME = os.environ['RANGE_NAME']

bot = telebot.TeleBot(TELEGRAM_TOKEN)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'credentials_service.json')
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

INDEX_OF_FIRST = 1

START_POSITION_FOR_PLACE = 18


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


def get_WB_articuls_and_query(colum_of_articul=7, colum_of_query=5):
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()
    query = '_'
    articuls_and_query_dict = {}
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                range=RANGE_NAME, majorDimension='ROWS').execute()
    values = result.get('values', [])
    if not values:
        print('No data found.')
    else:
        for row in values:
            if row[colum_of_articul].isdigit():
                if row[colum_of_query] != '':
                    query = row[colum_of_query]
                articuls_and_query_dict[row[colum_of_articul]] = query
    return articuls_and_query_dict


async def parser(query, target_id):
    page = 1
    position = 1
    flag = True
    headers = {
        "Accept": "*/*",
        "User-Agent": generate_user_agent()
    }
    finded_position = None
    async with aiohttp.ClientSession() as session:
        while flag:
            url = "https://search.wb.ru/exactmatch/ru/common/v4/search" \
                  "?appType=1" \
                  "&curr=rub" \
                  "&dest=-1029256,-102269,-1278703,-1255563" \
                  "&emp=0" \
                  "&lang=ru" \
                  "&locale=ru" \
                  f"&page={page}" \
                  "&pricemarginCoeff=1.0" \
                  f"&query={query}" \
                  "&reg=0" \
                  "&regions=68,64,83,4,38,80,33,70,82,86,75,30,69,22,66,31,48,1,40,71" \
                  "&resultset=catalog" \
                  "&sort=popular" \
                  "&spp=0" \
                  "&stores=117673,122258,122259,125238,125239,125240,6159,507,3158,117501,120602,120762,6158,121709,124731,159402,2737,130744,117986,1733,686,132043,1193"
            if page < 50:
                logging.info('Парсинг страницы ' + str(page))
                async with session.get(url=url, headers=headers) as r:
                    html_cod = await r.text()
                    try:
                        products = json.loads(html_cod)['data']['products']
                        if len(products) > 0:
                            for product in products:
                                id = product['id']
                                if id == target_id:
                                    finded_position = position
                                    return finded_position
                                position += 1
                        else:
                            flag = False
                            return '5000+'
                    except Exception as ex:
                        print(f"ошибка {ex}")
                        flag = False
                    finally:
                        page += 1
            else:
                return '5000+'


blacklist = []


def update_sheet(spreadsheet_id, range_name):
    position_for_place = START_POSITION_FOR_PLACE + \
        (dt.date.today().day - 1) * 6
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id,
                                range=range_name, majorDimension='ROWS').execute()
    values = result.get('values', [])
    data = []
    if not values:
        print('No data found.')
    else:
        i = INDEX_OF_FIRST
        query = '_'
        for row in values:
            if i < 0:
                i += 1
                continue
            try:
                articulus = row[7]
                price = row[11]
                logging.info(f'{articulus} {price}')
                position_for_place = START_POSITION_FOR_PLACE + \
                    (dt.date.today().day - 1) * 6
                if articulus.isdigit():
                    if int(articulus) in blacklist:
                        i += 1
                        continue
                    new_query = row[5]
                    if len(new_query) > 0:
                        query = new_query
                    if not price == 'Нет в наличии':
                        loop = asyncio.get_event_loop()
                        position = loop.run_until_complete(
                            parser(query, int(articulus)))
                    else:
                        position = 'Нет в наличии'
                    letter_for_range = convert_to_column_letter(
                        position_for_place)
                    if position is not None: 
                        position = f'{position}'
                        data += {'range': f'{range_name}!{letter_for_range}{i}',
                                'values': [[position]]},
            except Exception as e:
                logging.warning(e)
                pass
            i += 1
        body = {
            'valueInputOption': 'USER_ENTERED',
            'data': data}
        logging.info(body)
        sheet.values().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()


def get_position_on_the_page(page, query, articulus):
    id = 'c' + str(articulus)
    search_url = f'https://www.wildberries.ru/catalog/0/search.aspx?page={page}&search={query}'
    html = get_html(search_url)
    soup = BeautifulSoup(html, 'lxml')
    card_product = soup.find('div', id=id)
    return int(card_product['data-card-index']) + 1


def get_position(articulus, query):
    id = 'c' + str(articulus)
    page = 1
    success = False
    count_of_advertisement = 0
    count = 0
    while not success:
        query = query.strip()
        search_url = f'https://www.wildberries.ru/catalog/0/search.aspx?page={page}&search={query}'
        EXCEPTIONS_FOR_URL = {
            'Платье женское ': f'https://www.wildberries.ru/catalog/zhenshchinam/odezhda/platya?sort=popular&page={page}',
            'Платье женское': f'https://www.wildberries.ru/catalog/zhenshchinam/odezhda/platya?sort=popular&page={page}',
            'Шорты женские': f'https://www.wildberries.ru/catalog/zhenshchinam/odezhda/bryuki-i-shorty/shorty?sort=popular&page={page}',
            'Костюм женский': f'https://www.wildberries.ru/catalog/zhenshchinam/odezhda/kostyumy?sort=popular&page={page}',
            'Шорты женские ': f'https://www.wildberries.ru/catalog/zhenshchinam/odezhda/bryuki-i-shorty/shorty?sort=popular&page={page}'
        }
        if query in EXCEPTIONS_FOR_URL:
            search_url = EXCEPTIONS_FOR_URL[query]
        html = get_html(search_url)
        soup = BeautifulSoup(html, 'lxml')
        card_product = soup.find('div', id=id)
        # На первой странице проверяем, сколько рекламных объявлений
        # И если наш товар на ней, то считаем, сколько нерекламных до него
        if page == 1:
            advertisements = soup.find_all('div', class_='advert-card-item')
            if not card_product is None:
                all_cards = soup.find_all('div', class_='product-card')
                for card in all_cards:
                    if not 'advert-card-item' in card['class']:
                        count += 1
                    if card['id'] == id:
                        return count
            count_of_advertisement += len(advertisements)
        if card_product is None:
            count += len(soup.find_all('div', class_='product-card'))
            page += 1
            if page > 10:
                return 1000
            if len(soup.find_all('div', class_='product-card', limit=1)) == 0:
                return 0
        else:
            success = True
            return(count + int(card_product['data-card-index']) + 1 - count_of_advertisement)


def convert_to_column_letter(column_number):
    column_letter = ''
    while column_number != 0:
        c = ((column_number - 1) % 26)
        column_letter = chr(c + 65) + column_letter
        column_number = (column_number - c) // 26
    return column_letter


def main():
    while True:
        update_sheet(SPREADSHEET_ID)


def check_sheet_exitst_by_title(title):
    service = build('sheets', 'v4', credentials=credentials)
    sheet_metadata = service.spreadsheets().get(
        spreadsheetId=SPREADSHEET_ID).execute()
    sheets = sheet_metadata.get('sheets', '')
    for item in sheets:
        if item.get('properties').get('title') == title:
            return True
        return False


if __name__ == '__main__':
    pass
