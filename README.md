# Job Application Bot

This project is a Python-based automation tool designed to search for job listings and apply to them automatically. It uses Selenium for web automation and integrates with Anti-Captcha services to solve CAPTCHAs during the application process.

## Features

- **Automated Job Search**: Searches for job listings on Google using specified queries.
- **CAPTCHA Solving**: Utilizes Anti-Captcha services to solve CAPTCHAs encountered during the application process.
- **Automated Job Application**: Automatically fills out and submits job application forms on specified websites.

## Requirements

- Python 3.x
- Selenium
- WebDriver Manager for Chrome
- Anti-Captcha Official Python Library
- Google Search Python Library

## Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Install the required packages**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your environment**:
   - Ensure you have a valid Anti-Captcha API key.
   - Update the `cookies.json` file with your session cookies for the target job application site.
   - Update the `config.json` file with your personal application details such as start date, expected compensation, and other relevant information.

## Usage

1. **Run the bot**:
   ```bash
   python main.py
   ```

2. **Customize your job search**:
   - Modify the `job_search_query` variable in `main.py` to change the job search criteria.

## Important Notes

- Ensure that your `cookies.json` file is up-to-date with valid session cookies to avoid login issues.
- The bot is configured to work with job listings on `join.com`. Modify the code if you wish to target other websites.
- Make sure your `config.json` file is correctly filled out to ensure accurate application submissions.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.
