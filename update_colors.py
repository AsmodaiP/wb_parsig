from enum import Enum
from lib2to3.pytree import convert
from logging.handlers import RotatingFileHandler
import logging
import os.path
from time import sleep, time
from typing import final
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from google.oauth2 import service_account
import datetime as dt
from rsa import verify
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
SERVICE_ACCOUNT_FILE = 'credentials_service.json'
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

INDEX_OF_FIRST = 1

START_POSITION_FOR_PLACE = 18


def convert_16_to_10(hex_string):
    return int(hex_string, 16)

def rgb_to_percentile(rgb):
    # rgb = '#00FF00'

    return (convert_16_to_10(rgb[1:3])/255, convert_16_to_10(rgb[3:5])/255, convert_16_to_10(rgb[5:7])/255)


class Colors(Enum):
    green_color_rgb = rgb_to_percentile('#d9ead3')
    vivid_green_color_rgb = rgb_to_percentile('#b6d7a8')
    red_color_rgb = rgb_to_percentile('#ea9999')
    vivid_red_color_rgb = rgb_to_percentile('#e06666')  # 'ff2400
    default = rgb_to_percentile('#fce5cd')


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


def convert_to_column_letter(column_number):
    column_letter = ''
    while column_number != 0:
        c = ((column_number - 1) % 26)
        column_letter = chr(c + 65) + column_letter
        column_number = (column_number - c) // 26
    return column_letter


def get_request_for_change_color(sheet_id, spreadsheet_id, row, column, previous_position, position):
    
    color = Colors.default
    try:
        delta = int(previous_position) - int(position)
        if 10 > delta > 0:
            color = Colors.green_color_rgb
        elif delta >= 10:
            color = Colors.vivid_green_color_rgb

        elif -10 < delta < 0:
            color = Colors.red_color_rgb
        elif delta < -10:
            color = Colors.vivid_red_color_rgb
    except:
        pass
    color = color.value
    return {
        'repeatCell': {
            'range': {
                'sheetId': sheet_id,
                'startRowIndex': row,
                'endRowIndex': row+1,
                'startColumnIndex': column,
                'endColumnIndex': column+1
            },
            'cell': {
                'userEnteredFormat': {
                    'backgroundColor': {
                        'red': color[0],
                        'green': color[1],
                        'blue': color[2],
                        'alpha': 0.1
                    }
                }
            },
            'fields': 'userEnteredFormat.backgroundColor'
        }
    }


def get_sheet_id_by_name(name, spreadsheet_id):
    service = build('sheets', 'v4', credentials=credentials)
    sheet_metadata = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id).execute()
    sheets = sheet_metadata.get('sheets', '')
    for item in sheets:
        if item.get('properties').get('title') == name:
            return item.get('properties').get('sheetId')
    return None


def update_colors(spreadsheet_id, range_name, day):
    sheet_id = get_sheet_id_by_name(range_name, spreadsheet_id)
    

    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id,
                                range=range_name, majorDimension='ROWS').execute()
    values = result.get('values', [])
    requests_for_change_color = []
    
    for day in range(1,31):
        i = INDEX_OF_FIRST
        position_for_place = START_POSITION_FOR_PLACE + \
            (day - 1) * 6
        previous_position_place = START_POSITION_FOR_PLACE + \
            (day - 2) * 6
        
        for row in values:
            try:
                if i < 0:
                    raise
                try:
                    position = (row[position_for_place-1])
                except:
                    position = 0
                try:
                    
                    previous_position = (row[previous_position_place-1])
                except:
                    previous_position = 0
                requests_for_change_color.append(get_request_for_change_color(
                    sheet_id, spreadsheet_id, i-1, position_for_place-1, previous_position, position))

            except Exception as ex:
                print(f"ошибка {ex}")
            finally:
                i += 1

    body = {
        'requests': requests_for_change_color
    }
    print(len(requests_for_change_color))
    if requests_for_change_color:
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()


if __name__ == '__main__':
    # example 07.2022
    date = dt.datetime.now().strftime('%m.%Y')
    # print(date)
    # change_cell_color(date, '1LMqyN5w81xnRfvNf0CE75ozH7zMcTLhvYiNjTxHDURo', 1, 1, (255, 0, 0))
    # update_sheet('1LMqyN5w81xnRfvNf0CE75ozH7zMcTLhvYiNjTxHDURo', date)

    update_colors('1LMqyN5w81xnRfvNf0CE75ozH7zMcTLhvYiNjTxHDURo', '09.2022', 'day')

