from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import time
import json
import random
import logging
from webdriver_manager.chrome import ChromeDriverManager
from anticaptchaofficial.recaptchav2proxyless import *
from googlesearch import search

logging.basicConfig(level=logging.INFO)


class JobApplicationBot:
    def __init__(self, driver_path, cookies_file):
        self.driver_path = driver_path
        self.cookies_file = cookies_file
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.driver = None

    def _initialize_driver(self):
        service = Service(self.driver_path)
        self.driver = webdriver.Chrome(service=service, options=self.chrome_options)

    def _quit_driver(self):
        if self.driver:
            self.driver.quit()

    def search_jobs_on_google(self, query):
        self._initialize_driver()
        try:
            job_urls = []
            for url in search(query, num=10, stop=10, pause=2, tbs='qdr:d'):
                if 'join.com/companies' in url:
                    job_urls.append(url)
            return job_urls
        finally:
            self._quit_driver()

    def solve_captcha(self, site_key, url):
        solver = recaptchaV2Proxyless()
        solver.set_verbose(1)
        solver.set_key("YOUR_ANTI_CAPTCHA_API_KEY")
        solver.set_website_url(url)
        solver.set_website_key(site_key)
        g_response = solver.solve_and_return_solution()
        if g_response != 0:
            logging.info("Captcha solved: " + g_response)
            return g_response
        else:
            logging.error("Captcha solving failed: " + solver.error_code)
            return None

    def login_and_apply_to_jobs(self, job_urls):
        self._initialize_driver()
        try:
            with open(self.cookies_file, 'r') as file:
                cookies = json.load(file)
            for job_url in job_urls:
                self.driver.get(job_url)
                for cookie in cookies:
                    if "sameSite" in cookie and cookie["sameSite"] not in ["Strict", "Lax", "None"]:
                        cookie["sameSite"] = "Lax"
                    self.driver.add_cookie(cookie)
                self.driver.refresh()
                time.sleep(random.uniform(1, 3))

                try:
                    form = self.driver.find_element(By.XPATH, "//form[@data-testid='ApplyStep1Form']")
                    apply_button = form.find_element(By.XPATH, ".//button[@type='submit']")

                    # Use JavaScript to click the button to avoid detection
                    self.driver.execute_script("arguments[0].click();", apply_button)

                    time.sleep(random.uniform(1, 3))
                    try:
                        recaptcha_error = form.find_element(By.XPATH,
                                                            ".//div[contains(text(), 'Recaptcha token is invalid')]")
                        if recaptcha_error:
                            logging.error("Recaptcha token is invalid. Cannot proceed with application.")
                    except NoSuchElementException:
                        logging.info("No Recaptcha error found. Proceeding with application.")
                except Exception as e:
                    logging.info(f"Could not find apply button for {job_url}. It might be already applied.")
        finally:
            self._quit_driver()


cookies_file_path = "cookies.json"
bot = JobApplicationBot(ChromeDriverManager().install(), cookies_file_path)
job_search_query = "software engineer jobs site:join.com"
job_urls = bot.search_jobs_on_google(job_search_query)
bot.login_and_apply_to_jobs(job_urls)
