import time
import pymysql
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
import platform
import os
import config as config

filters = "filters.json"

CHROMEDRIVER_PATH = "chromedriver.exe"  # os.path.join(


#     os.path.dirname(__file__),
#     f"../chromedriver/{platform.system().lower()}/chromedriver"
# )


class DBHandler:
    DB_CONN = None

    def __init__(self):

        self.DB_HOST = config.DB_CONFIG["host"]
        self.DB_USER = config.DB_CONFIG["user"]
        self.DB_PW = config.DB_CONFIG["pw"]
        self.DB_NAME = config.DB_CONFIG["name"]

    def openConnection(self):

        self.DB_CONN = pymysql.connect(self.DB_HOST, self.DB_USER, self.DB_PW, self.DB_NAME, autocommit=True)

    def closeConnection(self):
        self.DB_CONN.close()

    def executeSQL(self, sql, args=None):
        self.openConnection()
        with self.DB_CONN.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, args)
            queryResult = cursor
        self.closeConnection()
        return queryResult

    def check_if_postingid_exists(self, postingid):
        sql = f"SELECT COUNT(*) FROM cars WHERE posting_id='{postingid}'"
        res = self.executeSQL(sql).fetchone()['COUNT(*)']
        if res == 0:
            return False
        else:
            return True

    def is_int(self, value):
        try:
            int(value)
            return True
        except Exception:
            return False

    def insert_new_car(self, data):
        now = datetime.now()
        source = "eBay"
        timestamp = None
        ad_title = data['Title']
        price = data['Price'] if 'Price' in data.keys() else 0
        if self.is_int(price):
            price = int(data['Price'].replace(',', ''))
        else:
            price = 0
        size = data['size'] if 'size' in data.keys() else None
        type = data['Body Type'] if 'Body Type' in data.keys() else None
        vin = data[
            'VIN (Vehicle Identification Number)'] if 'VIN (Vehicle Identification Number)' in data.keys() else None
        drive = data['Drive Type'] if 'Drive Type' in data.keys() else None
        fuel = data['Fuel Type'] if 'Fuel Type' in data.keys() else None
        image = data['Image'] if 'Image' in data.keys() else None
        odometer = data['Mileage'] if 'Mileage' in data.keys() else 0
        condition = data['Condition'] if 'Condition' in data.keys() else None
        paintcolor = data['Exterior Color'] if 'Exterior Color' in data.keys() else None
        year = data['Year'] if 'Year' in data.keys() else 0
        transmission = data['Transmission'] if 'Transmission' in data.keys() else None
        make = data['Make'] if 'Make' in data.keys() else None
        model = data['Model'] if 'Model' in data.keys() else None
        cylinders = data['Number of Cylinders'] if 'Number of Cylinders' in data.keys() else None
        postingid = data['eBay item Number'] if 'eBay item Number' in data.keys() else None
        url = pymysql.escape_string(data['URL'])

        sql = f"""INSERT INTO cars(created_at, source, offer_timestamp, type, price,
                    make, vin, car_condition, paint_color, image, size, odometer, year, ad_title,
                    posting_id, transmission, model, fuel, drive, url, cylinders) VALUES('{now}','{source}','{timestamp}'
                    ,'{type}','{price}','{make}','{vin}',
                    '{condition}','{paintcolor}','{image}','{size}',
                    '{odometer}','{year}','{ad_title}','{postingid}','{transmission}'
                    ,'{model}','{fuel}','{drive}' ,'{url}','{cylinders}');"""

        if not self.check_if_postingid_exists(postingid):
            self.executeSQL(sql)
            print(postingid + " inserted!")
        else:
            print(postingid + ' already in db')
        return

    def get_all_data(self):
        sql = "SELECT * FROM cars"
        return self.executeSQL(sql).fetchall()


class Obj:
    def __init__(self, db, ebay, value):
        self.db = db
        self.ebay = ebay
        self.value = value


