import os
import time
import base64
from glob import glob

import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import cv2
from selenium import webdriver
from datetime import datetime, timedelta

from captcha_to_string import preprocess, image_to_string

BASE_DIR = os.path.abspath('.')
LOCAL_DEALER_DIR = 'stock_local_dealer'
DATA_DIR = os.path.join(BASE_DIR, LOCAL_DEALER_DIR)

COMPANY_LIST_FILENAME = 'company_list.csv'
STOCK_ID_LIST = pd.read_csv(os.path.join(BASE_DIR, COMPANY_LIST_FILENAME)).stock_id.tolist()
# STOCK_ID_LIST = [3481]
CHROME_DRIVER = os.path.join(BASE_DIR, 'chromedriver.exe')

POST_URL = 'https://bsr.twse.com.tw/bshtm/bsMenu.aspx'
DATA_URL = 'https://bsr.twse.com.tw/bshtm/bsContent.aspx?v=t'


def current_time():
    return '[{}]'.format(datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S'))


def get_captcha_text(browser):
    captcha_element = browser.find_element_by_xpath(
        "//*[@id='Panel_bshtm']/table/tbody/tr/td/table/tbody/tr[1]/td/div/div[1]/img")
    img_captcha_base64 = browser.execute_async_script("""
        var ele = arguments[0], callback = arguments[1];
        ele.addEventListener('load', function fn(){
          ele.removeEventListener('load', fn, false);
          var cnv = document.createElement('canvas');
          cnv.width = this.width; cnv.height = this.height;
          cnv.getContext('2d').drawImage(this, 0, 0);
          callback(cnv.toDataURL('image/jpeg').substring(22));
        }, false);
        ele.dispatchEvent(new Event('load'));
        """, captcha_element)
    image_bytes = base64.b64decode(img_captcha_base64)
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, flags=cv2.IMREAD_GRAYSCALE)
    image = preprocess(image)
    text = image_to_string(image)
    return text


def extract_data(soup):
    tables = []
    left_tables = soup.select('td [valign="top"]')
    right_tables = soup.select('td [align="left"]')
    for i in range(len(left_tables)):
        tables.append(pd.read_html(str(left_tables[i]))[0])
    for i in range(len(right_tables)):
        tables.append(pd.read_html(str(right_tables[i]))[0])
    # print("{} stock id {} tables extracted".format(current_time(), stock_id))
    if not tables:
        return pd.DataFrame()
    data = pd.concat(tables).iloc[:-1]
    # print("{} stock id {} tables concat".format(current_time(), stock_id))
    data.columns = ['order', 'bank', 'price', 'buy_shares', 'sell_shares']
    data = data[data['order'] != '序']
    data['order'] = data['order'].astype('int')
    data = data.sort_values(by='order')
    data.reset_index(inplace=True, drop=True)
    return data


def get_data(browser, stock_id):
    data = pd.DataFrame()
    browser.get(POST_URL)
    # time.sleep(1)
    browser.find_element_by_id("TextBox_Stkno").send_keys(stock_id)
    check_text = '驗證碼錯誤!'

    while check_text and check_text != '查無資料':
        text = None
        while not text:
            try:
                text = get_captcha_text(browser)
            except Exception as e:
                print('{} Cannot get captcha image, {}'.format(current_time(), e))
                browser.refresh()
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
    data = extract_data(soup)
    # print("{} stock id {} tables cleaned".format(current_time(), stock_id))
    table_date = browser.find_element_by_id("receive_date").text.split('/')
    table_date = '-'.join(table_date)
    table_stock_id = browser.find_element_by_id("stock_id").text[:4]
    data['date'] = table_date
    data['stock_id'] = table_stock_id
    return data


def run_crawler(save_dir, stock_id_list):
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument("disable-gpu")
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome = webdriver.Chrome(executable_path=CHROME_DRIVER, options=options)

    for i in range(len(stock_id_list)):
        code = stock_id_list[i]
        print("{} Download stock id {} data ({}/{})".format(current_time(), code, i + 1, len(stock_id_list)))
        save_path = os.path.join(save_dir, '{}.csv'.format(code))
        if os.path.exists(save_path):
            continue
        df = get_data(chrome, code)
        if not df.empty:
            print('{} Data save at {}'.format(current_time(), save_path))
            df.to_csv(save_path, index=False, encoding="utf8")
        else:
            print('{} No data found, invalid stock id.'.format(current_time()))
        time.sleep(1)

    chrome.close()
    chrome.quit()


def check_data(save_dir, stock_id_list):
    num_files = len(glob(os.path.join(save_dir, '*')))
    if num_files != len(stock_id_list):
        print("{} Found {}/{} files in {}".format(current_time(), num_files, len(stock_id_list), save_dir))
        return False, stock_id_list
    wrong_data = []
    for i in range(len(stock_id_list)):
        code = stock_id_list[i]
        save_path = os.path.join(save_dir, '{}.csv'.format(code))
        df = pd.read_csv(save_path)
        if df.date[0] != current_date:
            print("{} Date {} mismatch {}".format(current_time(), df.date[0], current_date))
            wrong_data.append(code)
            continue
        if df.stock_id[0] != code:
            print("{} Stock ID {} mismatch {}".format(current_time(), df.stock_id[0], code))
            wrong_data.append(code)
            continue
    return len(wrong_data) == 0, wrong_data


if __name__ == '__main__':
    # Remote data updated after 4 pm. everyday
    if datetime.now().hour >= 16:
        current_date = datetime.strftime(datetime.now(), '%Y-%m-%d')
    else:
        current_date = datetime.strftime(datetime.now() - timedelta(days=1), '%Y-%m-%d')

    # Create save dir if it not exists
    save_directory = os.path.join(DATA_DIR, current_date)
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)
        print("{} Directory".format(current_time()), save_directory, " created")
    else:
        print("{} Directory".format(current_time()), save_directory, " already exists")

    # Initial checking
    is_complete, STOCK_ID_LIST = check_data(save_directory, STOCK_ID_LIST)
    while not is_complete:
        try:
            run_crawler(save_directory, STOCK_ID_LIST)
        except Exception as e:
            print(e)
            continue
        is_complete, STOCK_ID_LIST = check_data(save_directory, STOCK_ID_LIST)
