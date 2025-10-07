import time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup
import pandas as pd

def init_driver():
    options = Options()
    options.headless = True  # No window
    driver = webdriver.Firefox(options=options)
    return driver

def extract_fbref_schedule_table(url: str) -> pd.DataFrame:
    driver = init_driver()
    driver.get(url)
    time.sleep(5)  

    soup = BeautifulSoup(driver.page_source, "lxml")
    driver.quit()

    # 1️⃣ Search a container whose id corresponding to the pattern of the calendars
    container = soup.find(id="switcher_sched")
    if not container:
        container = soup.find(lambda tag: tag.has_attr("id") and tag["id"].startswith("div_sched_"))

    if not container:
        raise ValueError("Aucun conteneur calendrier trouvé sur la page.")

    # 2️⃣ Extract the first table from the container
    table = container.find("table")
    if not table:
        raise ValueError("Aucun tableau trouvé dans le conteneur calendrier.")

    # 3️⃣ Extract the columns
    header = [th.get_text(strip=True) for th in table.find("thead").find_all("th")]

    # 4️⃣ Extract the rows
    rows = []
    for row in table.find("tbody").find_all("tr"):
        if "class" in row.attrs and "spacer" in row["class"]:
            continue
        cells = [td.get_text(strip=True) for td in row.find_all(["th", "td"])]
        if len(cells) == len(header):
            rows.append(cells)

    return pd.DataFrame(rows, columns=header)