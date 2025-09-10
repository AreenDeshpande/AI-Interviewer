import os
from typing import List, Optional
import openai


openai.api_key = os.getenv('OPENAI_API_KEY')


def parse_resume_with_openai(resume_text: str) -> Optional[str]:
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": (
                    "Extract key information from the resume.\n"
                    "Focus on: 1) skills 2) experience 3) education 4) achievements.\n"
                    "Return a structured summary."
                )},
                {"role": "user", "content": f"Parse this resume and extract key information:\n\n{resume_text}"}
            ],
            temperature=0.3,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None


def generate_interview_questions(resume_text: str) -> List[str]:
    try:
        resume_data = parse_resume_with_openai(resume_text)
        if not resume_data:
            raise RuntimeError("Failed to parse resume")

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": (
                    "You are an expert technical interviewer. Based on the resume info, "
                    "generate 2 specific technical questions. Return ONLY an array of 2 questions."
                )},
                {"role": "user", "content": f"Generate questions based on this:\n\n{resume_data}"}
            ],
            temperature=0.7,
            max_tokens=200
        )
        questions = response.choices[0].message.content.strip().split('\n')
        questions = [q.strip().lstrip('1234567890.- ') for q in questions if q.strip()]
        if len(questions) > 2:
            questions = questions[:2]
        while len(questions) < 2:
            questions.append("Tell me about your most challenging technical project and how you overcame it.")
        return questions
    except Exception:
        return [
            "Tell me about your most challenging technical project and how you overcame it.",
            "What technical skills are you most proud of and why?"
        ]


def generate_interview_report(interview_data: dict) -> str:
    try:
        questions = interview_data.get('questions', [])
        responses = interview_data.get('responses', [])
        qa_pairs = []
        for i, question in enumerate(questions):
            response = next((r for r in responses if r.get('question_index') == i), None)
            answer = response.get('transcription', 'No response recorded') if response else 'No response recorded'
            if isinstance(answer, str) and answer.startswith('Error during Whisper transcription'):
                answer = 'No valid response recorded'
            qa_pairs.append(f"Q{i+1}: {question}\nA{i+1}: {answer}")
        interview_text = "\n\n".join(qa_pairs)

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": (
                    "You are an expert interview assessor. Provide a comprehensive evaluation with sections: "
                    "OVERVIEW, STRENGTHS, IMPROVEMENTS, TECHNICAL, COMMUNICATION, RECOMMENDATION, SCORE."
                )},
                {"role": "user", "content": f"Analyze this interview and provide a detailed report:\n\n{interview_text}"}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "INTERVIEW ASSESSMENT REPORT\n\nUnable to perform automated analysis. Manual review required."


