from bs4 import BeautifulSoup
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


# Check if the resume is already uploaded
# uploaded_icon = form.find_element(By.XPATH, ".//i[@data-testid='attachment-uploaded-icon']")
# if not uploaded_icon:
#     # Upload resume if not already uploaded
#     resume_input = form.find_element(By.XPATH, ".//input[@type='file']")
#     resume_input.send_keys("/path/to/your/resume.pdf")

# Optionally upload a cover letter
# cover_letter_input = form.find_element(By.XPATH, ".//input[@type='file']")
# cover_letter_input.send_keys("/path/to/your/cover_letter.pdf")


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

        try:
            job_urls = []
            with open('applied.txt', 'r') as file:
                applied_urls = file.read().splitlines()
            try:
                job_urls = [
                    # url for url in search(query, num=100, stop=100, pause=3, tbs='qdr:d')
                    # if 'join.com/companies' in url and url not in applied_urls
                ]
            except:
                pass

            if not job_urls:
                self._initialize_driver()
                n_pages = 3
                for page in range(1, n_pages):
                    url = f"http://www.google.com/search?q={query}&tbs=qdr:w&start={(page - 1) * 10}"
                    self.driver.get(url)
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    # soup = BeautifulSoup(r.text, 'html.parser')

                    searches = soup.find_all('div', class_="yuRUbf")
                    for h in searches:
                        if 'join.com/companies' in h.a.get('href') and h.a.get('href') not in applied_urls:
                            job_urls.append(h.a.get('href'))
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
                    logged_in = True
                    time.sleep(random.uniform(1, 3))

                retry_count = 0
                max_retries = 5
                skip_job = False
                while retry_count < max_retries:
                    try:
                        form = self.driver.find_element(By.XPATH, "//form[@data-testid='ApplyStep1Form']")
                        if form.find_elements(By.XPATH,
                                              ".//a[@data-testid='ViewApplicationLink']") or form.find_elements(
                            By.XPATH, ".//a[@data-testid='CompleteApplicationLink']"):
                            logging.info(f"Already applied for {job_url}. Skipping.")
                            skip_job = True
                            break

                        apply_button = form.find_element(By.XPATH, ".//button[@type='submit']")

                        time.sleep(random.uniform(1, 4))
                        apply_button.click()
                        self.driver.execute_script("arguments[0].click();", apply_button)
                        break
                    except NoSuchElementException:
                        skip_job = True
                        break
                    except Exception as e:
                        logging.warning(f"Attempt {retry_count + 1} failed for {job_url}. Error: {e}")
                        retry_count += 1
                        if retry_count < max_retries:
                            logging.info("Retrying...")
                            self.driver.refresh()
                            time.sleep(random.uniform(1, 3))
                        else:
                            skip_job = True
                            logging.error(f"Failed to apply for {job_url} after {max_retries} attempts.")

                if skip_job:
                    continue

                try:
                    time.sleep(random.uniform(10, 20))
                    form = self.driver.find_element(By.XPATH, "//form[@id='OnePagerForm']")
                    questions = form.find_elements(By.XPATH, ".//div[@data-testid='QuestionItem']")

                    for question in questions:
                        question_text = question.find_element(By.XPATH, ".//span").text
                        answer_field = question.find_element(By.XPATH, ".//div[@data-testid='QuestionAnswer']")
                        time.sleep(random.uniform(1, 3))

                        if "reside in" in question_text or "currently legally permitted" in question_text:
                            answer = config_data.get("reside_in_barcelona", "No")
                            yes_no_field = answer_field.find_element(By.XPATH,
                                                                     f".//div[@data-testid='{answer}Answer']")
                            self.driver.execute_script("arguments[0].click();", yes_no_field)

                        elif "available to start" in question_text or "available to start working" in question_text or "earliest date you could start" in question_text:
                            start_date = config_data.get("start_date", "")
                            date_input = answer_field.find_element(By.XPATH, ".//input[@type='text']")
                            date_input.send_keys(start_date)

                        elif "expected yearly compensation" in question_text or "salary range" in question_text:
                            compensation = config_data.get("expected_compensation", "")
                            compensation_input = answer_field.find_element(By.XPATH, ".//input[@type='text']")
                            compensation_input.send_keys(compensation)

                        elif "level of proficiency in English" in question_text:
                            proficiency = config_data.get("english_proficiency", "Professional working proficiency")
                            proficiency_input = answer_field.find_element(By.XPATH, ".//input[@type='text']")
                            proficiency_input.send_keys(proficiency)

                        elif "level of proficiency in" in question_text:
                            proficiency = config_data.get("german_proficiency", "None")
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

                        elif "currently live" in question_text or "currently located" in question_text:
                            experience = config_data.get("current_city", "Lahore, Pakistan")
                            experience_input = answer_field.find_element(By.XPATH, ".//input[@type='text']")
                            experience_input.send_keys(experience)

                        elif "comfortable working in a remote" in question_text:
                            experience = config_data.get("remotely_available", "Yes")
                            experience_input = answer_field.find_element(By.XPATH, ".//input[@type='text']")
                            experience_input.send_keys(experience)

                    submit_button = form.find_element(By.XPATH, ".//button[@type='submit']")
                    self.driver.execute_script("arguments[0].click();", submit_button)
                    time.sleep(random.uniform(10, 15))
                    with open("applied.txt", "a") as file:
                        file.write(f"{job_url}\n")
                except Exception as e:
                    time.sleep(random.uniform(1, 3))
                    logging.info(f"Could not complete application for {job_url}. Error: {e}")
            except Exception as e:
                time.sleep(random.uniform(1, 3))
                logging.info(f"Could not complete application for {job_url}. Error: {e}")


if __name__ == "__main__":
    cookies_file_path = "cookies.json"
    bot = JobApplicationBot(ChromeDriverManager().install(), cookies_file_path)
    job_search_queres = ['"software engineer" python site:join.com', '"software engineer" angular site:join.com',
                         '"software engineer" django site:join.com', '"Full Stack Developer" site:join.com',
                         '"Frontend Engineer" site:join.com', '"Backend Engineer" site:join.com']
    for job_search_query in job_search_queres:
        try:
            job_urls = bot.search_jobs_on_google(job_search_query)
            print(job_urls)
            bot.login_and_apply_to_jobs(job_urls)
            time.sleep(random.uniform(10, 30))
        except:
            pass
