from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import json
import os
import random
import logging
from webdriver_manager.chrome import ChromeDriverManager

from generate_cover_letter import CoverLetterGenerator

logging.basicConfig(level=logging.INFO)


class JobApplicationBot:
    def __init__(self, driver_path, cookies_file):
        self.driver_path = driver_path
        self.cookies_file = cookies_file
        self.chrome_options = Options()
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.driver = None

    def _initialize_driver(self):
        service = Service(self.driver_path)
        self.driver = webdriver.Chrome(service=service, options=self.chrome_options)

    def _quit_driver(self):
        if self.driver:
            self.driver.quit()

    def search_jobs(self, query, site_filter="join.com"):
        try:
            job_urls = []
            with open('applied.txt', 'r') as file:
                applied_urls = file.read().splitlines()
            # try:
            #     job_urls = [
            #         url for url in search(query, num=100, stop=100, pause=3, tbs='qdr:d')
            #         if site_filter in url and url not in applied_urls
            #     ]
            # except Exception as e:
            #     logging.error(f"Error during Google search: {e}")

            if not job_urls:
                self._initialize_driver()
                n_pages = 3
                for page in range(1, n_pages):
                    url = f"http://www.google.com/search?q={query}&tbs=qdr:w&start={(page - 1) * 10}"
                    self.driver.get(url)
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    searches = soup.find_all('div', class_="yuRUbf")
                    for h in searches:
                        if site_filter in h.a.get('href') and h.a.get('href') not in applied_urls:
                            job_urls.append(h.a.get('href'))
            return job_urls
        finally:
            self._quit_driver()

    def login_and_apply_to_jobs(self, job_urls, config_data, platform_url="https://join.com/auth/login"):
        self._initialize_driver()
        with open(self.cookies_file, 'r') as file:
            cookies = json.load(file)

        logged_in = False
        self.driver.get(platform_url)
        for job_url in job_urls:
            try:

                if not logged_in:
                    for cookie in cookies:
                        if "sameSite" in cookie and cookie["sameSite"] not in ["Strict", "Lax", "None"]:
                            cookie["sameSite"] = "Lax"
                        time.sleep(1)
                        self.driver.add_cookie(cookie)
                    self.driver.refresh()
                    logged_in = True
                    time.sleep(random.uniform(1, 3))

                self.driver.get(job_url)

                retry_count = 0
                max_retries = 5
                skip_job = False
                hr_name = "HR Manager"

                while retry_count < max_retries:
                    try:
                        form = self.driver.find_element(By.XPATH, "//form[@data-testid='ApplyStep1Form']")
                        if form.find_elements(By.XPATH,
                                              ".//a[@data-testid='ViewApplicationLink']") or form.find_elements(
                            By.XPATH, ".//a[@data-testid='CompleteApplicationLink']"):
                            logging.info(f"Already applied for {job_url}. Skipping.")
                            skip_job = True
                            break

                        cover_letter_field = form.find_elements(By.XPATH, ".//div[@data-testid='CoverLetterField']")
                        if cover_letter_field:
                            try:
                                try:
                                    job_title_element = self.driver.find_element(By.XPATH,
                                                                                 "//h1[contains(@class, 'sc-hLseeU')]")
                                    job_title = job_title_element.text.strip()
                                    logging.info(f"Extracted job title: {job_title}")
                                except NoSuchElementException:
                                    logging.error("Job title element not found.")
                                    job_title = "Unknown Position"
                                except Exception as e:
                                    logging.error(f"Error extracting job title: {e}")
                                    job_title = "Unknown Position"
                                job_description_element = self.driver.find_element(By.XPATH,
                                                                                   "//div[@class='EditorContent-sc-2db2ee7e-0 ilEXuK']")
                                job_description_html = job_description_element.get_attribute('innerHTML')

                                soup = BeautifulSoup(job_description_html, 'html.parser')
                                job_description_text = soup.get_text(separator='\n', strip=True)

                                logging.info(f"Extracted job description: {job_description_text[:100]}...")

                            except NoSuchElementException:
                                logging.error("Job description element not found.")
                                job_description_text = ""
                            except Exception as e:
                                logging.error(f"Error extracting job description: {e}")
                                job_description_text = ""
                            try:
                                hr_name_element = self.driver.find_elements(By.XPATH,
                                                                            "//div[@data-testid='PersonName']")
                                if len(hr_name_element) > 1:
                                    hr_name = hr_name_element[1].text.strip()
                                    logging.info(f"Extracted HR name: {hr_name}")
                            except NoSuchElementException:
                                logging.warning("HR name element not found. Defaulting to 'HR Manager'.")

                            except Exception as e:
                                logging.error(f"Error extracting HR name: {e}")
                                hr_name = "HR Manager"
                            cover_letter_generator = CoverLetterGenerator()
                            cover_letter_text = cover_letter_generator.generate_cover_letter(job_description_text,
                                                                                             job_title,
                                                                                             hr_name)
                            cover_letter_generator.save_cover_letter_as_pdf(cover_letter_text)
                            logging.info("Cover letter is required. Uploading cover letter.")
                            cover_letter_input = cover_letter_field[0].find_element(By.XPATH, ".//input[@type='file']")
                            cover_letter_input.send_keys(os.path.abspath("cover_letter.pdf"))

                        apply_button = form.find_element(By.XPATH, ".//button[@type='submit']")
                        time.sleep(random.uniform(1, 4))
                        apply_button.click()
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
                            yes_no_field = answer_field.find_element(By.XPATH, f".//div[@data-testid='{answer}Answer']")
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

                        else:
                            pass
                            # with open('resume.json', 'r') as file:
                            #     resume_data = json.load(file)
                            # prompt = (
                            #     "I need help filling out a job application based on my resume. For each question on the application, analyze the text and context to generate responses:\n\n"
                            #     "• Yes/No Questions: Answer with ‘Yes’ or ‘No’ based on typical professional suitability for the role.\n"
                            #     "• Radio/Checkbox Questions: I’ll provide options, so select the most relevant choice based on my resume.\n"
                            #     "• Text Input Questions: Provide concise, relevant answers within two lines, using my resume as reference. Focus on key skills, experiences, and achievements, adapting the tone to match a professional job application.\n\n"
                            #     "If you need clarification on any question or answer, prompt me before proceeding."
                            # )
                            # import google.generativeai as genai
                            # genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
                            # self.model = genai.GenerativeModel("gemini-1.5-flash")
                            # ai_response = self.model.generate_content(prompt)
                            # answer = ai_response.text.strip()
                            # 
                            # try:
                            #     answer_input = answer_field.find_element(By.XPATH, ".//input[@type='text']")
                            #     answer_input.send_keys(answer)
                            # except NoSuchElementException:
                            #     try:
                            #         option_field = answer_field.find_element(By.XPATH,
                            #                                                  f".//div[@data-testid='{answer}Answer']")
                            #         self.driver.execute_script("arguments[0].click();", option_field)
                            #     except NoSuchElementException:
                            #         try:
                            #             yes_no_field = answer_field.find_element(By.XPATH,
                            #                                                      f".//div[@data-testid='{answer}Answer']")
                            #             self.driver.execute_script("arguments[0].click();", yes_no_field)
                            #         except NoSuchElementException:
                            #             logging.warning(f"Could not determine input type for question: {question_text}")

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
    job_search_queries = ['"software engineer" python site:join.com', '"software engineer" angular site:join.com',
                          '"software engineer" django site:join.com', '"Full Stack Developer" site:join.com',
                          '"Frontend Engineer" site:join.com', '"Backend Engineer" site:join.com']
    for job_search_query in job_search_queries:
        try:
            job_urls = bot.search_jobs(job_search_query)
            print(job_urls)
            with open('config.json', 'r') as file:
                config_data = json.load(file)

            current_start_date = datetime.strptime(config_data['start_date'], "%Y-%m-%d")
            new_start_date = current_start_date + timedelta(days=15)
            config_data['start_date'] = new_start_date.strftime("%d-%m-%Y")

            bot.login_and_apply_to_jobs(job_urls, config_data)
            time.sleep(random.uniform(10, 30))
        except Exception as e:
            logging.error(f"Error processing query {job_search_query}: {e}")
