import os.path
from pathlib import Path
from sys import platform
from typing import Optional, Type, Union

from bs4 import BeautifulSoup
from multiprocessing import Pool, cpu_count

import easyocr
import matplotlib.pyplot as plt
import cv2
import numpy as np
import requests
from PIL import Image
import logging
import argparse
import multiprocessing as mp
from concurrent import futures as cf

import pandas as pd
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService

from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService

from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as GeckoService

from selenium.webdriver.safari.options import Options as SafariOptions
from selenium.webdriver.safari.webdriver import WebDriver as SafariDriver

from selenium.webdriver.remote.webdriver import WebDriver

from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager as EdgeDriverManager
from webdriver_manager.core.utils import ChromeType
from io import BytesIO
from tqdm import tqdm

logging.basicConfig(filename='logfile.txt', level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logging.getLogger('webdriver_manager').setLevel(logging.ERROR)
logger = logging.getLogger(__name__)
BrowserOptions = Union[ChromeOptions, EdgeOptions, FirefoxOptions, SafariOptions]

url=f'https://verify.bmdc.org.bd/'
# browser_name="edge"
# headless=True


def open_selenium_browser(browser_name: str, headless: bool):
    # browser_name = "firefox"
    # headless = False

    options_available = {
        "chrome": ChromeOptions,
        "edge": EdgeOptions,
        "firefox": FirefoxOptions,
        "safari": SafariOptions,
    }
    options = options_available[browser_name]()

    if headless:
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")

    if browser_name == "edge":
        driver = webdriver.Edge(
            service=EdgeService(
                EdgeDriverManager().install()
            ),
            options=options
        )
    elif browser_name == "firefox":
        options.log.level = "fatal"
        driver = webdriver.Firefox(
            service=GeckoService(
                GeckoDriverManager().install()
            ),
            options=options
        )
    else:
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        driver = webdriver.Chrome(
            service=ChromeService(
                ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
            ),
            options=options
        )

    return driver


def open_selenium_browser_v2(browser_name: str, headless: bool, ):
    class Config:
        selenium_web_browser = browser_name
        selenium_headless = headless

    config = Config()
    logging.getLogger("selenium").setLevel(logging.CRITICAL)

    # Options base definition
    options_available: dict[str, Type[BrowserOptions]] = {
        "chrome": ChromeOptions,
        "edge": EdgeOptions,
        "firefox": FirefoxOptions,
        "safari": SafariOptions,
    }
    options: BrowserOptions = options_available[config.selenium_web_browser]()
    # options.add_argument(
    #     "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.5615.49 Safari/537.36"
    # )

    if config.selenium_headless:
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")

    if config.selenium_web_browser == "firefox":

        service = GeckoService(GeckoDriverManager().install(), )
        # service.command_line_args()
        # service.service_args.remove('--verbose')
        # service.service_args.append('--log-path=/dev/null')

        driver = webdriver.Firefox(
            service=service, options=options
        )
    elif config.selenium_web_browser == "edge":

        service = EdgeService(EdgeDriverManager().install(), )
        # service.command_line_args()
        # service.service_args.remove('--verbose')
        # service.service_args.append('--log-path=/dev/null')

        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        driver = webdriver.Edge(
            service=service, options=options
        )
    elif config.selenium_web_browser == "safari":
        # Requires a bit more setup on the users end
        # See https://developer.apple.com/documentation/webkit/testing_with_webdriver_in_safari
        driver = webdriver.Safari(options=options)
    else:
        if platform == "linux" or platform == "linux2":
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--no-sandbox")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])

        chromium_driver_path = Path("/usr/bin/chromedriver")
        service = ChromeService(ChromeDriverManager().install(), )

        # service.command_line_args()
        # service.service_args.remove('--verbose')
        # service.service_args.append('--log-path=/dev/null')

        driver = webdriver.Chrome(
            service=service,
            options=options,
        )
    return driver


# class WebDriverContextManager:
#     def __enter__(self, browser_name: str, headless: bool)
#         print("Entering the block")
#         self.driver = open_selenium_browser(browser_name, headless)
#         return self.driver
#
#     def __exit__(self, exc_type, exc_value, traceback):
#         self.driver.quit()
#         print("Exiting the block")


def go_to_page_with_selenium(driver, url: str="https://verify.bmdc.org.bd/") -> tuple[WebDriver, str]:
    """Scrape text from a website using selenium

    Args:
        url (str): The url of the website to scrape

    Returns:
        Tuple[WebDriver, str]: The webdriver and the text scraped from the website
    """

    driver.get(url)

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    # Get the HTML content directly from the browser's DOM
    page_source = driver.execute_script("return document.body.outerHTML;")

    return driver, page_source


def get_captcha_image(page_source):
    # page_source = requests.get(url=url)
    bs_html = BeautifulSoup(page_source, 'html.parser')
    with open("page_source.txt", "w") as file:
        file.write(page_source)
    captcha_img_url = bs_html.find('div', {"id": "captcha1"}).find("img")["src"]
    # print(captcha_img_url)
    # img = np.array(Image.open(requests.get(captcha_img_url, stream = True).raw))
    img = np.array(Image.open(BytesIO(requests.get(captcha_img_url,stream = True).content)))

    return img[1:29,1:99,:]


def process_image(img):

    img_inv = cv2.bitwise_not(img)
    erode_kernel = np.ones((2, 2), np.uint8)
    dilute_kernel = np.ones((2, 2), np.uint8)
    # kernel[[0,0,2,2],[0,2,0,2]] = 0
    img_inv = cv2.erode(img_inv, erode_kernel, iterations=1)

    # _, img_inv = cv2.threshold(img_inv,128,255,cv2.THRESH_BINARY)
    # img_inv = cv2.dilate(img_inv, dilute_kernel, iterations=2)
    # img_inv = cv2.cvtColor(img_inv , cv2.COLOR_BGR2GRAY)

    x_shift = 20
    y_shift = 20
    ocr_ready_img = np.zeros((img_inv.shape[0] + x_shift, img_inv.shape[1] + y_shift, 3)).astype(np.uint8)

    # x_start = ocr_ready_img.shape[0]//2-img_inv.shape[0]//2
    # y_start = ocr_ready_img.shape[1]//2-img_inv.shape[1]//2
    ocr_ready_img[x_shift:img_inv.shape[0]+x_shift, y_shift:img_inv.shape[1]+y_shift] = img_inv

    return ocr_ready_img


def solve_captcha(img):

    ## OCR Solution (easyOCR)
    reader = easyocr.Reader(['en'],) # Maybe define this at the top, while importing packages
    result= reader.readtext(img, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    captcha_solution = result[0][1]

    ## Pytesseract
    # pytesseract.pytesseract.tesseract_cmd = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    # config = '-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRST0123456789 --psm 6'
    # captcha_solution = pytesseract.image_to_string(img_bin, config=config)

    return captcha_solution


def submit_form_selenium(driver,  doc_id, captcha_solution,):

    input_doc_id = driver.find_element(By.XPATH, "//div[@class='form-group']/input" )
    input_doc_id.send_keys(f"{doc_id}")

    input_captcha = driver.find_element(By.XPATH, "//input[@id='captcha_code']" )
    input_captcha.send_keys(captcha_solution)

    submit_button = driver.find_element(By.XPATH, "//button[@id='submit']" )
    submit_button.click()


    return driver, driver.current_url


def get_doctor_dict_selenium(driver):
    # driver.maximize_window()
    name_xpath = "//div[@class='col-md-8']/h3"
    bmdc_code_xpath = "//div[@class='text-center']/h3"

    registration_year_xpath = "//h5[@class='font-weight-bold mb-0 d-block']"
    dob_bg_lxpath = "//div[@class='form-group row mb-0']/div/h6"
    other_lxpath = "//div[@class='col-md-12']/h6"

    name = driver.find_element(By.XPATH, name_xpath) if driver.find_element(By.XPATH, name_xpath) else None
    bmdc_code = driver.find_element(By.XPATH, bmdc_code_xpath) if driver.find_element(By.XPATH,
                                                                                      bmdc_code_xpath) else None

    registration_details = driver.find_elements(By.XPATH, registration_year_xpath)
    registration_year, registration_validity, _ = registration_details if registration_details else [None, None, None]

    dob_bg = driver.find_elements(By.XPATH, dob_bg_lxpath)
    dob, bg = dob_bg[:2] if dob_bg else [None, None]

    other_details = driver.find_elements(By.XPATH, other_lxpath)

    reg_status = other_details[-1] if other_details else None
    # Scroll to the last element
    driver.execute_script("arguments[0].scrollIntoView();", reg_status)

    if len(other_details) > 2:
        father_name = other_details[0]
        mother_name = other_details[1]
        permanent_add = other_details[-2]
    else:
        father_name = None
        mother_name = None
        permanent_add = None


    doc_entry_dict = {
        "name": name.text if name else None,
        "bmdc_code": bmdc_code.text if bmdc_code else None,
        "registration_year": registration_year.text if registration_year else None,
        "registration_validity": registration_validity.text if registration_validity else None,
        "dob": dob.text if dob else None,
        "bg": bg.text if bg else None,
        "father_name": father_name.text if father_name else None,
        "mother_name": mother_name.text if mother_name else None,
        "permanent_add": permanent_add.text if permanent_add else None,
        "reg_status": reg_status.text if reg_status else None,
    }

    return doc_entry_dict


### These functions need to be organized
def doc_entry_generator(driver, id_start, id_end):
    id = id_start

    pbar = tqdm(total=id_end-id_start+1)
    while id <= id_end:
        driver, page_source = go_to_page_with_selenium(driver)
        captcha_img = get_captcha_image(page_source)
        captcha_img = process_image(captcha_img)
        captcha_solution = solve_captcha(captcha_img)

        driver, _ = submit_form_selenium(driver, id, captcha_solution)
        try:
            doc_entry_dict = get_doctor_dict_selenium(driver)
            yield doc_entry_dict
            id += 1
        except NoSuchElementException:
            pass
        time.sleep(3)
        pbar.update(1)
    pbar.close()


def single_doc_entry(id, browser_name, headless):
    driver = open_selenium_browser(browser_name, headless=headless)

    captcha_incorrect = True
    while captcha_incorrect:
        driver, page_source = go_to_page_with_selenium(driver)
        captcha_img = get_captcha_image(page_source)
        captcha_img = process_image(captcha_img)
        captcha_solution = solve_captcha(captcha_img)
        driver, _ = submit_form_selenium(driver, id, captcha_solution)
        try:
            doc_entry_dict = get_doctor_dict_selenium(driver)
            driver.close()
            return doc_entry_dict
        except NoSuchElementException:
            captcha_incorrect = True
            pass
        time.sleep(3)


def mp_doc_entry(id_start, id_end, browser_name, headless):
    driver = open_selenium_browser(browser_name, headless=headless)
    doc_list = []
    id = id_start
    while id <= id_end:
        driver, page_source = go_to_page_with_selenium(driver)
        captcha_img = get_captcha_image(page_source)
        captcha_img = process_image(captcha_img)
        captcha_solution = solve_captcha(captcha_img)

        driver, _ = submit_form_selenium(driver, id, captcha_solution)
        try:
            doc_entry_dict = get_doctor_dict_selenium(driver)
            doc_list.append(doc_entry_dict)
            id += 1
        except NoSuchElementException:
            pass
        time.sleep(3)
    driver.close()
    return doc_list

## Helpers
def divide_doc_ids(doc_id_start, doc_id_end, n_workers):
    delta = (doc_id_end - doc_id_start) // n_workers
    starts = [doc_id_start + i * (delta + 1) for i in range(n_workers)]
    ends = [
        doc_id_start + i * (delta + 1) + delta if doc_id_start + i * (delta + 1) + delta <= doc_id_end else doc_id_end
        for i in range(n_workers)]
    return starts, ends


## Whole processes
def main_normal(doc_id_start, doc_id_end, browser_name, headless):
    driver = open_selenium_browser(browser_name, headless=headless)
    rows = doc_entry_generator(driver, doc_id_start, doc_id_end)
    df = pd.DataFrame(rows, columns=["name", "bmdc_code", "registration_year", "registration_validity", "dob",
                               "father_name", "mother_name", "permanent_add", "reg_status"])
    driver.quit()
    return df


def main_multithread(doc_id_start, doc_id_end, browser_name, headless, workers=4):
    # # Main Function start
    # print("Starting Browser. ------------------")
    # driver = open_selenium_browser(browser_name, headless=headless)
    # print("Browser Opened. Now scraping. ------------------")

    # Divide to smaller sub-tasks: Divide the doc-ids into `n_workers` parts
    starts, ends = divide_doc_ids(doc_id_start, doc_id_end, n_workers=workers)
    print(f"starts: {starts}")
    print(f"ends: {ends}")

    df = pd.DataFrame(columns=["name", "bmdc_code", "registration_year", "registration_validity", "dob",
                               "father_name", "mother_name", "permanent_add", "reg_status"])

    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        fs = [pool.submit(mp_doc_entry, start_id, end_id, browser_name, headless) for start_id, end_id in zip(starts, ends)]
        total_tasks = doc_id_end - doc_id_start + 1

        for f in tqdm(cf.as_completed(fs), total=total_tasks, bar_format='{l_bar}{bar:20}{r_bar}{bar:-20b} {percentage:3.0f}%'):
            data_generator = f.result()
            for row in data_generator:
                df = df._append(row, ignore_index=True)

    return df


def main_multiprocess(doc_id_start, doc_id_end, browser_name, headless, workers=4):

    df = pd.DataFrame(columns=["name", "bmdc_code", "registration_year", "registration_validity", "dob",
                               "father_name", "mother_name", "permanent_add", "reg_status"])

    with cf.ProcessPoolExecutor(max_workers=workers) as executor:
        total_tasks = doc_id_end - doc_id_start + 1
        fs = [executor.submit(single_doc_entry, i, browser_name, headless) for i in range(doc_id_start, doc_id_end+1)]
        for f in tqdm(cf.as_completed(fs), total=total_tasks, bar_format='{l_bar}{bar:20}{r_bar}{bar:-20b} {percentage:3.0f}%'):
            df = df._append(f.result(), ignore_index=True)

    return df



def main_mp2(doc_id_start, doc_id_end, browser_name, headless, workers=4):
    # Divide to smaller sub-tasks: Divide the doc-ids into `n_workers` parts
    starts, ends = divide_doc_ids(doc_id_start, doc_id_end, n_workers=workers)
    print(f"starts: {starts}")
    print(f"ends: {ends}")

    df = pd.DataFrame(columns=["name", "bmdc_code", "registration_year", "registration_validity", "dob",
                               "father_name", "mother_name", "permanent_add", "reg_status"])

    with cf.ProcessPoolExecutor(max_workers=workers) as executor:
        fs = [executor.submit(mp_doc_entry, start_id, end_id, browser_name, headless) for start_id, end_id in zip(starts, ends)]

        for f in cf.as_completed(fs):
            df = df._append(f.result(), ignore_index=True)
            # data_generator = f.result()
            # for row in data_generator:
            #     df = df._append(row, ignore_index=True)

    return df


if __name__=='__main__':
    parser = argparse.ArgumentParser(description="Give the range of doctor id to scrape")
    parser.add_argument('-s','--start', type=int, help='website', default=11)
    parser.add_argument('-e', '--end', type=int, help='website', default=15)
    parser.add_argument('-b', '--browser', type=str, help='Browser name', default="chrome")
    parser.add_argument('-t', '--headless', action='store_false',  help='Browser type', default=True)
    parser.add_argument('-d', '--delta', type=int, help='Browser type', default=30)
    args = parser.parse_args()

    # Start Time
    star_time = time.time()

    doc_id_start = args.start
    doc_id_end = args.end
    browser_name = args.browser
    headless = args.headless

    num_processes = mp.cpu_count()
    workers = num_processes//2
    print(f"Number of parallel processes: {workers}")
    if not os.path.isdir("./scraped_data"):
        os.mkdir("./scraped_data")

    ## Main Function start
    total_tasks = doc_id_end - doc_id_start + 1
    delta = args.delta
    if total_tasks <= delta:
        df = main_multiprocess(doc_id_start, doc_id_end, browser_name, headless, workers=workers)
        df.to_csv(f"./scraped_data/doctor_{doc_id_start}_{doc_id_end}.csv", index=False)
    else:
        id_start = doc_id_start
        id_end = doc_id_start + delta
        while id_start <= doc_id_end:
            df = main_multiprocess(id_start, id_end, browser_name, headless, workers=workers)
            df.to_csv(f"./scraped_data/doctor_{id_start}_{id_end}.csv", index=False)
            print(id_start, id_end)
            id_start = id_end + 1
            id_end = id_end + delta if id_end + delta <= doc_id_end else doc_id_end



    # print("Starting Browser. ------------------")
    # driver = open_selenium_browser(browser_name, headless=headless)
    # print("Browser Opened. Now scraping. ------------------")

    # df = main_multithread(doc_id_start, doc_id_end, browser_name, headless, workers=workers)
    # df = main_normal(doc_id_start, doc_id_end,browser_name, headless)
    # df = main_multiprocess(doc_id_start, doc_id_end, browser_name, headless, workers=workers)
    # df = main_mp2(doc_id_start, doc_id_end, browser_name, headless, workers=workers)



    elapsed_time = time.time() - star_time
    print(f"Total Time taken: {elapsed_time//60} min, {elapsed_time - 60 * (elapsed_time//60)} sec.")

