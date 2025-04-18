from pathlib import Path
import json
import logging
import random
import time
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

from playwright.async_api import async_playwright, Page, Browser, ElementHandle, Locator
from playwright_stealth import stealth_async

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("application.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GreenhouseHandler:
    """Handler for job applications on Greenhouse ATS."""

    MAX_RETRIES = 3
    RETRY_DELAY = (1, 3)  # Random delay range for retries
    SUBMISSION_DELAY = (2, 5)  # Random delay range after submission

    def __init__(self, resume_path: str, resume_data_path: str):
        """Initialize the Greenhouse handler.

        Args:
            resume_path: Path to the resume PDF file
            resume_data_path: Path to the resume data JSON file
        """
        self.resume_path = Path(resume_path).absolute()
        self.resume_data = self._load_resume_data(resume_data_path)
        self.playwright = None
        self.browser = None
        self.page = None
        
        # Default answers for diversity and equal opportunity questions
        self.diversity_answers = {
            "disability_status": "No, I do not have a disability and have not had one in the past",
            "veteran_status": "I am not a protected veteran",
            "gender": None,  # Leave as None to skip
            "ethnicity": None,  # Leave as None to skip
            "race": None,  # Leave as None to skip
            "hispanic_latino": None  # Leave as None to skip
        }

    def _load_resume_data(self, path: str) -> Dict[str, Any]:
        """Load resume data from JSON file.

        Args:
            path: Path to the JSON file

        Returns:
            Dictionary with resume data
        """
        with open(path, 'r') as f:
            return json.load(f)

    def _random_delay(self, delay_range: Tuple[float, float]) -> None:
        """Implement a random delay within the specified range.

        Args:
            delay_range: Tuple of (min_delay, max_delay) in seconds
        """
        time.sleep(random.uniform(*delay_range))
        
    async def _async_random_delay(self, delay_range: Tuple[float, float]) -> None:
        """Implement an async random delay within the specified range.

        Args:
            delay_range: Tuple of (min_delay, max_delay) in seconds
        """
        await asyncio.sleep(random.uniform(*delay_range))

    async def start_browser(self) -> None:
        """Start a new browser instance with anti-detection measures."""
        self.playwright = await async_playwright().start()
        
        # Configure browser launch options for stealth
        self.browser = await self.playwright.chromium.launch(
            headless=False,  # Set to True for production
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-web-security',
                '--disable-site-isolation-trials'
            ]
        )
        
        # List of common user agents
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15'
        ]
        
        # Create context with enhanced options
        context = await self.browser.new_context(
            user_agent=random.choice(user_agents),
            viewport={'width': random.randint(1280, 1920), 'height': random.randint(800, 1080)},
            device_scale_factor=random.choice([1, 2]),
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation'],
            java_script_enabled=True,
            bypass_csp=True,
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'sec-ch-ua': '"Google Chrome";v="107", "Chromium";v="107", "Not=A?Brand";v="24"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1'
            }
        )
        
        # Create page and apply stealth plugin
        self.page = await context.new_page()
        
        # Apply stealth mode to avoid detection
        await stealth_async(self.page)
        
        # Add random mouse movements and delays during navigation
        await self._setup_human_behavior()
        
        logger.info("Browser started with anti-detection measures")

    async def close_browser(self) -> None:
        """Close the browser instance."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def apply_to_job(self, job_url: str) -> bool:
        """Apply to a job on Greenhouse.
        
        Args:
            job_url: URL of the job posting
            
        Returns:
            Boolean indicating success or failure
        """
        try:
            logger.info(f"Applying to job at {job_url}")
            await self.page.goto(job_url)
            await self._async_random_delay((2, 4))

            # Check for CAPTCHA early
            if await self._handle_captcha():
                logger.warning("CAPTCHA detected during initial page load. Aborting application.")
                return False

            # Find and click the apply button
            apply_button = self.page.locator('a:has-text("Apply"), button:has-text("Apply")')
            
            if await apply_button.count() == 0:
                apply_button = self.page.locator('a:has-text("Apply for this job"), button:has-text("Apply for this job")')
            
            if await apply_button.count() == 0:
                logger.error("Apply button not found")
                return False

            await apply_button.first.click()
            await self._async_random_delay((2, 3))
            
            # Check for CAPTCHA after clicking apply
            if await self._handle_captcha():
                logger.warning("CAPTCHA detected after clicking Apply. Aborting application.")
                return False
            
            # Check if we need to navigate to a new page or if the form appeared on the same page
            form = self.page.locator('form#application_form')
            if await form.count() == 0:
                # If we're on a different page (some Greenhouse jobs open a new page for application)
                form = self.page.locator('form')
                if await form.count() == 0:
                    logger.error("Application form not found")
                    return False
                    
            # Fill in personal information
            logger.info("Filling personal information")
            await self._fill_personal_information()
            
            # Upload resume
            logger.info("Uploading resume")
            await self._upload_resume()
            
            # Fill in additional questions (custom fields)
            logger.info("Filling additional questions")
            await self._fill_additional_questions()
            
            # Fill in diversity questions if present
            logger.info("Filling diversity information")
            await self._fill_diversity_information()
            
            # Check for CAPTCHA before submission
            if await self._handle_captcha():
                logger.warning("CAPTCHA detected before submission. Aborting application.")
                return False
            
            # Submit the application
            logger.info("Submitting application")
            submit_button = self.page.locator('input[type="submit"], button[type="submit"]')
            
            # Sometimes there's a "Submit Application" button instead
            if await submit_button.count() == 0:
                submit_button = self.page.locator('button:has-text("Submit Application")')
            
            if await submit_button.count() == 0:
                logger.error("Submit button not found")
                return False
                
            # Wait a moment before submitting
            await self._async_random_delay((1, 2))
            
            # Uncomment the line below to actually submit the application
            # await submit_button.click()
            
            # For testing, we'll log but not submit
            logger.info("Would submit application here (submission click commented out for testing)")
            
            # Record successful application
            with open("applied.txt", "a") as f:
                f.write(f"{job_url}\n")
                
            return True
            
        except Exception as e:
            logger.error(f"Error applying to job at {job_url}: {e}")
            return False

    async def _fill_personal_information(self) -> None:
        """Fill in personal information fields."""
        try:
            # Map resume data to common field names in Greenhouse
            field_mapping = {
                'first_name': self.resume_data["name"].split()[0],
                'last_name': ' '.join(self.resume_data["name"].split()[1:]),
                'email': self.resume_data["contact"]["email"],
                'phone': self.resume_data["contact"]["phone"],
                'address': self.resume_data["contact"]["location"]
            }
            
            # Fill each field if it exists
            for field_id, value in field_mapping.items():
                # Try different selectors for each field
                selectors = [
                    f'#job_application_{field_id}',
                    f'input[name="{field_id}"]',
                    f'input[name="job_application[{field_id}]"]',
                    f'input[id="{field_id}"]',
                    f'input[placeholder*="{field_id}"]'
                ]
                
                for selector in selectors:
                    field = self.page.locator(selector)
                    if await field.count():
                        await field.fill(value)
                        await self._async_random_delay((0.5, 1))
                        break
                        
            # Handle LinkedIn field if present
            linkedin_selectors = [
                '#job_application_linkedin_url',
                'input[name="job_application[linkedin_url]"]',
                'input[name="linkedin_url"]',
                'input[id="linkedin_url"]'
            ]
            
            for selector in linkedin_selectors:
                linkedin_field = self.page.locator(selector)
                if await linkedin_field.count():
                    await linkedin_field.fill(self.resume_data["contact"].get("linkedin", ""))
                    await self._async_random_delay((0.5, 1))
                    break
                    
        except Exception as e:
            logger.error(f"Error filling personal information: {e}")

    async def _upload_resume(self) -> None:
        """Upload resume file to the application form."""
        try:
            # Try different selectors for resume upload
            resume_selectors = [
                'input[type="file"]#resume_upload',
                'input[type="file"][name="resume"]',
                'input[type="file"][name="job_application[resume]"]',
                'input[type="file"]'  # Last resort, grab any file input
            ]
            
            for selector in resume_selectors:
                file_input = self.page.locator(selector)
                if await file_input.count():
                    await file_input.set_input_files(str(self.resume_path))
                    logger.info(f"Uploaded resume from {self.resume_path}")
                    await self._async_random_delay((1, 2))
                    break
                    
        except Exception as e:
            logger.error(f"Error uploading resume: {e}")

    async def _fill_additional_questions(self) -> None:
        """Fill in additional questions on the application form."""
        try:
            # Process each question field on the form
            question_groups = self.page.locator('.question')
            
            if await question_groups.count() == 0:
                # Try alternative selectors if standard selector doesn't work
                question_groups = self.page.locator('.custom-field')
                
                if await question_groups.count() == 0:
                    # If still no questions found, look for form groups or labels
                    question_groups = self.page.locator('.form-group, .field')
            
            # Map common questions to answers
            question_keywords = {
                # Work authorization
                "authorized to work": "Yes",
                "legally authorized": "Yes",
                "require sponsorship": "Yes",
                "require visa sponsorship": "Yes",
                "require work authorization": "Yes",
                
                # Language proficiency
                "english proficiency": "Professional working proficiency",
                "fluent in english": "Yes",
                
                # Years of experience
                "years of experience": self._get_years_of_experience(),
                "years of professional experience": self._get_years_of_experience(),
                
                # Education
                "highest level of education": "Bachelor's Degree",
                
                # Salary
                "salary expectations": "Competitive market rate",
                "salary requirement": "Negotiable based on total package",
                
                # Notice period
                "notice period": "2 weeks",
                
                # Relocation
                "willing to relocate": "Yes",
                
                # Remote work
                "remote work": "Yes",
                "work remotely": "Yes",
                
                # Source
                "how did you hear about this": "Job search",
                "how did you find this": "Job search",
                
                # Cover letter (leaving blank for now)
                "cover letter": "",
                
                # References (usually handled later in the process)
                "references": "Available upon request"
            }
            
            # Process each question group
            for i in range(await question_groups.count()):
                question_group = await question_groups.nth(i).element_handle()
                label_text = await question_group.text_content()
                
                if not label_text:
                    continue
                    
                label_text = label_text.strip().lower()
                
                # See if this question has been filled already
                if await self._is_field_filled(question_group):
                    continue
                    
                # Find an answer to the question
                answer = None
                
                for keyword, ans in question_keywords.items():
                    if keyword.lower() in label_text.lower():
                        answer = ans
                        break
                        
                if answer:
                    await self._fill_question_field(question_group, answer)
                    await self._async_random_delay((0.5, 1.5))
                    
        except Exception as e:
            logger.error(f"Error filling additional questions: {e}")

    async def _fill_diversity_information(self) -> None:
        """Fill in diversity and equal opportunity information if present."""
        try:
            # Try to find diversity section
            diversity_section = self.page.locator('#diversity, .diversity-section, .equal-opportunity, section:has-text("Equal Opportunity")')
            
            if await diversity_section.count() == 0:
                return  # No diversity section found
                
            # Fill veteran status if field exists and we have an answer
            if self.diversity_answers["veteran_status"]:
                await self._handle_dropdown_field("veteran status", self.diversity_answers["veteran_status"])
                
            # Fill disability status if field exists and we have an answer
            if self.diversity_answers["disability_status"]:
                await self._handle_dropdown_field("disability status", self.diversity_answers["disability_status"])
                
            # Fill gender if field exists and we have an answer
            if self.diversity_answers["gender"]:
                await self._handle_dropdown_field("gender", self.diversity_answers["gender"])
                
            # Fill race/ethnicity if fields exist and we have answers
            if self.diversity_answers["ethnicity"]:
                await self._handle_dropdown_field("ethnicity", self.diversity_answers["ethnicity"])
                
            if self.diversity_answers["race"]:
                await self._handle_dropdown_field("race", self.diversity_answers["race"])
                
            if self.diversity_answers["hispanic_latino"]:
                await self._handle_dropdown_field("hispanic or latino", self.diversity_answers["hispanic_latino"])
                
        except Exception as e:
            logger.error(f"Error filling diversity information: {e}")

    async def _handle_dropdown_field(self, field_label: str, value: str) -> None:
        """Handle selecting an option in a dropdown field.
        
        Args:
            field_label: The label text of the field
            value: The value to select
        """
        try:
            # Find select fields that match the label
            field_groups = self.page.locator('.field, .form-group, .question')
            
            for i in range(await field_groups.count()):
                field_group = await field_groups.nth(i).element_handle()
                label_text = await field_group.text_content()
                
                if not label_text or field_label.lower() not in label_text.lower():
                    continue
                    
                # Try to find a select element
                select_element = await field_group.query_selector('select')
                if select_element:
                    # Get options and try to find a match
                    options = await select_element.query_selector_all('option')
                    option_value = None
                    
                    for option in options:
                        option_text = await option.text_content()
                        if not option_text:
                            continue
                            
                        if value.lower() in option_text.lower():
                            option_value = await option.get_attribute('value')
                            break
                            
                    if option_value:
                        # Use the page locator to find and select the option
                        select_id = await select_element.get_attribute('id')
                        if select_id:
                            selector = f'#{select_id}'
                        else:
                            # Without an ID, try using the name attribute
                            select_name = await select_element.get_attribute('name')
                            selector = f'select[name="{select_name}"]'
                            
                        # Use the page context to select the option
                        dropdown = self.page.locator(selector)
                        if await dropdown.count():
                            await dropdown.select_option(value=option_value)
                            logger.info(f"Selected '{value}' for '{field_label}'")
                            return
                    
                # If no select element or couldn't find matching option, try radio buttons
                radio_labels = await field_group.query_selector_all('label')
                
                for radio_label in radio_labels:
                    radio_text = await radio_label.text_content()
                    if not radio_text:
                        continue
                        
                    if value.lower() in radio_text.lower():
                        # Try to find the associated radio button
                        radio = await radio_label.query_selector('input[type="radio"]')
                        if radio:
                            await radio.click()
                            logger.info(f"Selected radio '{value}' for '{field_label}'")
                            return
                        else:
                            # If no direct child, the radio might have an ID referenced by the label's 'for' attribute
                            for_attr = await radio_label.get_attribute('for')
                            if for_attr:
                                radio = await field_group.query_selector(f'input[type="radio"]#{for_attr}')
                                if radio:
                                    await radio.click()
                                    logger.info(f"Selected radio '{value}' for '{field_label}'")
                                    return
        except Exception as e:
            logger.error(f"Error handling dropdown field '{field_label}': {e}")

    async def _is_field_filled(self, field_group: ElementHandle) -> bool:
        """Check if a field has already been filled.
        
        Args:
            field_group: The field group element
            
        Returns:
            Boolean indicating if the field is already filled
        """
        try:
            # Check text inputs
            text_inputs = await field_group.query_selector_all('input[type="text"], input[type="email"], input[type="tel"]')
            for text_input in text_inputs:
                value = await text_input.get_attribute('value')
                if value and value.strip():
                    return True
                    
            # Check textarea
            textareas = await field_group.query_selector_all('textarea')
            for textarea in textareas:
                value = await textarea.get_attribute('value')
                if value and value.strip():
                    return True
                    
            # Check radio buttons and checkboxes
            checked = await field_group.query_selector('input[type="radio"]:checked, input[type="checkbox"]:checked')
            if checked:
                return True
                
            # Check selects
            selects = await field_group.query_selector_all('select')
            for select in selects:
                value = await select.get_attribute('value')
                if value and value != '':
                    return True
                    
            return False
            
        except Exception:
            # If we can't determine, assume it's not filled
            return False

    async def _fill_question_field(self, question_group: ElementHandle, answer: str) -> None:
        """Fill a question field with the appropriate answer.
        
        Args:
            question_group: The question field group
            answer: The answer to fill in
        """
        try:
            # Check if there's a text input
            text_input = await question_group.query_selector('input[type="text"], input[type="email"], input[type="tel"]')
            if text_input:
                await text_input.fill(answer)
                return
                
            # Check if there's a textarea
            textarea = await question_group.query_selector('textarea')
            if textarea:
                await textarea.fill(answer)
                return
                
            # Check if there are radio buttons
            radio_labels = await question_group.query_selector_all('label')
            for radio_label in radio_labels:
                radio_text = await radio_label.text_content()
                if not radio_text:
                    continue
                    
                # If the answer is Yes/No, look for matching labels
                if answer.lower() == "yes" and any(text in radio_text.lower() for text in ["yes", "agree"]):
                    radio = await radio_label.query_selector('input[type="radio"]')
                    if radio:
                        await radio.click()
                        return
                    else:
                        # If no direct child, the radio might have an ID referenced by the label's 'for' attribute
                        for_attr = await radio_label.get_attribute('for')
                        if for_attr:
                            radio = await question_group.query_selector(f'input[type="radio"]#{for_attr}')
                            if radio:
                                await radio.click()
                                return
                                
                elif answer.lower() == "no" and any(text in radio_text.lower() for text in ["no", "disagree"]):
                    radio = await radio_label.query_selector('input[type="radio"]')
                    if radio:
                        await radio.click()
                        return
                    else:
                        # If no direct child, the radio might have an ID referenced by the label's 'for' attribute
                        for_attr = await radio_label.get_attribute('for')
                        if for_attr:
                            radio = await question_group.query_selector(f'input[type="radio"]#{for_attr}')
                            if radio:
                                await radio.click()
                                return
                                
            # Check if there's a select element
            select_element = await question_group.query_selector('select')
            if select_element:
                options = await select_element.query_selector_all('option')
                option_value = None
                
                for option in options:
                    option_text = await option.text_content()
                    if not option_text:
                        continue
                        
                    if answer.lower() in option_text.lower():
                        option_value = await option.get_attribute('value')
                        break
                        
                if option_value:
                    await select_element.select_option(value=option_value)
                    return
                    
        except Exception as e:
            logger.error(f"Error filling question field: {e}")

    def _get_years_of_experience(self) -> str:
        """Calculate years of experience from resume.
        
        Returns:
            String with years of experience
        """
        try:
            total_months = 0
            
            for job in self.resume_data["experience"]:
                # Check if dates are present
                if "dates" not in job:
                    continue
                    
                dates = job["dates"]
                
                # Parse start year and end year
                if "–" in dates:
                    start_year = int(dates.split("–")[0].strip().split()[-1])
                    end_year = dates.split("–")[1].strip()
                    end_year = 2024 if end_year.lower() == "present" else int(end_year.split()[-1])
                    
                    total_months += (end_year - start_year) * 12
                    
            years = total_months // 12
            return f"{years}+ years"
            
        except Exception:
            # Default to a reasonable value if we can't calculate
            return "5+ years"

    def set_diversity_answers(self, 
                              disability_status: Optional[str] = None,
                              veteran_status: Optional[str] = None, 
                              gender: Optional[str] = None,
                              ethnicity: Optional[str] = None,
                              hispanic_latino: Optional[str] = None) -> None:
        """Set diversity answers for EEO sections.
        
        Args:
            disability_status: Disability status option
            veteran_status: Veteran status option
            gender: Gender option
            ethnicity: Ethnicity option
            hispanic_latino: Hispanic/Latino option
        """
        if disability_status:
            self.diversity_answers["disability_status"] = disability_status
            
        if veteran_status:
            self.diversity_answers["veteran_status"] = veteran_status
            
        if gender:
            self.diversity_answers["gender"] = gender
            
        if ethnicity:
            self.diversity_answers["ethnicity"] = ethnicity
            
        if hispanic_latino:
            self.diversity_answers["hispanic_latino"] = hispanic_latino

    async def __aenter__(self):
        """Start browser when entering async context."""
        await self.start_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close browser when exiting async context."""
        await self.close_browser()

    async def _setup_human_behavior(self) -> None:
        """Setup event handlers to simulate human-like behavior."""
        
        # Add random delay before navigation
        orig_goto = self.page.goto
        async def goto_with_delay(*args, **kwargs):
            await self._async_random_delay((1, 3))
            return await orig_goto(*args, **kwargs)
        self.page.goto = goto_with_delay
        
        # Add random delay after clicking
        orig_click = self.page.click
        async def click_with_delay(*args, **kwargs):
            result = await orig_click(*args, **kwargs)
            await self._async_random_delay((0.5, 2))
            return result
        self.page.click = click_with_delay 

    async def _handle_captcha(self) -> bool:
        """Check if a CAPTCHA is present and handle it.
        
        Returns:
            Boolean indicating if CAPTCHA was detected
        """
        # Check for common CAPTCHA indicators
        captcha_selectors = [
            'iframe[src*="recaptcha"]',
            'iframe[src*="captcha"]',
            'div.g-recaptcha',
            'div.h-captcha',
            'form[action*="validateCaptcha"]',
            'div[class*="captcha"]',
            'input[name*="captcha"]',
            'img[alt*="captcha" i]',
            'div:has-text("Verify you are human")',
            'div:has-text("unusual traffic")',
            'div:has-text("suspicious activity")'
        ]
        
        for selector in captcha_selectors:
            element = await self.page.query_selector(selector)
            if element:
                logger.warning(f"CAPTCHA detected using selector: {selector}")
                
                # Take a screenshot for debugging
                try:
                    await self.page.screenshot(path=f"captcha_detected_{int(time.time())}.png")
                    logger.info("Saved CAPTCHA screenshot")
                except Exception as e:
                    logger.error(f"Failed to save CAPTCHA screenshot: {e}")
                
                # Here we can implement CAPTCHA solving if using a service
                # For now, we'll just return that we detected it
                return True
                
        return False 