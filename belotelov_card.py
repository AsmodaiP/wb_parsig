
from logging.handlers import RotatingFileHandler
import logging
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
SPREADSHEET_ID = os.environ[f'{client}_SPREADSHEET_ID']
RANGE_NAME = os.environ['RANGE_NAME']

bot = telebot.TeleBot(TELEGRAM_TOKEN)

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
    if info['price'] != 'Нет в наличии'  and info['price'].strip() not in prev_price.strip():
        body['data'] +=  {'range': f'{range_name}!I{i}', 'values': [[prev_price]]},
    return body

def update_sheet():
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                range=RANGE_NAME, majorDimension='ROWS').execute()
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
                    body = get_body(RANGE_NAME, i, info, prev_price=row[9])


                    sheet.values().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
                    bot.send_message(295481377, f'Товар [«{row[4]}»](https://www.wildberries.ru/catalog/{articulus}/detail.aspx?targetUrl=SP) \n Цена - {info["price"]} ,\n Рейтинг - {info["raiting"]}', parse_mode='Markdown')
            except Exception as e:
                logging.info(f'С {articulus} что-то не так')
                logging.error('ошибка', exc_info=e)

            i += 1



def convert_to_column_letter(column_number):
    column_letter = ''
    while column_number != 0:
        c = ((column_number-1) % 26)
        column_letter = chr(c+65)+column_letter
        column_number = (column_number-c)//26
    return column_letter


def main():
    update_sheet()

def check_sheet_exitst_by_title(title):
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()
    sheet_metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheets = sheet_metadata.get('sheets', '')
    for item in sheets:
        if item.get("properties").get('title') == title:
            return True
        return False

if __name__ == '__main__':
    print()
    main()
