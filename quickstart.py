from __future__ import print_function
from logging.handlers import RotatingFileHandler
import logging
import os.path
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from parsing import get_detail_info, get_html
import datetime as dt

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'credentials_service.json')
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

INDEX_OF_FIRST = 1
SAMPLE_SPREADSHEET_ID = '1m_IcullUpEP4yOOnOH7ojBzbPpn38tFtVNyS40yKJjQ'
SAMPLE_RANGE_NAME = '04.2021'
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


def get_WB_articuls_and_query(colum_of_articul=7, colum_of_query=5):
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()
    query = '_'
    articuls_and_query_dict = {}
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=SAMPLE_RANGE_NAME, majorDimension='ROWS').execute()
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


blacklist = [

]


def update_sheet():
    position_for_place = START_POSITION_FOR_PLACE + (dt.date.today().day-1)*6
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=SAMPLE_RANGE_NAME, majorDimension='ROWS').execute()
    values = result.get('values', [])
    if not values:
        print('No data found.')
    else:
        i = INDEX_OF_FIRST
        query = '_'
        for row in values:
            articulus = row[7]
            try:
                if articulus.isdigit():
                    if int(articulus) in blacklist:
                        i += 1
                        continue
                    new_query = row[5]
                    if len(new_query) > 0:
                        query = new_query
                    logging.info(f'Получение детальной информации для {row[4]}, {articulus}')
                    info = get_detail_info(articulus)
                    if info['price'] != ' ':
                        position = get_position(articulus, query)
                    else: 
                        position = 1000
                    logging.info(f'Позиция в выдаче {position}')
                    letter_for_range = convert_to_column_letter(position_for_place)
                    body = {
                        'valueInputOption': 'USER_ENTERED',
                        'data': [
                            {'range': f'I{i}', 'values': [[info['price']]]},
                            {'range': f'K{i}:L{i}', 'values': [
                                [info['raiting'], info['reviewCount']]]},
                            {'range': f'{letter_for_range}{i}',
                            'values': [[position]]},
                        ]
                    }
                    # print(body['data'])
                    sheet.values().batchUpdate(spreadsheetId=SAMPLE_SPREADSHEET_ID, body=body).execute()
            except:
                logging.info(f'С {articulus} что-то не так')
            i += 1


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
        search_url = f'https://www.wildberries.ru/catalog/0/search.aspx?page={page}&search={query}'
        EXCEPTIONS_FOR_URL = {
            'Платье женское ': f'https://www.wildberries.ru/catalog/zhenshchinam/odezhda/platya?sort=popular&page={page}',
            'Платье женское': f'https://www.wildberries.ru/catalog/zhenshchinam/odezhda/platya?sort=popular&page={page}',
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
            if  not card_product is None:
                all_cards =  soup.find_all('div', class_='product-card')
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
            return(count+int(card_product['data-card-index']) + 1 - count_of_advertisement)


def convert_to_column_letter(column_number):
    column_letter = ''
    while column_number != 0:
        c = ((column_number-1) % 26)
        column_letter = chr(c+65)+column_letter
        column_number = (column_number-c)//26
    return column_letter




def main():
    update_sheet()


if __name__ == '__main__':
    main()
    # print(get_position('18259329','брюки женские палаццо'))

    # count_of_advertisement = 0
    # page = 1
    # search_url = f'https://www.wildberries.ru/catalog/zhenshchinam/odezhda/platya?sort=popular&page={page}'
    # soup = BeautifulSoup(get_html(search_url), 'lxml')
    # cards = soup.find_all('div', class_='product-card')
    # print(cards[0].find_all('div', class_='advert-card-item'))
    # # print(cards[0].find_all('div', class_='product-card__wrapper'))
    #     # print(soup2.find_all('div', class_='advert-card-item'))
    # print(len(count_of_advertisement))
    