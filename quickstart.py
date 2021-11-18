from __future__ import print_function
from logging import info
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
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'credentials.json')
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

INDEX_OF_FIRST = 1
SAMPLE_SPREADSHEET_ID = '1lRSNP64F-H8Cdz7brzgF5y-P8K3izQzN4iXYeNiums4'
SAMPLE_RANGE_NAME = '04.2021'
START_POSITION_FOR_PLACE = 17


position_for_place = START_POSITION_FOR_PLACE + (dt.date.today().day-1)*6


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


# blacklist =[39260058,42525405,42525640,43370556,16813287,39999746,16813676,36850119,23648568,36661756,34778015,35107438,35262469,42513555,43725639, 35266960, 36402995,42306411]
blacklist = []


def update_sheet():
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

            if articulus.isdigit():
                if int(articulus) in blacklist:
                    i += 1
                    continue
                new_query = row[5]
                if len(new_query) > 0:
                    query = new_query

                info = get_detail_info(articulus)
                position = get_position(articulus, query)
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
                print(body['data'])
                sheet.values().batchUpdate(spreadsheetId=SAMPLE_SPREADSHEET_ID, body=body).execute()
            i += 1


def get_position_on_the_page(page, query, articulus):
    id = 'c' + str(articulus)
    search_url = f'https://www.wildberries.ru/catalog/0/search.aspx?page={page}&search={query}'
    soup = BeautifulSoup(get_html(search_url), 'lxml')
    card_product = soup.find('div', id=id)
    return int(card_product['data-card-index']) + 1


def get_position(articulus, query):
    id = 'c' + str(articulus)
    page = 1
    success = False

    while not success:
        search_url = f'https://www.wildberries.ru/catalog/0/search.aspx?page={page}&search={query}'
        EXCEPTIONS_FOR_URL = {
            'Платье женское ': f'https://www.wildberries.ru/catalog/zhenshchinam/odezhda/platya?sort=popular&page={page}',
            'Платье женское': f'https://www.wildberries.ru/catalog/zhenshchinam/odezhda/platya?sort=popular&page={page}',
        }
        if query in EXCEPTIONS_FOR_URL:
            search_url = EXCEPTIONS_FOR_URL[query]
        soup = BeautifulSoup(get_html(search_url), 'lxml')
        card_product = soup.find('div', id=id)
        if card_product is None:
            page += 1
            if page > 10:
                return 100
            if len(soup.find_all('div', class_='product-card', limit=1)) == 0:
                return 0
        else:
            success = True
            return((page-1)*100+4+int(card_product['data-card-index']) + 1)


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

