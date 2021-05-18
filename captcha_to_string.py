import os
import glob
import argparse

import cv2
import pytesseract
import numpy as np


def preprocess(image_gray):
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    image_opening = cv2.morphologyEx(image_gray, cv2.MORPH_OPEN, kernel, iterations=1)
    image_blur = cv2.GaussianBlur(image_opening, (5, 5), 0)
    _, image_thresh = cv2.threshold(image_blur, 180, 255, cv2.THRESH_BINARY)

    num_components, components, stats, _ = cv2.connectedComponentsWithStats(image_thresh,
                                                                            None, None, None, 4, cv2.CV_32S)
    sizes = stats[:, -1]
    image_connected = np.zeros(components.shape, np.uint8)
    for i in range(1, num_components):
        if sizes[i] >= 64:
            image_connected[components == i] = 255

    kernel = np.ones((2, 2), np.uint8)
    image_dilation = cv2.dilate(image_connected, kernel, iterations=1)
    return image_dilation


def image_to_string(image):
    custom_config = r'--oem 2 --psm 7'
    s = pytesseract.image_to_string(image, config=custom_config)
    punctuations = " !()-[]{};:\'\"\\,<>./?@#$%^+^&*_~‘"
    for punctuation in punctuations:
        s = s.replace(punctuation, '')
    s = s.split('\n')[0].upper()
    if len(s) != 5:
        custom_config = r'--oem 1 --psm 7'
        s = pytesseract.image_to_string(image, config=custom_config)
        punctuations = " !()-[]{};:\'\"\\,<>./?@#$%^&*_~‘"
        for punctuation in punctuations:
            s = s.replace(punctuation, '')
        s = s.split('\n')[0].upper()
    if len(s) != 5:
        custom_config = r'--oem 0 --psm 7'
        s = pytesseract.image_to_string(image, config=custom_config)
        punctuations = " !()-[]{};:\'\"\\,<>./?@#$%^&*_~‘"
        for punctuation in punctuations:
            s = s.replace(punctuation, '')
        s = s.split('\n')[0].upper()
    return s


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--image_path",
                        help="The path of captcha image",
                        type=str)
    parser.add_argument("-d", "--image_dir",
                        help="The path of captcha images directory, if assigned, -i will be ignored",
                        type=str)
    parser.add_argument("-o", "--output_path",
                        help="The path of result text file, only works when -d is assigned",
                        type=str,
                        default=os.path.join('.', 'result.txt'))

    args = parser.parse_args()

    if args.image_dir:
        result = []
        image_paths = glob.glob(os.path.join(args.image_dir, '*.jpg'))
        for image_path in image_paths:
            input_image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            input_image = preprocess(input_image)
            ans = image_to_string(input_image)
            result.append((image_path, ans))
            print(image_path, ans)
        if args.output_path:
            with open(args.output_path, 'w', encoding='utf-8') as f:
                for line in result:
                    f.write('{},{}\n'.format(line[0], line[1]))
    else:
        image_path = args.image_path
        input_image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        input_image = preprocess(input_image)
        ans = image_to_string(input_image)
        print(image_path, ans)
