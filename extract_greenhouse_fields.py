import requests
from bs4 import BeautifulSoup
import logging
import json
import re
import os
import time
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class GreenhouseFormAnalyzer:
    """Analyzes Greenhouse job application forms to identify all fields."""
    
    def __init__(self, user_agent: str = None):
        """Initialize the analyzer with custom headers."""
        self.headers = {
            'User-Agent': user_agent or 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
    
    def fetch_job_page(self, url: str) -> str:
        """Fetch the HTML content of a job page."""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching job page: {e}")
            return ""
    
    def find_apply_link(self, soup: BeautifulSoup, base_url: str) -> str:
        """Find the 'Apply' button link in a job listing."""
        apply_buttons = soup.find_all(['a', 'button'], string=re.compile(r'apply', re.I))
        
        for button in apply_buttons:
            logger.info(f"Found apply button: {button.get_text(strip=True)}")
            
            if button.name == 'a':
                href = button.get('href')
                if href:
                    logger.info(f"Apply link found: {href}")
                    
                    # Construct full URL if it's a relative path
                    if not href.startswith(('http://', 'https://')):
                        full_url = f"{base_url.rstrip('/')}/{href.lstrip('/')}"
                        logger.info(f"Full apply URL: {full_url}")
                        return full_url
                    return href
        
        return ""
    
    def extract_form_fields(self, soup: BeautifulSoup) -> Dict[str, List[Dict[str, Any]]]:
        """Extract all form fields from the application form."""
        form = soup.find('form', id='application_form')
        if not form:
            form = soup.find('form')
        
        if not form:
            logger.warning("No application form found on the page")
            return {}
        
        fields = {
            "basic_info": [],
            "resume_upload": [],
            "cover_letter_upload": [],
            "custom_questions": [],
            "demographic_questions": []
        }
        
        # Extract standard fields (name, email, phone, location)
        for field_id in ['first_name', 'last_name', 'email', 'phone', 'candidate-location']:
            field = form.find('input', id=field_id)
            if field:
                label_elem = form.find('label', attrs={'for': field_id})
                label_text = label_elem.get_text(strip=True) if label_elem else field_id
                
                # Check if it's required
                required = False
                if label_elem:
                    required = '*' in label_elem.get_text() or label_elem.get('aria-required') == 'true'
                
                fields["basic_info"].append({
                    'id': field_id,
                    'name': field.get('name', ''),
                    'type': field.get('type', 'text'),
                    'label': label_text,
                    'required': required
                })
        
        # Extract file upload fields (resume, cover letter)
        resume_input = form.find('input', id='resume')
        if resume_input:
            upload_label = form.find('div', id='upload-label-resume')
            label_text = upload_label.get_text(strip=True) if upload_label else "Resume/CV"
            
            fields["resume_upload"].append({
                'id': 'resume',
                'type': 'file',
                'label': label_text,
                'required': True if upload_label and '*' in upload_label.get_text() else False,
                'accept': resume_input.get('accept', '')
            })
        
        cover_letter_input = form.find('input', id='cover_letter')
        if cover_letter_input:
            upload_label = form.find('div', id='upload-label-cover_letter')
            label_text = upload_label.get_text(strip=True) if upload_label else "Cover Letter"
            
            fields["cover_letter_upload"].append({
                'id': 'cover_letter',
                'type': 'file',
                'label': label_text,
                'required': True if upload_label and '*' in upload_label.get_text() else False,
                'accept': cover_letter_input.get('accept', '')
            })
        
        # Extract custom questions (typically with question_* ids)
        custom_questions = form.find_all('label', id=re.compile(r'question_\d+-label'))
        for label_elem in custom_questions:
            question_id = label_elem.get('for')
            
            if not question_id:
                continue
                
            field_elem = form.find(['input', 'select', 'textarea'], id=question_id)
            if not field_elem:
                continue
                
            field_type = 'text'
            if field_elem.name == 'select':
                field_type = 'select'
            elif field_elem.name == 'textarea':
                field_type = 'textarea'
            elif field_elem.get('type'):
                field_type = field_elem.get('type')
                
            # Check if it's required
            required = '*' in label_elem.get_text() or field_elem.get('aria-required') == 'true'
            
            fields["custom_questions"].append({
                'id': question_id,
                'type': field_type,
                'label': label_elem.get_text(strip=True).replace('*', ''),
                'required': required
            })
        
        # Extract demographic questions
        demographic_section = form.find('div', id='demographic-section')
        if demographic_section:
            demographic_labels = demographic_section.find_all('label')
            for label_elem in demographic_labels:
                question_id = label_elem.get('for')
                
                if not question_id:
                    continue
                    
                field_elem = form.find(['input', 'select'], id=question_id)
                if not field_elem:
                    continue
                    
                field_type = 'text'
                if field_elem.name == 'select':
                    field_type = 'select'
                elif field_elem.get('type'):
                    field_type = field_elem.get('type')
                    
                # Demographic questions are typically optional
                required = '*' in label_elem.get_text() or field_elem.get('aria-required') == 'true'
                
                fields["demographic_questions"].append({
                    'id': question_id,
                    'type': field_type,
                    'label': label_elem.get_text(strip=True).replace('*', ''),
                    'required': required
                })
        
        return fields
    
    def analyze_job_url(self, url: str, save_json: bool = True) -> Dict[str, Any]:
        """Analyze a job URL and extract form fields."""
        logger.info(f"Analyzing job URL: {url}")
        
        # Extract base URL for resolving relative links
        base_url_parts = url.split('/')
        if len(base_url_parts) >= 3:
            base_url = '/'.join(base_url_parts[:3])
        else:
            base_url = url
        
        # Fetch the page
        html_content = self.fetch_job_page(url)
        if not html_content:
            logger.error("Failed to fetch job page")
            return {}
        
        # Parse HTML
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Check if it's a job listing or application page
        apply_form = soup.find('form', id='application_form')
        
        # If it's not an application form, look for the apply button
        if not apply_form:
            logger.info("This is a job listing page, not an application form")
            apply_link = self.find_apply_link(soup, base_url)
            
            if apply_link:
                logger.info(f"Found apply link: {apply_link}")
                # Follow the apply link to get to the application form
                html_content = self.fetch_job_page(apply_link)
                if not html_content:
                    logger.error("Failed to fetch application form page")
                    return {}
                    
                # Re-parse HTML
                soup = BeautifulSoup(html_content, 'lxml')
        
        # Extract form fields
        fields = self.extract_form_fields(soup)
        
        # Count fields
        total_fields = sum(len(field_list) for field_list in fields.values())
        logger.info(f"Found {total_fields} form fields in total")
        
        for category, field_list in fields.items():
            logger.info(f"Found {len(field_list)} {category.replace('_', ' ')} fields")
        
        # Generate results
        results = {
            "url": url,
            "fields": fields,
            "total_fields": total_fields,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save to JSON file
        if save_json:
            filename = f"greenhouse_fields_{int(time.time())}.json"
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Saved field information to {filename}")
        
        return results

if __name__ == "__main__":
    # Sample Greenhouse job URLs to analyze
    job_urls = [
        "https://boards.greenhouse.io/greenthumbindustries/jobs/6665900",      # Green Thumb job
        "https://job-boards.greenhouse.io/greenthumbindustries/jobs/6665900",  # Alternative format
        "https://boards.greenhouse.io/dbtlabs/jobs/4301536"                    # Another company job
    ]
    
    analyzer = GreenhouseFormAnalyzer()
    
    for url in job_urls:
        logger.info("\n" + "="*80)
        analyzer.analyze_job_url(url) 