def run(url):
    print("Working on " + url)
    content = BeautifulSoup(requests.get(url).text, 'lxml')
    dictionary = {"Price": content.find('span', {'itemprop': 'price'}).text.replace("US $", '').split('.')[0],
                  "Image": content.find('img', {'id': 'icImg'})['src'],
                  "Title": pymysql.escape_string(content.find('h1', {'id': 'itemTitle'}).text.replace("Details about  \xa0", '')),
                  "eBay item Number": content.find('div', {'id': 'descItemNumber'}).text, "URL": url}
    templist = []
    t = content.find('div', {'class': 'itemAttr'}).find_all('table')
    table = t[len(t) - 1]
    for tr in table.find_all('tr'):
        for td in tr.find_all('td'):
            templist.append(td.text.strip().replace(':', ''))
    for i in range(0, len(templist) - 1, 2):
        dictionary[templist[i]] = templist[i + 1]
    print("Adding data to db: ")
    # handler = DBHandler()
    # handler.insert_new_car(data=dictionary)
    print(dictionary)


try:
    with open(filters) as file:
        data = json.load(file)
except:
    data = {
        "search": "Ford",
        "zipcode": "98006",
        "yearsOlderThan": "1999",
        "withinMiles": "100"
    }
print("Filters:")
print(data)
options = webdriver.ChromeOptions()
# print("Connecting existing Chrome for debugging...")
# options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
print("Turning off images to save bandwidth")
options.add_argument("--blink-settings=imagesEnabled=false")
print("Making chrome headless")
options.add_argument("--headless")
options.add_argument("--window-size=1920x1080")
print("Launching Chrome...")
driver = webdriver.Chrome(CHROMEDRIVER_PATH, options=options)
# driver.maximize_window()
driver.get("https://www.ebay.com/")
time.sleep(1)
print("Applying the filters")
driver.find_element_by_id("gh-as-a").click()
lh_located_btn = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.ID, "LH_Located"))
)
lh_located_btn.click()
driver.find_element_by_xpath("//select[@name='_sadis']/option[text()='" + data["withinMiles"] + "']").click()
zipcode_input = driver.find_element_by_id("_stpos")
zipcode_input.clear()
zipcode_input.send_keys(data["zipcode"])
# search_btn = WebDriverWait(driver, 10).until(
#     EC.presence_of_element_located((By.ID, "searchBtnLowerLnk"))
# )
#
# search_btn.click()
driver.find_element_by_id("searchBtnLowerLnk").click()
time.sleep(2)
driver.find_element_by_id("gh-ac").send_keys(data["search"])
driver.find_element_by_id("gh-btn").click()
time.sleep(1)
driver.find_element_by_xpath("//button[text()='More filters...']").click()
time.sleep(3)
modelyear = driver.find_element_by_xpath('//*[@id="c3-subPanel"]')
years = modelyear.text.split("\n")
years.sort()
years = [x for x in years if "(" not in x][:-1]
years.sort(reverse=True)
for year in years:
    if int(year) >= int(data["yearsOlderThan"]):
        modelyear.find_element_by_xpath(".//span[text()='" + year + "']").find_element_by_xpath("../..").click()
driver.find_element_by_id("c3-footerId").find_element_by_tag_name("button").click()
time.sleep(3)
driver.find_element_by_xpath("//label[text()='Within']").click()
driver.find_element_by_css_selector(
    'div.x-refine__text-list__container.x-refine__block-button--use-arrow'
).find_element_by_tag_name("button").click()
print("Done with filters, now working on the results!")
try:
    ul = driver.find_element_by_css_selector(".srp-results.srp-list.clearfix")
except:
    ul = driver.find_element_by_id("ListViewInner")
pagecount = len(driver.find_elements_by_class_name("pagination__item"))
print("Total pages: " + str(pagecount))
print("Listings on current page: " + str(len(ul.find_elements_by_css_selector(".s-item.s-item--watch-at-corner"))))
for li in ul.find_elements_by_css_selector(".s-item.s-item--watch-at-corner"):
    run(li.find_element_by_class_name("s-item__link").get_attribute('href'))
for i in range(1, pagecount - 1):
    time.sleep(2)
    for li in ul.find_elements_by_css_selector(".s-item.s-item--watch-at-corner"):
        run(li.find_element_by_class_name("s-item__link").get_attribute('href'))
    print("Page " + str(i) + " ended. Now moving to page " + str(i + 1))
    driver.find_element_by_class_name("pagination__next").click()

driver.close()
