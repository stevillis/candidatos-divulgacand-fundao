import logging
import os
import random
import time

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("scraper.log"), logging.StreamHandler()],
)

MT_CANDIDATES_URL = (
    "https://divulgacandcontas.tse.jus.br/divulga/#/candidato/CENTROOESTE/MT/2045202024"
)


def get_chrome_driver():
    service = Service()
    options = webdriver.ChromeOptions()

    # adding argument to disable the AutomationControlled flag
    options.add_argument("--disable-blink-features=AutomationControlled")

    # exclude the collection of enable-automation switches
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    # turn-off userAutomationExtension
    options.add_experimental_option("useAutomationExtension", False)

    return webdriver.Chrome(service=service, options=options)


def antibot(driver):
    # TODO: improve antitob detection
    scroll_y = random.randint(0, 700)
    driver.execute_script(f"window.scrollTo(0, {scroll_y})")
    time.sleep(random.randint(1, 5))


driver = get_chrome_driver()

# changing the property of the navigator value for webdriver to undefined
driver.execute_script(
    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
)

logging.info("Step 1: Access the website")
driver.get(MT_CANDIDATES_URL)
time.sleep(3)  # Wait for the page to load

logging.info("Step 2: Select the municipality")
select_municipio = Select(driver.find_element(By.ID, "codigoMunicipio"))
select_municipio.select_by_value("90670")  # Cuiabá
time.sleep(1)

logging.info("Step 3: Select the cargo (position)")
select_cargo = Select(driver.find_element(By.ID, "cargo"))
select_cargo.select_by_value("13")  # Councilor
time.sleep(1)

logging.info("Step 4: Click on the button to proceed")
driver.find_element(
    By.XPATH, "//*[@id='basicInformationSection']/div/button[1]"
).click()
time.sleep(1)

logging.info("Step 5: Get total candidates")
total_candidates_element = driver.find_element(
    By.XPATH, '//*[@id="basicInformationSection"]/div[1]/div[1]/div[1]'
)

total_candidates_text = total_candidates_element.text.strip()
total_candidates = int(total_candidates_text.split(":")[-1].strip())
logging.info("Total candidates: {total_candidates}")

logging.info("Step 6: Loop over candidates")
index = 0
while index < total_candidates:
    candidate_items = driver.find_elements(
        By.XPATH, "//div[contains(@class, 'list-group-item')]"
    )

    if index >= len(candidate_items):
        logging.info("No more candidates found.")
        break

    name = (
        candidate_items[index]
        .find_element(By.XPATH, ".//span[@class='fw-bold']")
        .text.strip()
    )

    logging.info("Getting data of candidate %d: %s", index + 1, name)

    federation = (
        candidate_items[index]
        .find_element(By.XPATH, ".//span[@class='fw-bold'][2]")
        .text.strip()
    )

    status = (
        candidate_items[index]
        .find_element(By.XPATH, ".//div[contains(@class, 'badge bg-info')]")
        .text.strip()
    )

    number = candidate_items[index].find_element(By.XPATH, ".//small").text.strip()

    antibot(driver)
    candidate_items[index].click()
    time.sleep(10)

    logging.info("Getting receipts of candidate %d: %s", index + 1, name)
    antibot(driver)
    driver.get(driver.current_url + "/prestacao/receitas")
    time.sleep(10)

    logging.info("Downloading data of candidate %d: %s", index + 1, name)
    antibot(driver)
    driver.find_element(By.CLASS_NAME, "link-exportar").click()

    logging.info("Opening arquivo.xlsx of candidate %d: %s", index + 1, name)
    arquivo_path = "C:\\Users\\stevi\\Downloads\\arquivo.xlsx"
    if os.path.exists(arquivo_path):
        df_exported = pd.read_excel(arquivo_path)

        # Create a DataFrame for candidate details with additional columns for each candidate's info
        candidate_info = {
            "name": name,
            "federation": federation,
            "status": status,
            "number": number,
        }

        df_candidate_info = pd.DataFrame(
            [candidate_info] * len(df_exported)
        )  # Repeat candidate info for each row in df_exported

        logging.info("Appending data of candidate %d: %s", index + 1, name)
        output_file_path = "candidaturas.xlsx"
        if os.path.exists(output_file_path):
            with pd.ExcelWriter(
                output_file_path, mode="a", engine="openpyxl", if_sheet_exists="overlay"
            ) as writer:
                combined_df = pd.concat(
                    [
                        df_candidate_info.reset_index(drop=True),
                        df_exported.reset_index(drop=True),
                    ],
                    axis=1,
                )
                combined_df.to_excel(
                    writer, sheet_name="Sheet1", index=False, header=False
                )
        else:
            combined_df = pd.concat(
                [
                    df_candidate_info.reset_index(drop=True),
                    df_exported.reset_index(drop=True),
                ],
                axis=1,
            )
            combined_df.to_excel(output_file_path, index=False)

        os.remove(arquivo_path)

    antibot(driver)
    driver.get(MT_CANDIDATES_URL)
    time.sleep(10)

    index += 1

    logging.info("%s Moving to next candidate %s", "-" * 30, "-" * 30)

driver.quit()
