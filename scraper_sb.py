from seleniumbase import SB
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from seleniumbase.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
import time
import json
import os
import sys

URL = "https://www.glassdoor.com/Job/index.htm"
JOBS_FILE = "../jobs.json"
STOP_FILE = "stop_signal.txt"

def parse_jobs(page_source):
    soup = BeautifulSoup(page_source, "html.parser")
    job_cards = soup.find_all("div", class_="jobCard JobCard_jobCardContent__JQ5Rq JobCardWrapper_easyApplyLabelNoWrap__PtpgT")
    jobs = []

    for card in job_cards:
        job_data = {}
        title_tag = card.find("a", class_="JobCard_jobTitle__GLyJ1")
        if title_tag:
            job_data["Title"] = title_tag.getText(strip=True)
            job_data["Link"] = title_tag.get("href")
        location_tag = card.find("div", class_="JobCard_location__Ds1fM")
        if location_tag:
            job_data["Location"] = location_tag.getText(strip=True)
        employer_tag = card.find("div", class_="EmployerProfile_profileContainer__63w3R EmployerProfile_compact__28h9t")
        if employer_tag:
            job_data["Employer"] = employer_tag.getText(strip=True)
        short_description_tag = card.find("div", class_="JobCard_jobDescriptionSnippet__l1tnl")
        if short_description_tag:
            job_data["Short description"] = short_description_tag.getText(strip=True)

        if job_data:
            jobs.append(job_data)

    return jobs

def scraper(url, job_name, location):
    print("[INFO] Starting scraper...")
    all_jobs = []

    with SB(uc=True, headless=True) as sb:
        sb.uc_open_with_reconnect(url, 8)

        try:
            sb.click('//*[@id="onetrust-accept-btn-handler"]')
            print("[INFO] Cookies accepted.")
        except (TimeoutException, NoSuchElementException):
            print("[INFO] No cookie dialog found.")

        sb.wait_for_element_visible('input#searchBar-jobTitle', timeout=15)
        sb.type('input#searchBar-jobTitle', job_name)

        sb.wait_for_element_visible('input#searchBar-location', timeout=15)
        sb.type('input#searchBar-location', location + Keys.ENTER)

        time.sleep(4)

        try:
            if not sb.headless:
                sb.uc_gui_click_captcha()
                print("[INFO] CAPTCHA clicked (if present).")
            else:
                print("[INFO] Skipping CAPTCHA click in headless mode.")
        except (TimeoutException, NoSuchElementException):
            print("[INFO] CAPTCHA not found or not needed. Continuing...")

        try:
            sb.click('//*[@id="left-column"]/div[1]/span/div/h1')
        except (TimeoutException, NoSuchElementException):
            pass

        first_show_more_clicked = False
        page_num = 0

        while True:
            if os.path.exists(STOP_FILE):
                print("[INFO] Stop signal detected. Exiting scraper.")
                break

            sb.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            page_source = sb.get_page_source()
            jobs = parse_jobs(page_source)
            new_jobs = [job for job in jobs if job not in all_jobs]
            all_jobs.extend(new_jobs)

            with open(JOBS_FILE, "w", encoding="utf-8") as f:
                json.dump(all_jobs, f, ensure_ascii=False, indent=2)

            print(f"[INFO] Saved {len(all_jobs)} total jobs (Page {page_num + 1})")

            try:
                sb.wait_for_element_visible('//*[@id="left-column"]/div[2]/div/div/button', timeout=5)
                sb.click('//*[@id="left-column"]/div[2]/div/div/button')
                time.sleep(2.5)

                if not first_show_more_clicked:
                    try:
                        sb.click('button.CloseButton')
                    except (TimeoutException, NoSuchElementException):
                        pass
                    first_show_more_clicked = True

                page_num += 1
            except (TimeoutException, NoSuchElementException):
                print("[INFO] No more 'Show More' button or end of list.")
                break

    print(f"[INFO] Scraping finished. Total jobs saved: {len(all_jobs)}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scraper_sb.py <JOB_NAME> <LOCATION>")
        sys.exit(1)

    job_name = sys.argv[1]
    location = sys.argv[2]
    scraper(URL, job_name, location)