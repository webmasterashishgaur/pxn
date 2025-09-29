"""
methods.py

This page is used to write reusable methods.

"""

from recruitment.models import Recruitment, RecruitmentSurvey
import os
from groq import Groq
import logging
import json


def is_stagemanager(request):
    """
    This method is used to check stage manager, if the employee is also
    recruitment manager it returns true
    """
    try:
        employee = request.user.employee_get
        return employee.recruitment_set.exists() or employee.stage_set.exists()
    except Exception:
        return False


def is_recruitmentmanager(request):
    """
    This method is used to check the employee is recruitment manager or not
    """
    try:
        employee = request.user.employee_get
        return employee.recruitment_set.exists()
    except Exception:
        return False


def stage_manages(request, stage):
    """
    This method is used to check the employee manager to this stage."""
    try:
        employee = request.user.employee_get

        return (
            stage.stage_manager.filter(id=employee.id).exists()
            or stage.recruitment_id.recruitment_managers.filter(id=employee.id).exists()
        )
    except Exception:
        return False


def recruitment_manages(request, recruitment):
    """
    This method is used to check the employee is manager to the current recruitment
    """
    try:
        employee = request.user.employee_get
        return recruitment.recruitment_managers.filter(id=employee.id).exists()
    except Exception:
        return False


def update_rec_template_grp(upt_template_ids, template_groups, rec_id):
    recruitment_obj = Recruitment.objects.get(id=rec_id)
    if list(upt_template_ids) != list(template_groups):
        recruitment_surveys = RecruitmentSurvey.objects.filter(recruitment_ids=rec_id)
        if recruitment_surveys:
            for survey in recruitment_surveys:
                survey.recruitment_ids.remove(rec_id)
                survey.save()
        if upt_template_ids:
            rec_surveys_templates = RecruitmentSurvey.objects.filter(
                template_id__in=upt_template_ids
            )
            for survey in rec_surveys_templates:
                survey.recruitment_ids.add(recruitment_obj)

def parse_resume_with_groq(resume_text, model="meta-llama/llama-4-scout-17b-16e-instruct"):
    """
    Calls Llama 4 via Groq to extract structured resume details from resume_text.
    Returns a dict with keys: education, skills, experience, certifications, summary.
    """
    prompt = (
        "You are an expert resume parser."
        "Your task is to extract resume data from the input text."
        "The output JSON should match the structure and detail level of the sample resume below."
        "If a field is missing in the resume text, return it as null or an empty list."
        "Do NOT infer or invent any data; only extract what is explicitly present."

        "\n\n--- SAMPLE STRUCTURE ---\n"
        "1. summary: Professional summary as detailed bullet points (not just a single paragraph).\n"
        "2. education: List of degrees, institutions, and years (if available). Each entry should be:\n"
        "   - degree: string\n"
        "   - institution: string\n"
        "   - year: string or null\n"
        "3. experience: List of jobs. For each job, extract:\n"
        "   - title: job title\n"
        "   - company: company name\n"
        "   - location: location (if mentioned)\n"
        "   - start_date: month/year or year if available\n"
        "   - end_date: month/year or year if available\n"
        "   - responsibilities: list of detailed bullet points showing actual duties and tasks\n"
        "4. certifications: List of certifications as found\n"
        "5. skills: List of skills (as present in the resume)\n"

        "IMPORTANT: For every job, extract all bullet points or listed responsibilities.\n"
        "If a section or field is missing, return it as null or empty list.\n"
        "Your output must be: a single JSON object with keys: summary, education, experience, certifications, skills.\n"

        "\nReturn ONLY JSON, without any additional explanation or text.\n"

        "\n--- Resume text follows ---\n"
        + resume_text
    )
    try:
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            model=model,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        logging.exception("Groq LLM resume parsing failed")
        return None

