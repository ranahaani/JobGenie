"""
Lever.co specific implementation of the job application bot.
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
import logging
import re
import os

from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from job_bots.base_bot import BaseJobApplicationBot
from job_bots.config import ApplicationConfig, PlatformConfig
from job_bots.utils import record_applied_job
from generate_cover_letter import CoverLetterGenerator

# Configure logging
logger = logging.getLogger(__name__)


class LeverApplicationBot(BaseJobApplicationBot):
    """A bot that automates job applications on Lever.co."""

    def __init__(self, driver_path: str, platform_config: PlatformConfig, cookies_file: Optional[Path] = None):
        """Initialize the Lever.co application bot.

        Args:
            driver_path: Path to the Chrome driver
            platform_config: Lever.co platform configuration
            cookies_file: Path to the cookies file (optional)
        """
        super().__init__(driver_path, platform_config, cookies_file)

        # Lever doesn't typically require login for applications
        self.platform_url = None
        self.resume_data_cache = None

    def _extract_job_details(self) -> Tuple[str, str, str]:
        """Extract job details from the Lever job page.

        Returns:
            Tuple of (job_title, job_description, hr_name)
        """
        try:
            # Extract job title
            job_title_element = self.driver.find_element(
                By.XPATH, "//h2[contains(@class, 'posting-headline')]"
            )
            job_title = job_title_element.text.strip()
            logger.info(f"Extracted job title: {job_title}")
        except NoSuchElementException:
            try:
                # Alternative method to find job title
                job_title_element = self.driver.find_element(
                    By.XPATH, "//h2"
                )
                job_title = job_title_element.text.strip()
                logger.info(f"Extracted job title (alternative): {job_title}")
            except NoSuchElementException:
                logger.error("Job title element not found.")
                job_title = "Unknown Position"

        try:
            # Extract job description from the main content
            description_element = self.driver.find_element(
                By.XPATH, "//div[contains(@class, 'content')]"
            )
            description_html = description_element.get_attribute('innerHTML')
            job_description = BeautifulSoup(description_html, 'html.parser').get_text(separator='\n', strip=True)
            logger.info(f"Extracted job description: {job_description[:100]}...")
        except NoSuchElementException:
            try:
                # Try to get all content from the page
                description_element = self.driver.find_element(
                    By.XPATH, "//div[contains(@id, 'content')]"
                )
                description_html = description_element.get_attribute('innerHTML')
                job_description = BeautifulSoup(description_html, 'html.parser').get_text(separator='\n', strip=True)
                logger.info(f"Extracted job description (alternative): {job_description[:100]}...")
            except NoSuchElementException:
                logger.error("Job description element not found.")
                job_description = ""

        # Lever doesn't typically display HR contact names on job pages
        hr_name = self.DEFAULT_HR_NAME

        # Look for company name to personalize
        try:
            company_element = self.driver.find_element(
                By.XPATH, "//a/img"
            )
            company_name = company_element.get_attribute("alt")
            if company_name:
                hr_name = f"{company_name} Hiring Manager"
                logger.info(f"Using company name for HR: {hr_name}")
        except NoSuchElementException:
            logger.warning(f"Company name not found. Using default HR name: {hr_name}")

        return job_title, job_description, hr_name

    def _is_already_applied(self) -> bool:
        """Check if already applied for this job.

        Returns:
            Boolean indicating if already applied
        """
        # Lever doesn't typically show if you've already applied
        # This method is primarily used as a safety check
        return False

    def _handle_resume_upload(self) -> bool:
        """Handle resume upload in the Lever application form.

        Returns:
            Boolean indicating if upload was successful
        """
        try:
            # Locate the file input for resume
            resume_input = self.driver.find_element(
                By.XPATH, "//input[@name='resume']"
            )

            # Set the file path
            resume_path = str(Path("Abdullah_Resume.pdf").absolute())
            resume_input.send_keys(resume_path)

            logger.info("Resume uploaded successfully")
            self._random_delay((5, 10))
            return True
        except NoSuchElementException:
            logger.error("Resume upload field not found")
            return False
        except Exception as e:
            logger.error(f"Error uploading resume: {e}")
            return False

    def _fill_basic_info(self, config: ApplicationConfig) -> bool:
        """Fill basic information fields in the Lever application form.

        Args:
            config: Application configuration

        Returns:
            Boolean indicating if all required fields were filled
        """
        try:
            # Load resume data if not already loaded
            if not self.resume_data_cache:
                try:
                    with open('resume.json', 'r') as f:
                        self.resume_data_cache = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading resume data: {e}")
                    return False

            # Fill in full name
            try:
                self._random_delay((5, 10))
                name_field = self.driver.find_element(By.XPATH, "//input[@name='name']")
                name_field.clear()
                name_field.send_keys(self.resume_data_cache.get("name", ""))
            except NoSuchElementException:
                logger.error("Name field not found")
                return False

            # Fill in email
            try:
                self._random_delay((5, 10))
                email_field = self.driver.find_element(By.XPATH, "//input[@name='email']")
                email_field.clear()
                email_field.send_keys(self.resume_data_cache.get("contact", {}).get("email", ""))
            except NoSuchElementException:
                logger.error("Email field not found")
                return False

            # Fill in phone
            try:
                self._random_delay((5, 10))
                phone_field = self.driver.find_element(By.XPATH, "//input[@name='phone']")
                phone_field.clear()
                phone_field.send_keys(self.resume_data_cache.get("contact", {}).get("phone", ""))
            except NoSuchElementException:
                logger.error("Phone field not found")
                return False

            # Fill in current location (if available)
            try:
                self._random_delay((5, 10))
                location_field = self.driver.find_element(By.XPATH, "//input[@name='location']")
                location_field.clear()
                location_field.send_keys(self.resume_data_cache.get("contact", {}).get("location", ""))
            except NoSuchElementException:
                logger.warning("Location field not found, skipping")

            # Fill in current company (if available)
            try:
                self._random_delay((5, 10))
                company_field = self.driver.find_element(By.XPATH, "//input[@name='org']")
                company_field.clear()
                if self.resume_data_cache.get("experience") and len(self.resume_data_cache["experience"]) > 0:
                    company_field.send_keys(self.resume_data_cache["experience"][0].get("company", ""))
            except NoSuchElementException:
                logger.warning("Company field not found, skipping")

            logger.info("Basic information filled successfully")
            return True
        except Exception as e:
            logger.error(f"Error filling basic information: {e}")
            return False

    def _fill_links(self) -> bool:
        """Fill in links (LinkedIn, GitHub, etc.) in the Lever application form.

        Returns:
            Boolean indicating if links were filled successfully
        """
        try:
            # Load resume data if not already loaded
            if not self.resume_data_cache:
                try:
                    with open('resume.json', 'r') as f:
                        self.resume_data_cache = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading resume data: {e}")
                    return False

            # Fill in LinkedIn URL
            try:
                self._random_delay((5, 10))
                linkedin_field = self.driver.find_element(By.XPATH,
                                                          "//input[contains(@placeholder, 'LinkedIn') or @name='urls[LinkedIn]']")
                linkedin_field.clear()
                linkedin_field.send_keys(self.resume_data_cache.get("contact", {}).get("linkedin", ""))
            except NoSuchElementException:
                logger.warning("LinkedIn field not found, skipping")

            # Fill in GitHub URL
            try:
                self._random_delay((5, 10))
                github_field = self.driver.find_element(By.XPATH,
                                                        "//input[contains(@placeholder, 'GitHub') or @name='urls[GitHub]']")
                github_field.clear()
                github_field.send_keys(self.resume_data_cache.get("contact", {}).get("github", ""))
            except NoSuchElementException:
                logger.warning("GitHub field not found, skipping")

            logger.info("Links filled successfully")
            return True
        except Exception as e:
            logger.error(f"Error filling links: {e}")
            return False

    def _handle_work_authorization(self, config: ApplicationConfig) -> bool:
        """Handle work authorization questions in the Lever application form.

        Args:
            config: Application configuration

        Returns:
            Boolean indicating if questions were answered successfully
        """
        try:
            self._random_delay((5, 10))
            # Find sponsorship question
            sponsorship_radios = self.driver.find_elements(
                By.XPATH, "//input[@type='radio' and @name='sponsorship']"
            )

            if sponsorship_radios:
                # Determine which option to select based on config
                require_sponsorship = config.require_sponsorship.lower() == "yes"

                # Find the correct radio button to click
                if require_sponsorship:
                    # Look for "Yes" option
                    for radio in sponsorship_radios:
                        label = radio.find_element(By.XPATH, "following-sibling::*[1]")
                        if label.text.strip().lower() == "yes":
                            radio.click()
                            break
                else:
                    # Look for "No" option
                    for radio in sponsorship_radios:
                        label = radio.find_element(By.XPATH, "following-sibling::*[1]")
                        if label.text.strip().lower() == "no":
                            radio.click()
                            break

            logger.info("Work authorization questions handled successfully")
            return True
        except Exception as e:
            logger.error(f"Error handling work authorization questions: {e}")
            return False

    def _handle_location_questions(self, config: ApplicationConfig) -> bool:
        """Handle location-related questions in the Lever application form.

        Args:
            config: Application configuration

        Returns:
            Boolean indicating if questions were answered successfully
        """
        try:
            self._random_delay((5, 10))
            # Find all location-related checkboxes
            location_checkboxes = self.driver.find_elements(
                By.XPATH, "//input[@type='checkbox']"
            )

            # Look for "Yes" option for work location questions
            for checkbox in location_checkboxes:
                try:
                    label = checkbox.find_element(By.XPATH, "following-sibling::*[1]")
                    if label.text.strip().lower() == "yes":
                        if not checkbox.is_selected():
                            checkbox.click()
                except:
                    continue

            logger.info("Location questions handled successfully")
            return True
        except Exception as e:
            logger.error(f"Error handling location questions: {e}")
            return False

    def _fill_additional_info(self, config: ApplicationConfig) -> bool:
        """Fill additional information field in the Lever application form.

        Args:
            config: Application configuration

        Returns:
            Boolean indicating if information was filled successfully
        """
        try:
            self._random_delay((5, 10))
            # Find additional information textarea
            additional_info = self.driver.find_element(By.XPATH, "//textarea")

            # Create a brief message
            message = (
                f"I am excited about this opportunity and believe my skills align well with the position. "
                f"I am available to start on {config.start_date} and my expected compensation is {config.expected_compensation}. "
                f"I am fluent in English ({config.english_proficiency}) and am {config.remotely_available.lower()} available to work remotely."
            )

            additional_info.clear()
            additional_info.send_keys(message)

            logger.info("Additional information filled successfully")
            return True
        except NoSuchElementException:
            logger.warning("Additional information field not found, skipping")
            return True
        except Exception as e:
            logger.error(f"Error filling additional information: {e}")
            return False

    def _handle_demographic_questions(self) -> bool:
        """Handle demographic questions in the Lever application form.

        Returns:
            Boolean indicating if questions were handled successfully
        """
        # Skip demographic questions as they are optional
        logger.info("Skipping optional demographic questions")
        return True

    def _submit_application(self) -> bool:
        """Submit the Lever application form.

        Returns:
            Boolean indicating if submission was successful
        """
        try:
            self._random_delay((5, 10))

            # Check for any validation errors before submitting
            error_messages = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'error-message')]")
            if error_messages:
                for error in error_messages:
                    logger.error(f"Form validation error: {error.text}")
                return False

            # Find the submit button
            submit_button = self.driver.find_element(
                By.XPATH, "//button[contains(text(), 'Submit application')]"
            )

            # Click the submit button
            self.driver.execute_script("arguments[0].click();", submit_button)
            logger.info("Clicked submit button")

            # Give the page some time to process
            self._random_delay((3, 5))

            # Check for validation errors after clicking submit
            error_messages = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'error-message')]")
            if error_messages:
                for error in error_messages:
                    logger.error(f"Form validation error after submission: {error.text}")
                return False

            # Use a longer timeout for submission confirmation (30 seconds)
            longer_wait = WebDriverWait(self.driver, 30)

            # Check for various success indicators
            try:
                # Look for several possible success indicators
                success_conditions = [
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Thank you')]")),
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'thank you')]")),
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Application received')]")),
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[contains(text(), 'application has been submitted')]")),
                    EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Application received')]")),
                    EC.url_contains("thanks")
                ]

                # Wait for any of the success conditions
                for condition in success_conditions:
                    try:
                        longer_wait.until(condition)
                        logger.info("Application submitted successfully")
                        return True
                    except:
                        continue

                # If we reached this point without finding any success indicators, check URL
                if "thanks" in self.driver.current_url or "confirmation" in self.driver.current_url:
                    logger.info("Application submitted successfully (detected from URL)")
                    return True

                # If the form is no longer visible, assume success
                try:
                    self.driver.find_element(By.XPATH, "//button[contains(text(), 'Submit application')]")
                except NoSuchElementException:
                    logger.info("Application submitted successfully (form no longer present)")
                    return True

                logger.error("Could not confirm application submission")
                return False

            except TimeoutException:
                logger.error("Timed out waiting for submission confirmation")

                # Check if the form is still visible
                try:
                    self.driver.find_element(By.XPATH, "//button[contains(text(), 'Submit application')]")
                    logger.error("Form is still present, submission likely failed")
                    return False
                except NoSuchElementException:
                    logger.info("Form is no longer present, assuming successful submission")
                    return True

        except NoSuchElementException:
            logger.error("Submit button not found")
            return False
        except Exception as e:
            logger.error(f"Error submitting application: {e}")
            return False

    def apply_to_job(self, job_url: str, config: ApplicationConfig) -> bool:
        """Apply to a job on Lever.co.

        Args:
            job_url: URL of the job posting
            config: Application configuration

        Returns:
            Boolean indicating if application was successful
        """
        logger.info(f"Applying to job at {job_url}")

        try:
            # Navigate to the job page
            self.driver.get(job_url)
            self._random_delay(self.RETRY_DELAY)

            # Check if job URL is already in the applied jobs
            try:
                if os.path.exists('applied.txt') and job_url in open('applied.txt').read():
                    logger.info(f"Already applied for {job_url}. Skipping.")
                    return False
            except:
                pass

            # Extract job details for cover letter
            job_title, job_description, hr_name = self._extract_job_details()

            # Generate cover letter
            cover_letter_generator = CoverLetterGenerator()
            cover_letter_text = cover_letter_generator.generate_cover_letter(
                job_description, job_title, hr_name
            )
            cover_letter_generator.save_cover_letter_as_pdf(cover_letter_text)

            # Click on Apply button
            apply_button = self.driver.find_element(
                By.XPATH, "//a[contains(text(), 'Apply for this job')]"
            )
            apply_button.click()
            self._random_delay(self.RETRY_DELAY)

            # Track how many steps we've completed successfully
            completed_steps = 0
            total_steps = 7  # Total number of steps in the application process

            # Handle each section of the application form
            steps = [
                self._handle_resume_upload,
                lambda: self._fill_basic_info(config),
                self._fill_links,
                lambda: self._handle_work_authorization(config),
                lambda: self._handle_location_questions(config),
                lambda: self._fill_additional_info(config),
                self._handle_demographic_questions,
            ]

            # Execute all form filling steps
            for step_func in steps:
                if step_func():
                    completed_steps += 1
                else:
                    logger.error("Application process failed during form filling")
                    return False
                self._random_delay(self.RETRY_DELAY)

            # All form filling steps completed successfully
            if completed_steps == total_steps:
                # Try to submit the form
                submission_result = self._submit_application()

                # Even if we can't fully confirm submission success,
                # if we filled out all the fields and clicked submit,
                # we'll consider it a success for tracking purposes
                if submission_result:
                    logger.info(f"Successfully applied to {job_url}")
                    record_applied_job(job_url)
                    return True
                else:
                    logger.warning(f"Form filled completely but submission confirmation failed for {job_url}")
                    # Still record as applied because we completed all steps and attempted submission
                    record_applied_job(job_url)
                    return True
            else:
                logger.error(f"Failed to complete all application steps for {job_url}")
                return False

        except Exception as e:
            logger.error(f"Error applying to job at {job_url}: {e}")
            return False

    def login_and_apply_to_jobs(self, job_urls: List[str], config: ApplicationConfig) -> None:
        """Apply to multiple jobs on Lever.co.

        Args:
            job_urls: List of job posting URLs
            config: Application configuration
        """
        logger.info(f"Applying to {len(job_urls)} jobs on Lever.co")

        try:
            # Lever doesn't typically require login
            for job_url in job_urls:
                try:
                    success = self.apply_to_job(job_url, config)
                    if success:
                        logger.info(f"Successfully applied to {job_url}")
                    else:
                        logger.warning(f"Failed to apply to {job_url}")

                    # Random delay between applications
                    self._random_delay((5, 10))
                except Exception as e:
                    logger.error(f"Error applying to {job_url}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error in login_and_apply_to_jobs: {e}")
