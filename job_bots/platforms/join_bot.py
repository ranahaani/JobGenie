"""
Join.com specific implementation of the job application bot.
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
import logging

from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from job_bots.base_bot import BaseJobApplicationBot
from job_bots.config import ApplicationConfig, PlatformConfig
from job_bots.utils import record_applied_job
from generate_cover_letter import CoverLetterGenerator

# Configure logging
logger = logging.getLogger(__name__)


class JoinApplicationBot(BaseJobApplicationBot):
    """A bot that automates job applications on join.com."""

    def __init__(self, driver_path: str, platform_config: PlatformConfig, cookies_file: Optional[Path] = None):
        """Initialize the Join.com application bot.

        Args:
            driver_path: Path to the Chrome driver
            platform_config: Join.com platform configuration
            cookies_file: Path to the cookies file (optional)
        """
        super().__init__(driver_path, platform_config, cookies_file)
        self.platform_url = platform_config.login_url or "https://join.com/auth/login"

    def _extract_job_details(self) -> Tuple[str, str, str]:
        """Extract job details from the page.

        Returns:
            Tuple of (job_title, job_description, hr_name)
        """
        try:
            job_title = self.driver.find_element(
                By.XPATH, "//h1[contains(@class, 'sc-hLseeU')]"
            ).text.strip()
            logger.info(f"Extracted job title: {job_title}")
        except NoSuchElementException:
            logger.error("Job title element not found.")
            job_title = "Unknown Position"

        try:
            description_element = self.driver.find_element(
                By.XPATH, "//div[@class='EditorContent-sc-2db2ee7e-0 ilEXuK']"
            )
            description_html = description_element.get_attribute('innerHTML')
            job_description = BeautifulSoup(description_html, 'html.parser').get_text(separator='\n', strip=True)
            logger.info(f"Extracted job description: {job_description[:100]}...")
        except NoSuchElementException:
            description_element = self.driver.find_element(
                By.ID, "about-job"
            )
            description_html = description_element.get_attribute('innerHTML')
            job_description = BeautifulSoup(description_html, 'html.parser').get_text(separator='\n', strip=True)
            

        try:
            hr_elements = self.driver.find_elements(By.XPATH, "//div[@data-testid='PersonName']")
            hr_name = hr_elements[1].text.strip() if len(hr_elements) > 1 else self.DEFAULT_HR_NAME
            logger.info(f"Extracted HR name: {hr_name}")
        except (NoSuchElementException, IndexError):
            logger.warning(f"HR name element not found. Defaulting to '{self.DEFAULT_HR_NAME}'.")
            hr_name = self.DEFAULT_HR_NAME

        return job_title, job_description, hr_name

    def _handle_captcha(self, form: WebElement) -> bool:
        """Handle captcha detection and retry logic.

        Args:
            form: The form WebElement

        Returns:
            Boolean indicating if captcha was handled successfully
        """
        try:
            captcha_error = form.find_elements(By.XPATH, ".//div[contains(text(), 'Recaptcha token is invalid')]")
            if captcha_error:
                logger.warning("Captcha detected. Retrying...")
                return True
        except:
            return False
        return False

    def _submit_form_with_retry(self, form: WebElement, form_type: str = "initial") -> bool:
        """Submit form with retry logic for captcha handling.

        Args:
            form: The form WebElement
            form_type: Type of form ("initial" or "questions")

        Returns:
            Boolean indicating if submission was successful
        """
        retry_count = 0
        while retry_count < self.MAX_RETRIES:
            try:
                cover_letter_fields = form.find_elements(By.XPATH, ".//div[@data-testid='CoverLetterField']")
                cover_letter_field = cover_letter_fields[0] if cover_letter_fields else None
                if cover_letter_field:
                    self._submit_cover_letter(form)
                submit_button = form.find_element(By.XPATH, ".//button[@type='submit']")
                self.driver.execute_script("arguments[0].click();", submit_button)
                self._random_delay(self.SUBMISSION_DELAY)

                if self._handle_captcha(form):
                    retry_count += 1
                    if retry_count < self.MAX_RETRIES:
                        self.driver.refresh()
                        self._random_delay(self.RETRY_DELAY)
                        form = self.driver.find_element(By.XPATH, "//form[@data-testid='ApplyStep1Form']")
                        if form_type == "questions":
                            form = self.driver.find_element(By.XPATH, "//form[@id='OnePagerForm']")
                    else:
                        logger.error("Max retries reached for captcha.")
                        return False
                else:
                    return True
            except Exception as e:
                logger.error(f"Error submitting {form_type} form: {e}")
                retry_count += 1

        return False

    def _handle_application_questions(self, form: WebElement, config: ApplicationConfig) -> None:
        """Handle application form questions.

        Args:
            form: The form WebElement
            config: Application configuration
        """
        questions = form.find_elements(By.XPATH, ".//div[@data-testid='QuestionItem']")

        question_handlers = {
            "reside in": lambda field: self._handle_yes_no(field, config.reside_in_barcelona),
            "currently legally permitted": lambda field: self._handle_yes_no(field, config.reside_in_barcelona),
            "available to start": lambda field: self._handle_text_input(field, config.start_date),
            "expected yearly compensation": lambda field: self._handle_text_input(field, config.expected_compensation),
            "level of proficiency in English": lambda field: self._handle_text_input(field, config.english_proficiency),
            "level of proficiency in": lambda field: self._handle_text_input(field, config.german_proficiency),
            "require sponsorship": lambda field: self._handle_yes_no(field, config.require_sponsorship),
            "years of work experience": lambda field: self._handle_text_input(field, config.react_experience),
            "currently live": lambda field: self._handle_text_input(field, config.current_city),
            "comfortable working in a remote": lambda field: self._handle_text_input(field, config.remotely_available),
        }

        for question in questions:
            question_text = question.find_element(By.XPATH, ".//span").text.lower()
            answer_field = question.find_element(By.XPATH, ".//div[@data-testid='QuestionAnswer']")

            for keyword, handler in question_handlers.items():
                if keyword in question_text:
                    handler(answer_field)
                    break

            self._random_delay(self.RETRY_DELAY)

    @staticmethod
    def _handle_yes_no(field: WebElement, answer: str) -> None:
        """Handle yes/no question fields."""
        yes_no_field = field.find_element(By.XPATH, f".//div[@data-testid='{answer}Answer']")
        yes_no_field.click()

    @staticmethod
    def _handle_text_input(field: WebElement, answer: str) -> None:
        """Handle text input fields."""
        input_field = field.find_element(By.XPATH, ".//input[@type='text']")
        input_field.send_keys(answer)

    def _submit_cover_letter(self, cover_letter_field: WebElement) -> None:
        """Submit cover letter to form.
        
        Args:
            cover_letter_field: The form WebElement containing the cover letter field
        """
        try:
            cover_letter_input = cover_letter_field.find_element(By.XPATH, ".//input[@type='file']")
            cover_letter_input.send_keys(str(Path("cover_letter.pdf").absolute()))
        except Exception as e:
            logger.error(f"Unable to submit cover letter: {e}")

    def apply_to_job(self, job_url: str, config: ApplicationConfig) -> bool:
        """Apply to a specific job.

        Args:
            job_url: URL of the job posting
            config: Application configuration

        Returns:
            Boolean indicating if application was successful
        """
        self.driver.get(job_url)

        try:
            # Initial application form
            form = self.driver.find_element(By.XPATH, "//form[@data-testid='ApplyStep1Form']")

            # Check if already applied
            if form.find_elements(By.XPATH, ".//a[@data-testid='ViewApplicationLink']") or \
                    form.find_elements(By.XPATH, ".//a[@data-testid='CompleteApplicationLink']"):
                logger.info(f"Already applied for {job_url}. Skipping.")
                record_applied_job(job_url)
                return False

            # Handle cover letter if required
            cover_letter_field = form.find_elements(By.XPATH, ".//div[@data-testid='CoverLetterField']")
            if cover_letter_field:
                job_title, job_description, hr_name = self._extract_job_details()

                cover_letter_generator = CoverLetterGenerator()
                cover_letter_text = cover_letter_generator.generate_cover_letter(
                    job_description, job_title, hr_name
                )
                cover_letter_generator.save_cover_letter_as_pdf(cover_letter_text)

            # Submit initial form with retry logic
            if not self._submit_form_with_retry(form, "initial"):
                return False

            # Handle additional questions
            questions_form = self.driver.find_element(By.XPATH, "//form[@id='OnePagerForm']")
            self._handle_application_questions(questions_form, config)

            # Submit questions form with retry logic
            if not self._submit_form_with_retry(questions_form, "questions"):
                return False

            # Record successful application
            record_applied_job(job_url)
            return True

        except Exception as e:
            logger.error(f"Error applying to {job_url}: {e}")
            return False

    def login_and_apply_to_jobs(self, job_urls: List[str], config: ApplicationConfig) -> None:
        """Login and apply to multiple jobs.

        Args:
            job_urls: List of job URLs to apply to
            config: Application configuration
        """
        self.driver.get(self.platform_url)
        self._load_cookies()
        self.driver.refresh()
        self._random_delay(self.RETRY_DELAY)

        for job_url in job_urls:
            try:
                success = self.apply_to_job(job_url, config)
                if success:
                    logger.info(f"Successfully applied to {job_url}")
                    self._random_delay((10, 30))
            except Exception as e:
                logger.error(f"Failed to process {job_url}: {e}") 
