"""
Greenhouse.io specific implementation of the job application bot.
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import json
import logging
import re

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
                # Handle dropdown selects
                field = self.driver.find_element(By.ID, field_id)
                select = Select(field)
                
                # Try to find option by visible text or by value
                try:
                    select.select_by_visible_text(answer)
                except:
                    # If no exact match, try to find a similar option
                    options = select.options
                    for option in options:
                        if answer.lower() in option.text.lower():
                            select.select_by_visible_text(option.text)
                            break
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
                # In Greenhouse, radio buttons usually have labels after them
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
                    if answer.lower() in label_text or (answer.lower() == 'yes' and 'yes' in label_text):
                        radio.click()
                        break
            elif field_type == "file" and "resume" in field_id.lower():
                # Handle resume upload
                field = self.driver.find_element(By.ID, field_id)
                # Assuming resume is stored at "resume.pdf"
                field.send_keys(str(Path("resume.pdf").absolute()))
            elif field_type == "file" and "cover_letter" in field_id.lower():
                # Handle cover letter upload
                field = self.driver.find_element(By.ID, field_id)
                field.send_keys(str(Path("cover_letter.pdf").absolute()))
            elif field_type == "textarea":
                # Handle text areas
                field = self.driver.find_element(By.ID, field_id)
                field.clear()
                field.send_keys(answer)
                
            logger.info(f"Filled field {field_id} of type {field_type} with answer")
        except Exception as e:
            logger.error(f"Error handling field {field_id}: {e}")

    def _map_config_to_greenhouse_fields(self, config: ApplicationConfig) -> Dict[str, str]:
        """Map application config to Greenhouse field types.
        
        Args:
            config: Application configuration
            
        Returns:
            Dictionary mapping field types to answers
        """
        # Common field mappings for Greenhouse
        return {
            "first_name": "FIRST_NAME_FROM_RESUME",  # Will need to extract from resume
            "last_name": "LAST_NAME_FROM_RESUME",  # Will need to extract from resume
            "email": "EMAIL_FROM_RESUME",  # Will need to extract from resume
            "phone": "PHONE_FROM_RESUME",  # Will need to extract from resume
            "location": config.current_city,
            "visa": "Yes" if config.require_sponsorship == "Yes" else "No",
            "start_date": config.start_date,
            "salary": config.expected_compensation,
            "remote": "Yes" if config.remotely_available == "Yes" else "No",
            "experience": config.react_experience,
            "english": config.english_proficiency,
            "german": config.german_proficiency,
            "skills": ", ".join(config.skills),
        }

    def _handle_field_by_label(self, label_text: str, answer: str) -> bool:
        """Handle a form field based on its label text.
        
        Args:
            label_text: The label text of the field
            answer: The answer to fill in
            
        Returns:
            Boolean indicating if the field was handled
        """
        # Common label patterns in Greenhouse forms
        label_patterns = {
            "name": "first_name, last_name",
            "first name": "first_name",
            "last name": "last_name",
            "email": "email",
            "phone": "phone",
            "location": "location, current_city",
            "address": "location",
            "city": "current_city",
            "authorized to work": "visa, require_sponsorship",
            "legally authorized": "visa, require_sponsorship",
            "require visa sponsorship": "visa, require_sponsorship",
            "require sponsorship": "visa, require_sponsorship",
            "work remotely": "remote, remotely_available",
            "start date": "start_date",
            "when can you start": "start_date",
            "availability": "start_date",
            "salary": "salary, expected_compensation",
            "compensation": "salary, expected_compensation",
            "english proficiency": "english, english_proficiency",
            "proficiency in english": "english, english_proficiency",
            "german proficiency": "german, german_proficiency",
            "proficiency in german": "german, german_proficiency",
            "years of experience": "experience, react_experience",
            "work experience": "experience, react_experience",
        }
        
        for pattern, field_keys in label_patterns.items():
            if pattern in label_text.lower():
                field_key_list = [k.strip() for k in field_keys.split(",")]
                for field_key in field_key_list:
                    # Try to map the field and answer
                    field_mapping = self._map_config_to_greenhouse_fields(self.current_config)
                    if field_key in field_mapping:
                        return True
                
        return False

    def _extract_resume_data(self) -> Dict[str, str]:
        """Extract basic information from resume.json.
        
        Returns:
            Dictionary with basic resume info
        """
        try:
            with open('resume.json', 'r') as file:
                resume_data = json.load(file)
                
            info = {
                "first_name": resume_data["name"].split()[0] if resume_data.get("name") else "",
                "last_name": resume_data["name"].split()[-1] if resume_data.get("name") else "",
                "email": resume_data.get("contact", {}).get("email", ""),
                "phone": resume_data.get("contact", {}).get("phone", ""),
            }
            return info
        except Exception as e:
            logger.error(f"Error extracting resume data: {e}")
            return {
                "first_name": "",
                "last_name": "",
                "email": "",
                "phone": "",
            }

    def _handle_application_form(self, config: ApplicationConfig) -> bool:
        """Handle the Greenhouse application form.
        
        Args:
            config: Application configuration
            
        Returns:
            Boolean indicating if form was successfully submitted
        """
        # Store config for use in other methods
        self.current_config = config
        
        # Extract form fields using the analyzer
        try:
            # Try to get the HTML content for analysis
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            form = soup.find('form', id='application_form')
            if not form:
                logger.warning("Application form not found, looking for apply button")
                # Try to find and click the apply button
                apply_buttons = self.driver.find_elements(
                    By.XPATH, 
                    "//a[contains(text(), 'Apply') or contains(@class, 'apply') or contains(@id, 'apply')]"
                )
                if apply_buttons:
                    self.driver.execute_script("arguments[0].click();", apply_buttons[0])
                    self._random_delay(self.RETRY_DELAY)
                    
                    # Get updated page source
                    html_content = self.driver.page_source
            
            # Use the analyzer to extract field information
            fields_info = self.form_analyzer.extract_form_fields(BeautifulSoup(html_content, 'html.parser'))
            
            # Get resume data for filling personal info
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
                    self._handle_greenhouse_form_field(field_id, field_type, config.current_city)
                
                self._random_delay((0.5, 1))
            
            # Handle resume upload
            for field in fields_info.get("resume_upload", []):
                field_id = field["id"]
                self._handle_greenhouse_form_field(field_id, "file", "")
                self._random_delay((0.5, 1))
            
            # Handle cover letter upload if needed
            for field in fields_info.get("cover_letter_upload", []):
                field_id = field["id"]
                # Make sure we have a cover letter generated
                job_title, job_description, hr_name = self._extract_job_details()
                cover_letter_path = self.generate_cover_letter(job_title, job_description, hr_name)
                self._handle_greenhouse_form_field(field_id, "file", cover_letter_path)
                self._random_delay((0.5, 1))
            
            # Handle custom questions
            for field in fields_info.get("custom_questions", []):
                field_id = field["id"]
                field_type = field["type"]
                label_text = field["label"]
                
                # Try to handle by label
                handled = False
                
                # Check for questions about work authorization or visa
                if "visa" in label_text.lower() or "sponsorship" in label_text.lower() or "authorized" in label_text.lower():
                    self._handle_greenhouse_form_field(field_id, field_type, "Yes" if config.require_sponsorship == "Yes" else "No")
                    handled = True
                
                # Check for questions about start date
                elif "start" in label_text.lower() or "available" in label_text.lower():
                    self._handle_greenhouse_form_field(field_id, field_type, config.start_date)
                    handled = True
                
                # Check for questions about compensation
                elif "compensation" in label_text.lower() or "salary" in label_text.lower():
                    self._handle_greenhouse_form_field(field_id, field_type, config.expected_compensation)
                    handled = True
                
                # Check for questions about remote work
                elif "remote" in label_text.lower():
                    self._handle_greenhouse_form_field(field_id, field_type, "Yes" if config.remotely_available == "Yes" else "No")
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
                
                # If not handled by our patterns, try to use a default answer
                if not handled:
                    if field_type == "text" or field_type == "textarea":
                        self._handle_greenhouse_form_field(field_id, field_type, "Please see my resume for details")
                    elif field_type == "select":
                        # For selects, we'll need to find a suitable option
                        pass
                    elif field_type == "checkbox" or field_type == "radio":
                        # For checkboxes, choose a sensible default (usually 'yes' is better)
                        self._handle_greenhouse_form_field(field_id, field_type, "Yes")
                
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
                # Handle errors and try again (simplified for now)
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