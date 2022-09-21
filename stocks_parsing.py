
import logging
import os.path
from googleapiclient.discovery import build
from google.oauth2 import service_account
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'credentials_service.json')
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

STOCK_SHEET_ID = os.environ['STOCK_SHEET_ID']
FULL_INFO_SHEET_ID = os.environ['FULL_INFO_ID']


def get_stocks(stocks_sheet_id):
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=stocks_sheet_id,
                                range='Остатки ФБО!A:Z').execute()
    values = result.get('values', [])
    for row in values:
        try:
            
            result[row[5]] = {
                'WB_article': row[3],
                'size': row[6],
                'article': row[4],
                'fbo_count': int(row[8]) if row[8] else 0,
                'fbs_count': int(row[21]) if row[21] else 0,
            }
        except Exception as e:
            logging.error(e, exc_info=True)
            pass
    return result


def add_info_about_wb_article_and_size(full_info_sheet_id, stocks_info):
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=full_info_sheet_id,
                                range='Товары!A:Z').execute()
    values = result.get('values', [])
    result = {}
    for stock in stocks_info:
        for row in values:
            if row[5] == stock:
                stocks_info[stock]['WB_article'] = row[3]
                stocks_info[stock]['size'] = row[6]
                break
    return stocks_info


def create_request(spreadsheet_id, row, stocks_info, wb_article):
    info = find_all_stocks_by_wb_article(wb_article, stocks_info)
    info = sorted(info, key=lambda x: x['fbs_count'] + x['fbo_count'], reverse=True)
    values = []
    for stock in info:
        values.append(
            {"userEnteredValue": f'{stock["size"]}: {stock["fbs_count"]}, {stock["fbo_count"]}.'})

    request = {
        "setDataValidation": {
            "range": {
                "sheetId": 794038833,
                "startRowIndex": row-1,
                "endRowIndex": row,
                "startColumnIndex": 10,
                "endColumnIndex": 11
            },
            "rule": {
                "condition": {
                    "type": 'ONE_OF_LIST',
                    "values": values
                },
                "showCustomUi": True,
                "strict": True
            }
        }
    }

    return request


def find_all_stocks_by_wb_article(wb_article, stocks_info):
    result = []
    for stock in stocks_info:
        try:
            if stocks_info[stock]['WB_article'] == wb_article:
                result.append(stocks_info[stock])
        except Exception as e:
            # logging.error(e, exc_info=True)
            pass
    return result


def format_stocks_info(stocks_info, wb_article):
    info = find_all_stocks_by_wb_article(wb_article, stocks_info)
    info = sorted(info, key=lambda x: x['fbs_count'] + x['fbo_count'], reverse=True)
    msg = ''
    for stock in info:
        msg += f'{stock["size"]+":" if len(info)>1 else ""} {stock["fbs_count"]}, {stock["fbo_count"]}.\n'
    if len(info) > 1:
        msg += f'Всего: {sum(int(x["fbs_count"])for x in info)}, {sum(int(x["fbo_count"]) for x in info)}.'
    return msg


stocks_info = add_info_about_wb_article_and_size(FULL_INFO_SHEET_ID, get_stocks(STOCK_SHEET_ID))

print(get_stocks(STOCK_SHEET_ID))

def update_sheet(spreadsheet_id, range_name, stocks_info):
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id,
                                range=range_name, majorDimension='ROWS').execute()
    values = result.get('values', [])
    body_data = []
    if not values:
        print('No data found.')
        return
    for i, row in enumerate(values, 1):
        try:
            article = row[6]
            if article.isdigit():

                stocks = format_stocks_info(stocks_info, article)
                info = find_all_stocks_by_wb_article(article, stocks_info)
                info = sorted(info, key=lambda x: x['fbs_count'] + x['fbo_count'], reverse=True)
                all_sum = f'{sum(int(x["fbs_count"])for x in info)}, {sum(int(x["fbo_count"]) for x in info)}'

                if stocks:
                    body_data.append([{'range': f'{range_name}!K{i}', 'values': [[stocks]]}])
                    body_data.append([{'range': f'{range_name}!N{i}', 'values': [[all_sum]]}])
        except Exception as e:
            logging.error(e, exc_info=True)
            pass
    body = {
        'valueInputOption': 'USER_ENTERED',
        'data': body_data
    }

    sheet.values().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

import datetime
date = datetime.datetime.now().strftime('%d.%m.%Y')
update_sheet('1LMqyN5w81xnRfvNf0CE75ozH7zMcTLhvYiNjTxHDURo', '09.2022', stocks_info)

