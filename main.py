from selenium import webdriver
from selenium.common import NoSuchElementException
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
        # self.chrome_options.add_argument("--headless")
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
        with open(self.cookies_file, 'r') as file:
            cookies = json.load(file)
        with open('config.json', 'r') as file:
            config_data = json.load(file)
        logged_in = False
        for job_url in job_urls:
            try:
                self.driver.get(job_url)

                if not logged_in:
                    for cookie in cookies:
                        if "sameSite" in cookie and cookie["sameSite"] not in ["Strict", "Lax", "None"]:
                            cookie["sameSite"] = "Lax"
                        time.sleep(1)
                        self.driver.add_cookie(cookie)
                    self.driver.refresh()
                    time.sleep(random.uniform(1, 3))

                try:
                    form = self.driver.find_element(By.XPATH, "//form[@data-testid='ApplyStep1Form']")
                    logged_in = True
                    apply_button = form.find_element(By.XPATH, ".//button[@type='submit']")
                    time.sleep(random.uniform(1, 4))
                    self.driver.execute_script("arguments[0].click();", apply_button)
                    time.sleep(random.uniform(8, 15))
                except NoSuchElementException:
                    logging.info("No Recaptcha error found. Proceeding with application.")

                try:
                    form = self.driver.find_element(By.XPATH, "//form[@id='OnePagerForm']")
                    questions = form.find_elements(By.XPATH, ".//div[@data-testid='QuestionItem']")

                    for question in questions:
                        question_text = question.find_element(By.XPATH, ".//span").text
                        answer_field = question.find_element(By.XPATH, ".//div[@data-testid='QuestionAnswer']")

                        if "reside in" in question_text:
                            answer = config_data.get("reside_in_barcelona", "No")
                            yes_no_field = answer_field.find_element(By.XPATH,
                                                                     f".//div[@data-testid='{answer}Answer']")
                            self.driver.execute_script("arguments[0].click();", yes_no_field)

                        elif "available to start" in question_text:
                            start_date = config_data.get("start_date", "")
                            date_input = answer_field.find_element(By.XPATH, ".//input[@type='text']")
                            date_input.send_keys(start_date)

                        elif "expected yearly compensation" in question_text:
                            compensation = config_data.get("expected_compensation", "")
                            compensation_input = answer_field.find_element(By.XPATH, ".//input[@type='text']")
                            compensation_input.send_keys(compensation)

                        elif "level of proficiency in English" in question_text:
                            proficiency = config_data.get("english_proficiency", "Professional working proficiency")
                            proficiency_input = answer_field.find_element(By.XPATH, ".//input[@type='text']")
                            proficiency_input.send_keys(proficiency)

                        elif "require sponsorship for employment visa status" in question_text:
                            sponsorship = config_data.get("require_sponsorship", "Yes")
                            yes_no_field = answer_field.find_element(By.XPATH,
                                                                     f".//div[@data-testid='{sponsorship}Answer']")
                            self.driver.execute_script("arguments[0].click();", yes_no_field)

                        elif "years of work experience in" in question_text:
                            experience = config_data.get("react_experience", "3")
                            experience_input = answer_field.find_element(By.XPATH, ".//input[@type='text']")
                            experience_input.send_keys(experience)

                    submit_button = form.find_element(By.XPATH, ".//button[@type='submit']")
                    self.driver.execute_script("arguments[0].click();", submit_button)
                    with open("applied.txt", "a") as file:
                        file.write(f"{job_url}\n")

                    time.sleep(random.uniform(1, 3))
                except Exception as e:
                    logging.info(f"Could not complete application for {job_url}. Error: {e}")
            except Exception as e:
                logging.info(f"Could not complete application for {job_url}. Error: {e}")


if __name__ == "__main__":
    cookies_file_path = "cookies.json"
    bot = JobApplicationBot(ChromeDriverManager().install(), cookies_file_path)
    job_search_query = "software engineer jobs site:join.com"
    job_urls = bot.search_jobs_on_google(job_search_query)
    bot.login_and_apply_to_jobs(job_urls)
