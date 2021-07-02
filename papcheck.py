"""
Author: Thomas Simmons <g.thomas.simmons@gmail.com>
6/1/2021
"""

# web scraper stuff
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# file management stuff
import json
import arrow
import pandas as pd
import gspread
from time import sleep


# generates datetime stamp for records
def now():
    return arrow.now().format("MM-DD-YYYY HH:mm:ss")


# generates a dictionary of domain names
# used to filter get_price_data()
# example format for domains.json is {"dhm":"directhomemedical"}
with open("domains.json") as j:
    d = json.load(j)

# loads a new browser instance and tests its connection
def local_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36"
    )
    driver = webdriver.Chrome(
        executable_path="/usr/local/bin/chromedriver", options=options
    )
    driver.implicitly_wait(20)
    driver.get("https://google.com")
    if driver.title == "Google":
        return driver
    else:
        print("Local driver failed to load.")
        driver.close()


# extract product data from each url
def get_price_data(url):
    driver = local_driver()
    driver.get(url)
    sleep(3)

    try:
        # 
        if d.get("shp") in url:
            result = driver.find_element_by_xpath(
                '//span[@class="price"][@itemprop="price"]'
            ).text

        elif (d.get("lqd") in url) or (d.get("csply") in url) or (d.get("eght") in url):
            result = driver.find_element_by_xpath('//span[contains(text(), "$")]').text

        elif d.get("medx") in url:
            result = driver.find_element_by_xpath('//em[contains(text(), "$")]').text

        elif d.get("dhm") in url:
            try:
                h1_tag = driver.find_element_by_xpath("//h1").text
                if "UNAVAILABLE" in h1_tag:
                    result = "0"
            except:
                result = driver.find_element_by_xpath(
                    '//*[@id="js-price-value"]'
                ).get_attribute("data-base-price")

        elif d.get("xchg") in url:
            try:
                result = driver.find_element_by_xpath(
                    '//*[@id="stickyBlockStartPoint"]//span[@class="retail_price on_sale"]'
                ).text
            except:
                print(f"No sale price found for {driver.title}", end="\r")
                try:
                    result = driver.find_element_by_xpath(
                        '//span[@class="retail_price"]'
                    ).get_attribute("content")
                except:
                    print(f"No retail price found for {driver.title}", end="\r")
                    try:
                        result = driver.find_element_by_xpath(
                            '//span[contains(text(), "$")]'
                        ).text
                        print(f"Found retail price for {driver.title}', end='\r'")
                    except:
                        print(f"No price found for {driver.title}", end="\r")
                        result = "0"

        elif (d.get("buym") in url) or (d.get("cntn") in url) or (d.get("lft") in url):
            result = driver.find_elements_by_xpath('//span[contains(text(), "$")]')[
                1
            ].text

        elif d.get("sleep") in url:
            prices = driver.find_elements_by_xpath('//span[contains(text(), "$")]')
            for p in prices:
                if p.text:
                    result = p.text

        elif d.get("cpap") in url:
            prices = driver.find_elements_by_xpath('//span[contains(text(), "$")]')
            for p in prices:
                if ("$" in p.text) and (" " not in p.text):
                    return p.text

        else:
            result = "0"
    except:
        print(
            f"\n\nError on page\nHeader: {driver.find_element_by_xpath('//h1').text}\nURL: {driver.current_url}"
        )
        result = "0"

    driver.close()
    return result


# grabs links from predetermined google sheet
def get_data(worksheet=None, sheet=None):
    if not worksheet:
        worksheet = "Worksheet Name"
    if not sheet:
        sheet = "Worksheet Name"
    gc = gspread.service_account(filename="service_account.json")
    sh = gc.open(worksheet)
    wks = sh.worksheet(sheet)
    data = wks.get_all_values()
    headers = data.pop(0)
    return pd.DataFrame(data, columns=headers)


# saves dictionary containing price data as a csv file
def dict_to_csv(df):
    df["Price"] = df["Link"].apply(lambda x: get_price_data(x))
    df["Price"] = df["Price"].str.replace("[$,]", "", regex=True)
    df["Updated"] = df["Updated"].apply(lambda x: now())
    df.to_csv("data.csv", encoding="utf-8", index=False)


# uploads new csv file data to google sheets
def csv_to_drive():
    gc = gspread.service_account(filename="service_account.json")
    content = open("data.csv", "r").read()
    gc.import_csv(
        "INSERT_GOOGLE_SPREADSHEET_ID", content.encode("utf-8")
    )  # encoding is important here too


def main():
    comp_df = get_data()
    dict_to_csv(comp_df)
    csv_to_drive()


if __name__ == "__main__":
    main()
