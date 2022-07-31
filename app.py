import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe
import altair as alt
import streamlit as st
import datetime
import re
import os
from dotenv import load_dotenv
load_dotenv()

def get_worksheet():
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    credentials = Credentials.from_service_account_file(
        'service_account.json',
        scopes=scopes
    )

    gc = gspread.authorize(credentials)

    SP_SHEET_KEY = os.getenv('SP_SHEET_KEY')
    sh = gc.open_by_key(SP_SHEET_KEY)
    SP_SHEET = 'gas_data'
    worksheet = sh.worksheet(SP_SHEET)

    return worksheet

def get_df(worksheet):
    data = worksheet.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])
    
    return df

def update_df(df,new_data):

    new_df = pd.DataFrame(new_data)

    df_updated = pd.concat([df, new_df], ignore_index=True)
    return df_updated

def set_new_data(df,date,gas_text,total_mileage_text):
    gas = int(gas_text)
    total_mileage = int(total_mileage_text)
    df_tail = df.tail(1)
    last_total_mileage = int(df_tail.iat[0, 2])
    mileage = total_mileage - last_total_mileage
    gas_mileage = round(mileage / gas, 1)
    new_data = {
        'date': [date],
        'gas': [gas],
        'total_mileage': [total_mileage],
        'mileage': [mileage],
        'gas_mileage': [gas_mileage]
    }
    return new_data

def get_chart(df):
    df = df.astype({
        'gas_mileage': float
    })

    ymax = df['gas_mileage'].max()+10
    ymin = df['gas_mileage'].min()-10
    chart = alt.Chart(df).mark_line().encode(
        x='date:T',
        y=alt.Y('gas_mileage:Q', scale=alt.Scale(domain=[ymin, ymax]))
    )
    return chart

def error_check(date, gas_text, total_mileage_text):
    count = 0
    pattern_date = "[0-9]{4}/[0-9]{1,2}/[0-9]{1,2}$"
    pattern_int = "[0-9]+$"
    pattern_float = "[0-9]+\.[0-9]+$"
    date_res = re.match(pattern_date, date)
    if date_res == None:
        st.write('<span style="color:red;background:pink">日付を"yyyy/mm/dd"の形式で入力してください。</span>',
              unsafe_allow_html=True)
    else:
        count = count + 1

    res_gas_int = re.match(pattern_int, gas_text)
    res_gas_float = re.match(pattern_float, gas_text)
    if res_gas_int == None and res_gas_float == None:
        st.write('<span style="color:red;background:pink">給油量を半角数字で入力してください。</span>',
              unsafe_allow_html=True)
    else:
        count = count + 1

    res_total_mileage = re.match(pattern_int, total_mileage_text)
    if res_total_mileage == None:
        st.write('<span style="color:red;background:pink">総走行距離を半角数字で入力してください。</span>',
              unsafe_allow_html=True)
    else:
        count = count + 1
    return count

st.title('ガソリン燃費計算')
st.write('## 給油登録')
st.write('### 日付')

today = datetime.date.today().strftime('%Y/%m/%d')

date = st.text_input('日付を入力してください。', f'{today}')
st.write('### 給油量')
gas_text = st.text_input('給油量を入力してください。単位:L')
st.write('### 総走行距離')
total_mileage_text = st.text_input('給油時の総走行距離を入力してください。単位:km')

try:
    if st.button('登録'):
        # 登録後に実行

        # エラー処理
        count = error_check(date, gas_text, total_mileage_text)
        if count == 3:
            worksheet = get_worksheet()
            df = get_df(worksheet)

            # 新規データ追加
            new_data = set_new_data(df,date,gas_text,total_mileage_text)
            df_updated = update_df(df, new_data)
            set_with_dataframe(worksheet, df_updated, row=1, col=1)

            # 追加したデータを読み込む
            worksheet = get_worksheet()
            df = get_df(worksheet)
            df2 = df.set_index('date').tail()
            
            st.write('------')

            gas_mileage = new_data['gas_mileage'][0]
            st.markdown(f'### 今回の燃費：{gas_mileage}')
            st.write('最近の給油状況', df2)

            chart = get_chart(df)
            st.write('燃費')
            st.altair_chart(chart, use_container_width=True)
except:
    st.error('エラーが起きています。')
