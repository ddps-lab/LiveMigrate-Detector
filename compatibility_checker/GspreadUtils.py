import pandas as pd
from pathlib import Path

import gspread as gs
from gspread_formatting import *

root_path = str(Path(__file__).resolve().parent)
gc = gs.service_account(filename=f'{root_path}/secure-outpost-380004-e4e1eebe8a35.json')

def read_gspread(worksheet):
    sheet = gc.open('us-west-2 x86 isa set').worksheet(worksheet)
    df = pd.DataFrame(sheet.get_all_records())
    
    return df

def write_gspread(worksheet, df):
    '''
    The function writes the contents of the dataframe to a Google Spreadsheet.
    '''
    # write google spread sheet1(core features)
    sheet = gc.open('us-west-2 x86 isa set').worksheet(worksheet)
    sheet.clear() # 이전 데이터 삭제
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

    format_cell = cellFormat(
        verticalAlignment='MIDDLE', 
        wrapStrategy='OVERFLOW_CELL', 
        textFormat=textFormat(fontSize=10)
    )

    format_cell_range(sheet, '1:500', format_cell)

def read_CPU_Feature_Visualization():
    sheet = gc.open('CPU Feature Visualization').worksheet('all features')
    df = pd.DataFrame(sheet.get_all_records())
    
    return df