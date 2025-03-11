from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait

import time


def extract_href(input_file, output_file, output_bib_file, chrome_driver):
    """
    优化后的文献引用信息抓取函数

    Parameters:
    input_file (str): 文献标题列表文件路径
    output_file (str): 链接输出文件路径
    output_bib_file (str): BibTeX内容输出文件路径
    chrome_driver (str): ChromeDriver路径
    """
    # 初始化浏览器设置
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    # 设置代理为 localhost:7890
    proxy = "socks5://127.0.0.1:7890"
    options.add_argument(f'--proxy-server={proxy}')
    # 设置 ChromeDriver 的路径
    service = Service(chrome_driver.replace('\\', '/'))

    with open(input_file, 'r', encoding='utf-8') as scholars, \
            open(output_file, 'w', encoding='utf-8') as file_out, \
            open(output_bib_file, 'w', encoding='utf-8') as file_bib_out:
        browser = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(browser, 15)
        processed_links = set()
        failed_records = []

        browser.get("https://httpbin.org/ip")
        print(browser.page_source)

        try:
            browser.get("https://scholar.google.com")

            for line in scholars:
                try:
                    title = line.strip().split('\t')[-1]
                    print(f"Processing: {title}")

                    # 执行搜索
                    search_box = wait.until(
                        EC.presence_of_element_located((By.NAME, "q"))
                    )
                    search_box.clear()
                    search_box.send_keys(title)

                    search_button = wait.until(
                        EC.element_to_be_clickable((By.NAME, "btnG"))
                    )
                    search_button.click()

                    # 获取引用按钮
                    cite_btn = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "a.gs_or_cit"))
                    )
                    cite_btn.click()

                    # 获取BibTeX链接
                    bib_link = wait.until(
                        EC.presence_of_element_located((By.LINK_TEXT, "BibTeX"))
                    ).get_attribute('href')

                    # 处理重复链接
                    if bib_link not in processed_links:
                        processed_links.add(bib_link)
                        file_out.write(f"{bib_link}\n")

                        # 获取BibTeX内容
                        browser.get(bib_link)
                        bib_content = wait.until(
                            EC.presence_of_element_located((By.TAG_NAME, "pre"))
                        ).text
                        file_bib_out.write(f"{bib_content}\n\n")

                except (TimeoutException, NoSuchElementException) as e:
                    print(f"Error processing {title}: {str(e)}")
                    failed_records.append(title)
                    continue

        finally:
            browser.quit()
            print(f"Process completed. Failed records: {failed_records}")


if __name__ == "__main__":
    input_file = 'references.txt'
    output_file = 'scholar_link.txt'
    output_bib_file = 'scholar_bib.bib'
    chrome_driver = r'D:\download\chromedriver-win64\chromedriver.exe'
    extract_href(input_file, output_file, output_bib_file, chrome_driver)
