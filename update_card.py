

import logging
import os.path
from time import sleep
from googleapiclient.discovery import build
from google.oauth2 import service_account
import datetime as dt
import parsing_by_wb_api


SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'credentials_service.json')
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

INDEX_OF_FIRST = 1
START_POSITION_FOR_PLACE = 17


def update_sheet(spreadsheet_id, range_name):
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id,
                                range=range_name, majorDimension='ROWS').execute()
    values = result.get('values', [])
    data = []
    i = INDEX_OF_FIRST
    for row in values:
        logging.info(row[:15])
        try:
            article = row[6]
            info = parsing_by_wb_api.get_detail_info(int(article))
            previous_price = ''.join(filter(str.isalnum, row[9]))
            if str(info['price']).replace(' ', '') != previous_price:
                print(f'{previous_price} \n\n\n\n\n')
                data += [{'range': f'{range_name}!H{i}',
                          'values': [[f'{previous_price} {dt.datetime.now().strftime("%H:%M  %d.%m")}']]}]
            data += [
                {'range': f'{range_name}!J{i}', 'values': [[info['price']]]},
                {'range': f'{range_name}!I{i}', 'values': [[info['client_price']]]},
                {'range': f'{range_name}!L{i}:M{i}', 'values': [[info['raiting'], info['reviewCount']]]},
            ]
        except Exception as e:
            logging.info(f'С {article} что-то не так', exc_info=e)
        i += 1
    body = {
        'valueInputOption': 'USER_ENTERED',
        'data': data
    }
    sheet.values().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
    data = []


if __name__ == '__main__':
        update_sheet('1m_IcullUpEP4yOOnOH7ojBzbPpn38tFtVNyS40yKJjQ', '06.2022')