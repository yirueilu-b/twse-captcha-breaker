import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup as bs
import cv2
import numpy as np

URL = 'https://bsr.twse.com.tw/bshtm/bsMenu.aspx'


def get_image(url):
    html = requests.get(url).text
    soup = bs(html, 'html.parser')
    placeholders = soup.find_all('img', {'border': "0"})
    image_url = 'https://bsr.twse.com.tw/bshtm/' + placeholders[0]['src']
    resp = requests.get(image_url, stream=True).raw
    image = np.asarray(bytearray(resp.read()), dtype="uint8")
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    return image


if __name__ == '__main__':
    for i in range(25):
        time.sleep(1)
        print(i)
        img = get_image(URL)
        cv2.imwrite('data/' + datetime.strftime(datetime.now(), '%Y%m%d%H%M%S%f') + '.jpg', img)
