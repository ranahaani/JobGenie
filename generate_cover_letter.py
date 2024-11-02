from fpdf import FPDF
from dotenv import load_dotenv
import os
import json
import google.generativeai as genai


class CoverLetterGenerator:
    def __init__(self):
        load_dotenv()
        self.openai_api_key = os.getenv("GEMINI_API_KEY")

        # Load resume from resume.json
        with open('resume.json', 'r') as file:
            resume_data = json.load(file)
        self.resume_text = self._convert_resume_to_text(resume_data)

        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def _convert_resume_to_text(self, resume_data):
        resume_text = f"Name: {resume_data['name']}\n"
        resume_text += f"Location: {resume_data['contact']['location']}\n"
        resume_text += f"Phone: {resume_data['contact']['phone']}\n"
        resume_text += f"Email: {resume_data['contact']['email']}\n"
        resume_text += f"GitHub: {resume_data['contact']['github']}\n"
        resume_text += f"LinkedIn: {resume_data['contact']['linkedin']}\n\n"

        resume_text += "Experience:\n"
        for experience in resume_data['experience']:
            resume_text += f"- {experience['position']} at {experience['company']} ({experience['dates']})\n"
            for responsibility in experience['responsibilities']:
                resume_text += f"  * {responsibility}\n"
            resume_text += "\n"

        resume_text += "Projects:\n"
        for project in resume_data['projects']:
            resume_text += f"- {project['name']} ({project['dates']}): {project['description']}\n"
        resume_text += "\n"

        resume_text += "Education:\n"
        education = resume_data['education']
        resume_text += f"- {education['degree']} from {education['institution']} ({education['dates']})\n"
        resume_text += f"  * CGPA: {education['cgpa']}\n"
        for achievement in education['achievements']:
            resume_text += f"  * {achievement}\n"
        resume_text += "\n"

        resume_text += "Skills:\n"
        for category, skills in resume_data['skills'].items():
            resume_text += f"- {category.capitalize()}: {', '.join(skills)}\n"

        return resume_text

    def generate_cover_letter(self, job_description, job_title, hr_name):
        prompt = (
            "Create a concise, job-winning cover letter for a [specific job title] role. "
            "Use the following job description and resume text to highlight my relevant skills and achievements. "
            "Structure the letter in three to four lines, with a human-like tone that conveys enthusiasm and professionalism. "
            "If the HR contact name is provided, start with their name; otherwise, begin with 'HR Manager.' "
            "Conclude with 'Best regards,' followed by my name. "
            "Format the letter in markdown so it is ready to be converted to PDF without further changes. "
            "Replace the values of vars in the square bracket i.e [Job Title].\n"
            "Only output the cover letter text in markdown format.\n\n"
            f"Job Description:\n{job_description}\n\n"
            f"Resume:\n{self.resume_text}\n\n"
            f"HR Name:\n{hr_name}\n\n"
            f"Job Title:\n{job_title}\n\n"
            "Example Output:\n\n"
            "Dear [HR Name or 'HR Manager'],\n\n"
            "I'm excited to apply for the [Job Title] position, where my background in **[relevant field/experience]** "
            "and skills in **[specific skills]** align with your needs at [Company Name]. "
            "Having achieved [notable achievement or relevant experience] and with a commitment to [specific job goal "
            "or value]\n\n"
            "Best regards,\n"
            "[Your Name]"
        )
        response = self.model.generate_content(prompt)
        cover_letter_text = response.text
        return cover_letter_text

    def save_cover_letter_as_pdf(self, cover_letter_text, file_name="cover_letter.pdf"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        with open('resume.json', 'r', encoding='utf-8') as file:
            resume_data = json.load(file)

        contact_info = resume_data['contact']

        pdf.cell(0, 10, f"Email: {contact_info['email']}", ln=True)
        pdf.cell(0, 10, f"Phone: {contact_info['phone']}", ln=True)
        pdf.cell(0, 10, f"Location: {contact_info['location']}", ln=True)
        pdf.cell(0, 10, f"GitHub: {contact_info['github']}", ln=True)
        pdf.cell(0, 10, f"LinkedIn: {contact_info['linkedin']}", ln=True)

        pdf.set_xy(10, 80)
        pdf.multi_cell(0, 10, cover_letter_text.encode('latin-1', 'replace').decode('latin-1'))

        pdf.output(file_name, 'F')
