"""
Greenhouse.io specific implementation of the job application bot.
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import json
import logging
import re
import os

from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import Select

from extract_greenhouse_fields import GreenhouseFormAnalyzer
from job_bots.base_bot import BaseJobApplicationBot
from job_bots.config import ApplicationConfig, PlatformConfig
from job_bots.utils import record_applied_job, is_already_applied

# Configure logging
logger = logging.getLogger(__name__)


class GreenhouseApplicationBot(BaseJobApplicationBot):
    """Bot for automating job applications on Greenhouse platform."""

    def __init__(self, driver_path: str, platform_config: PlatformConfig, cookies_file: Optional[Path] = None):
        """Initialize the Greenhouse application bot.

        Args:
            driver_path: Path to the Chrome driver
            platform_config: Greenhouse platform configuration
            cookies_file: Path to the cookies file (optional)
        """
        super().__init__(driver_path, platform_config, cookies_file)
        self.form_analyzer = GreenhouseFormAnalyzer()
        # To store current config for use in some methods
        self.current_config = None
        # Resume data cache
        self.resume_data_cache = None

    def _extract_job_details(self) -> Tuple[str, str, str]:
        """Extract job details from the Greenhouse job page.

        Returns:
            Tuple of (job_title, job_description, hr_name)
        """
        try:
            # Extract job title - common patterns in Greenhouse
            job_title_element = self.driver.find_element(
                By.XPATH, "//h1[contains(@class, 'app-title') or contains(@class, 'job-title')]"
            )
            job_title = job_title_element.text.strip()
            logger.info(f"Extracted job title: {job_title}")
        except NoSuchElementException:
            try:
                # Alternative method to find job title
                job_title_element = self.driver.find_element(
                    By.XPATH, "//h1"
                )
                job_title = job_title_element.text.strip()
                logger.info(f"Extracted job title (alternative): {job_title}")
            except NoSuchElementException:
                logger.error("Job title element not found.")
                job_title = "Unknown Position"

        try:
            # Extract job description - common patterns in Greenhouse
            description_element = self.driver.find_element(
                By.XPATH, "//div[contains(@class, 'content-intro') or contains(@class, 'job-description')]"
            )
            description_html = description_element.get_attribute('innerHTML')
            job_description = BeautifulSoup(description_html, 'html.parser').get_text(separator='\n', strip=True)
            logger.info(f"Extracted job description: {job_description[:100]}...")
        except NoSuchElementException:
            try:
                # Try to get all content
                description_element = self.driver.find_element(
                    By.XPATH, "//div[@id='content' or @id='main-content' or @class='main-content']"
                )
                description_html = description_element.get_attribute('innerHTML')
                job_description = BeautifulSoup(description_html, 'html.parser').get_text(separator='\n', strip=True)
                logger.info(f"Extracted job description (alternative): {job_description[:100]}...")
            except NoSuchElementException:
                logger.error("Job description element not found.")
                job_description = ""

        # Greenhouse doesn't typically display HR contact names on job pages
        hr_name = self.DEFAULT_HR_NAME

        # Look for company name to personalize
        try:
            company_element = self.driver.find_element(
                By.XPATH, "//div[contains(@class, 'company-name')]"
            )
            company_name = company_element.text.strip()
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
        try:
            # Look for indicators that application was already submitted
            applied_indicators = [
                "//div[contains(text(), 'You have already applied')]",
                "//p[contains(text(), 'already applied')]",
                "//div[contains(@class, 'application-complete')]"
            ]

            for indicator in applied_indicators:
                elements = self.driver.find_elements(By.XPATH, indicator)
                if elements:
                    return True

            return False
        except Exception:
            return False

    def _handle_greenhouse_form_field(self, field_id: str, field_type: str, answer: str) -> None:
        """Handle a specific field in the Greenhouse form.

        Args:
            field_id: HTML ID of the field
            field_type: Type of field (text, select, etc.)
            answer: Answer to fill in the field
        """
        try:
            if field_type == "text" or field_type == "email" or field_type == "tel":
                # Handle text inputs
                field = self.driver.find_element(By.ID, field_id)
                field.clear()
                field.send_keys(answer)

            elif field_type == "select":
                # Handle both traditional and React-based select components
                field = self.driver.find_element(By.ID, field_id)

                # Check if it's a multi-select field by looking for "[]" in the id or name
                is_multi_select = "[]" in field_id or field.get_attribute("multiple") == "true"

                # Check if it's a React-based select
                parent = None
                try:
                    parent = field.find_element(By.XPATH, "./ancestor::div[contains(@class, 'select-shell')]")
                except:
                    pass

                if parent:
                    # React-based select handling
                    # Click to open the dropdown
                    self.driver.execute_script("arguments[0].click();", field)
                    self._random_delay((0.5, 1))

                    # For multi-select fields, we might need to select multiple options
                    if is_multi_select and isinstance(answer, list):
                        # Handle each answer in the list
                        for single_answer in answer:
                            try:
                                # Try to find and click the option
                                option = self.driver.find_element(
                                    By.XPATH,
                                    f"//div[contains(@class, 'select__option') and contains(text(), '{single_answer}')]"
                                )
                                self.driver.execute_script("arguments[0].click();", option)
                                self._random_delay((0.5, 1))
                            except NoSuchElementException:
                                # If exact match not found, try partial match
                                options = self.driver.find_elements(
                                    By.XPATH,
                                    "//div[contains(@class, 'select__option')]"
                                )
                                for option in options:
                                    if single_answer.lower() in option.text.lower():
                                        self.driver.execute_script("arguments[0].click();", option)
                                        self._random_delay((0.5, 1))
                                        break
                    else:
                        # Handle single selection (original code)
                        try:
                            option = self.driver.find_element(
                                By.XPATH,
                                f"//div[contains(@class, 'select__option') and contains(text(), '{answer}')]"
                            )
                            self.driver.execute_script("arguments[0].click();", option)
                        except NoSuchElementException:
                            # If exact match not found, try partial match
                            options = self.driver.find_elements(
                                By.XPATH,
                                "//div[contains(@class, 'select__option')]"
                            )
                            for option in options:
                                if answer.lower() in option.text.lower():
                                    self.driver.execute_script("arguments[0].click();", option)
                                    break
                else:
                    # Handle traditional select
                    select = Select(field)

                    if is_multi_select and isinstance(answer, list):
                        # Handle multiple selections
                        for single_answer in answer:
                            try:
                                select.select_by_visible_text(single_answer)
                            except:
                                # Try to find a similar option
                                options = select.options
                                for option in options:
                                    if single_answer.lower() in option.text.lower():
                                        select.select_by_visible_text(option.text)
                                        break
                    else:
                        # Handle single selection (original code)
                        try:
                            select.select_by_visible_text(answer)
                        except:
                            # If no exact match, try to find a similar option
                            options = select.options
                            for option in options:
                                if answer.lower() in option.text.lower():
                                    select.select_by_visible_text(option.text)
                                    break

            elif field_type == "combobox":
                # Handle combobox inputs (like location)
                field = self.driver.find_element(By.ID, field_id)
                field.clear()
                field.send_keys(answer)
                self._random_delay((0.5, 1))

                # Try to select from dropdown if it appears
                try:
                    option = self.driver.find_element(
                        By.XPATH,
                        f"//div[contains(@class, 'select__option') and contains(text(), '{answer}')]"
                    )
                    self.driver.execute_script("arguments[0].click();", option)
                except NoSuchElementException:
                    # If no exact match in dropdown, just keep the typed value
                    pass

            elif field_type == "checkbox":
                # Handle checkboxes
                if answer.lower() in ['yes', 'true', '1']:
                    field = self.driver.find_element(By.ID, field_id)
                    if not field.is_selected():
                        field.click()
                else:
                    field = self.driver.find_element(By.ID, field_id)
                    if field.is_selected():
                        field.click()

            elif field_type == "radio":
                # Handle radio buttons
                radio_group = self.driver.find_elements(By.NAME, field_id)
                for radio in radio_group:
                    label_text = ""
                    try:
                        # Try to find the label text associated with this radio
                        label_id = radio.get_attribute("id")
                        if label_id:
                            label = self.driver.find_element(By.XPATH, f"//label[@for='{label_id}']")
                            label_text = label.text.strip().lower()
                    except:
                        pass

                    # Click the radio if its label matches our answer
                    if answer.lower() in label_text:
                        radio.click()
                        break

            elif field_type == "file":
                # Handle file uploads
                field = self.driver.find_element(By.ID, field_id)

                # Check if it's resume or cover letter
                if "resume" in field_id.lower():
                    # Use the specific resume file
                    resume_path = answer if answer and Path(answer).exists() else "Abdullah_Resume.pdf"
                    field.send_keys(str(Path(resume_path).absolute()))
                elif "cover_letter" in field_id.lower():
                    field.send_keys(str(Path("cover_letter.pdf").absolute()))
                elif answer:  # For any other file upload with a specified path
                    field.send_keys(str(Path(answer).absolute()))

            elif field_type == "textarea":
                # Handle text areas
                field = self.driver.find_element(By.ID, field_id)
                field.clear()
                field.send_keys(answer)

            # Check if field is required and not filled
            try:
                is_required = field.get_attribute("aria-required") == "true"
                is_invalid = field.get_attribute("aria-invalid") == "true"
                if is_required and is_invalid:
                    logger.warning(f"Required field {field_id} appears to be invalid after filling")
            except:
                pass

            logger.info(f"Filled field {field_id} of type {field_type} with answer")

        except Exception as e:
            logger.error(f"Error handling field {field_id}: {e}")

    def _handle_demographic_section(self, config: ApplicationConfig) -> None:
        """Handle the demographic questions section of the form.
        
        Args:
            config: Application configuration
        """
        try:
            # Handle Gender
            self._handle_greenhouse_form_field("4024662004", "select", config.gender)

            # Handle Gender Identity (new field)
            gender_identity = config.gender_identity if hasattr(config, 'gender_identity') else "Prefer not to say"
            self._handle_greenhouse_form_field("4024663004", "select", gender_identity)

            # Handle Pronouns (new field)
            pronouns = config.pronouns if hasattr(config, 'pronouns') else "Prefer not to say"
            self._handle_greenhouse_form_field("4024664004", "select", pronouns)

            # Handle Sexual Orientation (new field)
            sexual_orientation = config.sexual_orientation if hasattr(config,
                                                                      'sexual_orientation') else "Prefer not to say"
            self._handle_greenhouse_form_field("4024665004", "select", sexual_orientation)

            # Handle Hispanic/Latinx question (new field)
            hispanic_latinx = config.hispanic_latinx if hasattr(config, 'hispanic_latinx') else "Prefer not to say"
            self._handle_greenhouse_form_field("4024666004", "select", hispanic_latinx)

            # Handle Race/Ethnicity
            self._handle_greenhouse_form_field("4024667004", "select", config.ethnicity)

            # Handle Veteran Status
            self._handle_greenhouse_form_field("4024668004", "select", config.veteran_status)

            # Handle Disability Status
            self._handle_greenhouse_form_field("4024669004", "select", config.disability_status)

            logger.info("Completed demographic section")

        except Exception as e:
            logger.error(f"Error handling demographic section: {e}")

    def _handle_sony_specific_questions(self, config: ApplicationConfig) -> None:
        """Handle Sony-specific questions in the application form.
        
        Args:
            config: Application configuration
        """
        try:
            # Handle previous Sony employment
            self._handle_greenhouse_form_field("question_13103294004", "select",
                                               config.previous_employment if hasattr(config,
                                                                                     'previous_employment') else "No")

            # Handle relocation assistance
            self._handle_greenhouse_form_field("question_13103297004", "select",
                                               config.need_relocation if hasattr(config, 'need_relocation') else "Yes")

            # Handle certification checkbox
            self._handle_greenhouse_form_field("question_13103300004", "select", "Yes")

            logger.info("Completed Sony-specific questions")

        except Exception as e:
            logger.error(f"Error handling Sony-specific questions: {e}")


    def _handle_application_form(self, config: ApplicationConfig) -> bool:
        """Handle the Greenhouse application form.
        
        Args:
            config: Application configuration
            
        Returns:
            Boolean indicating if form was successfully submitted
        """
        # Store config for use in other methods
        self.current_config = config

        try:
            # Get the HTML content for analysis
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')

            # Find the application form
            form = soup.find('form', id='application-form')
            if not form:
                logger.warning("Application form not found, looking for apply button")
                apply_buttons = self.driver.find_elements(
                    By.XPATH,
                    "//a[contains(text(), 'Apply') or contains(@class, 'apply') or contains(@id, 'apply')]"
                )
                if apply_buttons:
                    self.driver.execute_script("arguments[0].click();", apply_buttons[0])
                    self._random_delay(self.RETRY_DELAY)
                    html_content = self.driver.page_source

            # Extract field information
            fields_info = self.form_analyzer.extract_form_fields(BeautifulSoup(html_content, 'html.parser'))

            # Log all extracted fields for debugging
            logger.info(f"Extracted fields from form:")
            for category, fields in fields_info.items():
                logger.info(f"  {category}: {len(fields)} fields")

            # Get resume data
            resume_data = self._extract_resume_data()

            # Fill basic info fields
            for field in fields_info.get("basic_info", []):
                field_id = field["id"]
                field_type = field["type"]

                if "first_name" in field_id:
                    self._handle_greenhouse_form_field(field_id, field_type, resume_data["first_name"])
                elif "last_name" in field_id:
                    self._handle_greenhouse_form_field(field_id, field_type, resume_data["last_name"])
                elif "email" in field_id:
                    self._handle_greenhouse_form_field(field_id, field_type, resume_data["email"])
                elif "phone" in field_id:
                    self._handle_greenhouse_form_field(field_id, field_type, resume_data["phone"])
                elif "location" in field_id or "address" in field_id:
                    self._handle_greenhouse_form_field(field_id, "combobox", config.current_city)

                self._random_delay((0.5, 1))

            # Handle resume upload
            for field in fields_info.get("resume_upload", []):
                field_id = field["id"]
                # Use the specific resume file path provided in the config
                self._handle_greenhouse_form_field(field_id, "file", "Abdullah_Resume.pdf")
                self._random_delay((0.5, 1))

            # Handle cover letter upload if needed
            for field in fields_info.get("cover_letter_upload", []):
                field_id = field["id"]
                job_title, job_description, hr_name = self._extract_job_details()
                cover_letter_path = self.generate_cover_letter(job_title, job_description, hr_name)
                self._handle_greenhouse_form_field(field_id, "file", cover_letter_path)
                self._random_delay((0.5, 1))

            # Handle Sony-specific questions
            self._handle_sony_specific_questions(config)
            self._random_delay((0.5, 1))

            # Handle technical questions with resume data
            self._handle_technical_questions(resume_data)
            self._random_delay((0.5, 1))

            # Handle demographic section if present
            if soup.find('div', id='demographic-section'):
                self._handle_demographic_section(config)
                self._random_delay((0.5, 1))

            # Handle education section if present
            education_container = soup.find('div', class_='education--container')
            if education_container:
                self._handle_education_section(soup, fields_info)
                self._random_delay((0.5, 1))

            # Handle custom questions
            for field in fields_info.get("custom_questions", []):
                field_id = field["id"]
                field_type = field["type"]
                label_text = field["label"]

                # Skip fields we've already handled in specific methods
                if field_id in ["question_13169191004", "question_13169192004", "question_13183961004",
                                "question_13183962004", "question_13183963004", "question_13183964004",
                                "question_13183965004", "question_13103294004", "question_13103297004",
                                "question_13103300004"]:
                    continue

                # Try to handle by label
                handled = False

                # Check for questions about LinkedIn or social profiles
                if "linkedin" in label_text.lower() or "social" in label_text.lower():
                    linkedin = self.resume_data_cache.get("contact", {}).get("linkedin",
                                                                             "") if self.resume_data_cache else ""
                    self._handle_greenhouse_form_field(field_id, field_type, linkedin)
                    handled = True

                # Check for questions about website or portfolio
                elif "website" in label_text.lower() or "portfolio" in label_text.lower():
                    github = self.resume_data_cache.get("contact", {}).get("github",
                                                                           "") if self.resume_data_cache else ""
                    self._handle_greenhouse_form_field(field_id, field_type, github)
                    handled = True

                # Check for questions about work authorization or visa
                elif "visa" in label_text.lower() or "sponsorship" in label_text.lower() or "authorized" in label_text.lower() or "legally" in label_text.lower():
                    self._handle_greenhouse_form_field(field_id, field_type,
                                                       "Yes" if config.require_sponsorship == "Yes" else "No")
                    handled = True

                # Check for questions about sources (how did you hear about us)
                elif "hear about" in label_text.lower() and field_type == "checkbox":
                    # Use the dedicated method for checkbox groups
                    self._handle_job_source_checkboxes(field_id)
                    handled = True

                # Check for questions about start date
                elif "start" in label_text.lower() or "available" in label_text.lower():
                    self._handle_greenhouse_form_field(field_id, field_type, config.start_date)
                    handled = True

                # Check for questions about compensation
                elif "compensation" in label_text.lower() or "salary" in label_text.lower():
                    self._handle_greenhouse_form_field(field_id, field_type, config.expected_compensation)
                    handled = True

                # Check for questions about metropolitan area location
                elif "metropolitan" in label_text.lower() or "west coast" in label_text.lower():
                    # Use dedicated handler
                    self._handle_metropolitan_area_question(field_id)
                    handled = True

                # Check for questions about education/degree
                elif "bachelor" in label_text.lower() or "degree" in label_text.lower() or "computer science" in label_text.lower():
                    self._handle_greenhouse_form_field(field_id, field_type, "Yes")
                    handled = True

                # Check for questions about programming experience
                elif "python" in label_text.lower():
                    self._handle_greenhouse_form_field(field_id, field_type, "Yes")
                    handled = True
                elif "c++" in label_text.lower():
                    self._handle_greenhouse_form_field(field_id, field_type, "No")
                    handled = True

                # Check for questions about remote work
                elif "remote" in label_text.lower():
                    self._handle_greenhouse_form_field(field_id, field_type,
                                                       "Yes" if config.remotely_available == "Yes" else "No")
                    handled = True

                # Check for questions about language proficiency
                elif "english" in label_text.lower():
                    self._handle_greenhouse_form_field(field_id, field_type, config.english_proficiency)
                    handled = True
                elif "german" in label_text.lower():
                    self._handle_greenhouse_form_field(field_id, field_type, config.german_proficiency)
                    handled = True

                # Check for questions about experience
                elif "experience" in label_text.lower():
                    self._handle_greenhouse_form_field(field_id, field_type, config.react_experience)
                    handled = True

                # Check for questions about family members or relatives
                elif "family" in label_text.lower() or "relative" in label_text.lower():
                    self._handle_greenhouse_form_field(field_id, field_type, "No")
                    handled = True

                # Check for questions about regulatory (FDA/OIG)
                elif "debarred" in label_text.lower() or "fda" in label_text.lower() or "oig" in label_text.lower():
                    self._handle_greenhouse_form_field(field_id, field_type, "No")
                    handled = True

                # If not handled by our patterns, use AI to generate an answer
                if not handled:
                    ai_answer = self._handle_unknown_field_with_ai(field_id, field_type, label_text)
                    self._handle_greenhouse_form_field(field_id, field_type, ai_answer)

                self._random_delay((0.5, 1))

            # Submit the form
            submit_button = self.driver.find_element(
                By.XPATH,
                "//button[@type='submit' or contains(@class, 'submit') or contains(text(), 'Submit')]"
            )
            self.driver.execute_script("arguments[0].click();", submit_button)
            self._random_delay(self.SUBMISSION_DELAY)

            # Check for errors or confirmation
            error_elements = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'error') or contains(@class, 'alert')]"
            )

            if error_elements:
                logger.warning("Form submission had errors, attempting to fix and resubmit")
                # Try to fix any invalid fields
                for error in error_elements:
                    try:
                        error_id = error.get_attribute("id")
                        if error_id:
                            field_id = error_id.replace("-error", "")
                            field = self.driver.find_element(By.ID, field_id)
                            field_type = field.get_attribute("type") or "select"

                            # Try to fix the field with AI assistance
                            label_elem = self.driver.find_element(By.XPATH, f"//label[@for='{field_id}']")
                            label_text = label_elem.text if label_elem else field_id
                            ai_answer = self._handle_unknown_field_with_ai(field_id, field_type, label_text)
                            self._handle_greenhouse_form_field(field_id, field_type, ai_answer)
                    except:
                        continue

                # Try submitting again
                submit_button = self.driver.find_element(
                    By.XPATH,
                    "//button[@type='submit' or contains(@class, 'submit') or contains(text(), 'Submit')]"
                )
                self.driver.execute_script("arguments[0].click();", submit_button)
                self._random_delay(self.SUBMISSION_DELAY)

            # Check for confirmation
            confirmation_elements = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'confirmation') or contains(@class, 'success') or contains(text(), 'Thank you')]"
            )

            if confirmation_elements:
                logger.info("Application submitted successfully")
                return True

            # If we can't confirm success or failure, assume success
            logger.info("Application appears to be submitted, but couldn't confirm")
            return True

        except Exception as e:
            logger.error(f"Error in handling application form: {e}")
            return False

    def apply_to_job(self, job_url: str, config: ApplicationConfig) -> bool:
        """Apply to a Greenhouse job.
        
        Args:
            job_url: URL of the job posting
            config: Application configuration
            
        Returns:
            Boolean indicating if application was successful
        """
        logger.info(f"Applying to Greenhouse job: {job_url}")

        # Check if already applied using utility function
        if is_already_applied(job_url):
            logger.info(f"Already applied for {job_url} (found in applied.txt). Skipping.")
            return False

        self.driver.get(job_url)
        self._random_delay((1, 3))

        # Check if already applied based on page content
        if self._is_already_applied():
            logger.info(f"Already applied for {job_url} (detected on page). Skipping.")
            record_applied_job(job_url)
            return False

        # Look for the apply button if not on application form
        if "boards.greenhouse.io" in job_url and "/apply/" not in job_url:
            # We're on a job listing page, not an application form
            apply_buttons = self.driver.find_elements(
                By.XPATH,
                "//a[contains(text(), 'Apply') or contains(@class, 'apply') or contains(@id, 'apply')]"
            )

            if apply_buttons:
                # Get the href from the apply button
                apply_url = apply_buttons[0].get_attribute("href")
                logger.info(f"Found apply URL: {apply_url}")

                if apply_url:
                    self.driver.get(apply_url)
                    self._random_delay((1, 3))
                else:
                    # Try clicking the button
                    self.driver.execute_script("arguments[0].click();", apply_buttons[0])
                    self._random_delay((1, 3))

        # Handle the application form
        success = self._handle_application_form(config)

        if success:
            # Record successful application
            record_applied_job(job_url)
            return True
        else:
            return False

    def login_and_apply_to_jobs(self, job_urls: List[str], config: ApplicationConfig) -> None:
        """Apply to multiple Greenhouse jobs.
        
        Args:
            job_urls: List of job URLs to apply to
            config: Application configuration
        """
        # Greenhouse doesn't typically require login for applications
        for job_url in job_urls:
            try:
                success = self.apply_to_job(job_url, config)
                if success:
                    logger.info(f"Successfully applied to {job_url}")
                    self._random_delay((10, 30))
            except Exception as e:
                logger.error(f"Failed to process {job_url}: {e}")
