
import os
import sys
import datetime as dt

from dotenv import load_dotenv
from update_card import update_sheet
client = os.path.splitext(os.path.basename(sys.argv[0]))[0].split('_')[0].upper()
load_dotenv()
ID_FOR_NOTIFICATION = os.environ['ID_FOR_NOTIFICATION'].split(',')
SPREADSHEET_ID = os.environ[f'{client}_SPREADSHEET_ID']

range_name = dt.datetime.now().strftime('%m.%Y')

update_sheet(SPREADSHEET_ID, range_name)