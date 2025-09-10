from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
import io


def get_status_color(status: str) -> str:
    status = (status or '').lower()
    if 'selected' in status:
        return '#4CAF50'
    if 'next round' in status:
        return '#2196F3'
    if 'rejected' in status:
        return '#F44336'
    if 'not good' in status:
        return '#FF9800'
    if 'good in another role' in status:
        return '#9C27B0'
    return '#757575'


def create_pdf_report(report_content: str, candidate_name: str = 'Candidate', status: str = 'Pending Review', score: str = 'N/A'):
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            title=f"Interview Report - {candidate_name}",
            author="Lsoys Apps & Games - AI Interviewer System",
            subject="Interview Assessment"
        )

        if score == 'N/A' and 'SCORE:' in report_content:
            score_line = [line for line in report_content.split('\n') if 'SCORE:' in line]
            if score_line:
                try:
                    score = score_line[0].split('SCORE:')[1].strip()
                except Exception:
                    score = 'N/A'

        styles = getSampleStyleSheet()
        company_style = ParagraphStyle('CompanyHeader', parent=styles['Heading1'], fontSize=16, alignment=1, textColor='#1A237E', fontName='Helvetica-Bold', spaceAfter=6)
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=18, spaceAfter=5, alignment=1, textColor='#1A237E')
        subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=14, alignment=1, spaceAfter=10)
        status_style = ParagraphStyle('StatusStyle', parent=styles['Heading2'], fontSize=12, alignment=1, textColor='white', backColor=get_status_color(status), borderWidth=1, borderColor='#333333', borderPadding=5, borderRadius=4, spaceAfter=10)
        score_style = ParagraphStyle('ScoreStyle', parent=styles['Heading2'], fontSize=14, alignment=1, textColor='#333333', spaceAfter=5)
        date_style = ParagraphStyle('DateStyle', parent=styles['Normal'], fontSize=10, alignment=1, textColor='#666666', spaceAfter=15)
        heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=14, spaceBefore=12, spaceAfter=8, textColor='#283593', borderWidth=0, borderColor='#C5CAE9', borderPadding=5, borderRadius=2)
        subheading_style = ParagraphStyle('CustomSubheading', parent=styles['Heading3'], fontSize=12, spaceAfter=8, textColor='#303F9F')
        body_style = ParagraphStyle('CustomBody', parent=styles['Normal'], fontSize=10, spaceAfter=12, alignment=TA_JUSTIFY, leading=14)
        question_style = ParagraphStyle('QuestionStyle', parent=styles['Normal'], fontSize=11, fontName='Helvetica-Bold', spaceAfter=2, textColor='#1A237E', leftIndent=10)
        answer_style = ParagraphStyle('AnswerStyle', parent=styles['Normal'], fontSize=10, spaceAfter=12, leftIndent=20, leading=14)
        footer_style = ParagraphStyle('FooterStyle', parent=styles['Normal'], fontSize=8, alignment=1, textColor='#666666')

        story = []
        story.append(Paragraph('LSOYS APPS & GAMES', company_style))
        story.append(Paragraph('INTERVIEW ASSESSMENT REPORT', title_style))
        story.append(Paragraph(f'Candidate: {candidate_name}', subtitle_style))
        story.append(Paragraph(f'Status: {status}', status_style))
        story.append(Paragraph(f'SCORE: {score}', score_style))
        current_time = datetime.now().strftime('%B %d, %Y at %H:%M')
        story.append(Paragraph(f'Generated on: {current_time}', date_style))
        story.append(Spacer(1, 10))

        sections = report_content.split('\n')
        in_qa_section = False
        skip_score_section = False
        for section in sections:
            if not section.strip():
                story.append(Spacer(1, 6))
                continue
            if 'SCORE:' in section:
                skip_score_section = True
                continue
            if skip_score_section and section.strip() and not section.strip().isupper():
                skip_score_section = False
            if skip_score_section:
                continue
            if 'INTERVIEW QUESTIONS & ANSWERS' in section:
                in_qa_section = True
                story.append(Spacer(1, 10))
                story.append(Paragraph(section.strip(), heading_style))
                story.append(Spacer(1, 10))
                continue
            if in_qa_section:
                if section.strip().startswith('Question'):
                    story.append(Paragraph(section.strip(), question_style))
                elif section.strip().startswith('Response:'):
                    story.append(Paragraph(section.strip(), answer_style))
            elif section.strip().isupper() and len(section.strip()) < 50:
                story.append(Spacer(1, 10))
                story.append(Paragraph(section.strip(), heading_style))
                story.append(Spacer(1, 5))
            else:
                story.append(Paragraph(section.strip(), body_style))

        story.append(Spacer(1, 20))
        story.append(Spacer(1, 10))
        story.append(Paragraph('Generated by AI Interviewer | www.lsoysappsandgames.com/ai-interviewer', footer_style))

        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception:
        return None


