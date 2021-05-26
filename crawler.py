import os
import time

import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import cv2
from selenium import webdriver
from datetime import datetime

from captcha_to_string import preprocess, image_to_string

BASE_DIR = os.path.abspath('.')
LOCAL_DEALER_DIR = 'stock_local_dealer'
DATA_DIR = os.path.join(BASE_DIR, LOCAL_DEALER_DIR)

COMPANY_LIST_FILENAME = 'company_list.csv'
# STOCK_ID_LIST = pd.read_csv(os.path.join(BASE_DIR, COMPANY_LIST_FILENAME)).stock_id.tolist()
STOCK_ID_LIST = [8039]
CHROME_DRIVER = os.path.join(BASE_DIR, 'chromedriver.exe')

POST_URL = 'https://bsr.twse.com.tw/bshtm/bsMenu.aspx'
DATA_URL = 'https://bsr.twse.com.tw/bshtm/bsContent.aspx?v=t'


def current_time():
    return '[{}]'.format(datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S'))


def get_captcha_text(img_url):
    response = requests.get(img_url, stream=True).raw
    image = np.asarray(bytearray(response.read()), dtype="uint8")
    image = cv2.imdecode(image, cv2.IMREAD_GRAYSCALE)
    image = preprocess(image)
    text = image_to_string(image)
    return text


def get_data(browser, stock_id):
    data = pd.DataFrame()
    browser.get(POST_URL)
    time.sleep(1)
    browser.find_element_by_id("TextBox_Stkno").send_keys(stock_id)
    check_text = '驗證碼錯誤!'
    while check_text and check_text != '查無資料':
        image_url = browser.find_elements_by_tag_name('img')[1].get_attribute("src")
        text = None
        while not text:
            try:
                text = get_captcha_text(image_url)
                time.sleep(2)
            except Exception as e:
                print('{} Cannot get captcha image, {}'.format(current_time(), e))
                browser.refresh()
                time.sleep(2)
                browser.find_element_by_id("TextBox_Stkno").send_keys(stock_id)

        browser.find_element_by_name("CaptchaControl1").send_keys(text)
        browser.find_element_by_id("btnOK").click()
        check_text = browser.find_element_by_id("Label_ErrorMsg").text
        if not check_text:
            print("{} Submit stock id {} and validation code {}: {}".format(current_time(), stock_id, text, '查詢成功'))
        else:
            print("{} Submit stock id {} and validation code {}: {}".format(current_time(), stock_id, text, check_text))

    if check_text == "查無資料":
        return data

    browser.get(DATA_URL)
    # print("{} stock id {} html page received".format(current_time(), stock_id))
    html = browser.page_source
    soup = BeautifulSoup(html, 'html.parser')
    # print("{} stock id {} bs4 parsing html done".format(current_time(), stock_id))
    tables = []
    left_tables = soup.select('td [valign="top"]')
    right_tables = soup.select('td [align="left"]')
    for i in range(len(left_tables)):
        tables.append(pd.read_html(str(left_tables[i]))[0])
    for i in range(len(right_tables)):
        tables.append(pd.read_html(str(right_tables[i]))[0])
    # print("{} stock id {} tables extracted".format(current_time(), stock_id))
    data = pd.concat(tables).iloc[:-1]
    # print("{} stock id {} tables concat".format(current_time(), stock_id))
    data.columns = ['order', 'bank', 'price', 'buy_shares', 'sell_shares']
    data = data[data['order'] != '序']
    data['order'] = data['order'].astype('int')
    data = data.sort_values(by='order')
    data.reset_index(inplace=True, drop=True)
    # print("{} stock id {} tables cleaned".format(current_time(), stock_id))
    return data


if __name__ == '__main__':
    current_date = datetime.strftime(datetime.now(), '%Y%m%d')
    dir_path = os.path.join(DATA_DIR, current_date)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print("{} Directory".format(current_time()), dir_path, " Created")
    else:
        print("{} Directory".format(current_time()), dir_path, " already exists...")

    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument("disable-gpu")
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome = webdriver.Chrome(executable_path=CHROME_DRIVER, chrome_options=options)

    for i in range(len(STOCK_ID_LIST)):
        code = STOCK_ID_LIST[i]
        print("{} Download stock id {} data ({}/{})".format(current_time(), code, i + 1, len(STOCK_ID_LIST)))
        save_path = os.path.join(dir_path, '{}.csv'.format(code))
        df = get_data(chrome, code)
        if not df.empty:
            print('{} Data save at {}'.format(current_time(), save_path))
            df.to_csv(save_path, index=False, encoding="utf8")
        else:
            print('{} No data found, invalid stock id.'.format(current_time()))
        time.sleep(2)

    chrome.quit()
    chrome.close()
