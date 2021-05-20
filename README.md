# TWSE Captcha Breaker

Recognize string from the captcha on TWSE daily report using Tesseract OCR.

Example for crawling data from TWSE using Selenium

##  Usage

[Follow the steps to install Tesseract](https://tesseract-ocr.github.io/tessdoc/Installation.html)

Download `eng.traineddata` for using legacy engine

Run `pip install -r requirements.txt`

Run `python captcha_to_string.py -h` to see the usage or import the `image_to_string()` function in your own script to use

Example:

```
# inference for one image
python captcha_to_string.py -i ./data/0001.jpg
# inference for all images in a directory
python captcha_to_string.py -d ./data
# specify a output file path
python captcha_to_string.py -d ./data -o ./my_res.txt
```

Run `crawler.py` to crawl the data from TWSE

## Preprocess

- Using "Opening" to filter small noises on image

- Before converting image to binary, apply blurring on image for better filtering noises

- Convert image to binary

- Find connected components and remove relatively small ones

- Apply dilatation on image to make text bolder

> The code and visualization could be found in `captcha_breaker.ipynb`

## Tesseract

- Use `--psm 7` (Treat the image as a single text line.)

- Use `--oem 2`, `--oem 1` then `--oem 0` sequentially if length of output string is not equals to 5

## Crawler

- Request the target URL

- Get captcha image by extract the `src` of image then use `captcha_to_string.py` to recognize the text on the image

- Fill the form and submit with Selenium

- Clean and save the data

## Result

![](./result.png)