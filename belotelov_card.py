
import os
import sys
# from card import update_sheet
import datetime as dt
from time import time

from dotenv import load_dotenv
from update_card import update_sheet
# получаем имя клиента капсом
client = os.path.splitext (os.path.basename (sys.argv [0]))[0].split('_')[0].upper()
load_dotenv()
# TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
ID_FOR_NOTIFICATION = os.environ['ID_FOR_NOTIFICATION'].split(',')
# #берем соответвтующей id в .env
SPREADSHEET_ID = os.environ[f'{client}_SPREADSHEET_ID']

range_name = dt.datetime.now().strftime('%m.%Y')
while True:
    update_sheet(SPREADSHEET_ID,range_name)
