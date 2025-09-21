import os
from datetime import datetime, timedelta, timezone
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


def send_report_email(db, report_pdf, candidate_name: str = 'Candidate', recipient_email: str = 'piyushkrishna11@gmail.com') -> bool:
    try:
        email_id = f"{candidate_name.lower().replace(' ', '_')}_{int(datetime.now().timestamp())}"
        existing_email = db.sent_emails.find_one({
            'candidate_name': candidate_name,
            'recipient': recipient_email,
            'sent_at': {'$gt': datetime.now(timezone.utc) - timedelta(hours=1)}
        })
        if existing_email:
            return True

        msg = MIMEMultipart()
        msg['Subject'] = f"Interview Assessment Report - {candidate_name}"
        msg['From'] = 'piyushkrishna11@gmail.com'
        msg['To'] = recipient_email
        msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
        msg['Message-ID'] = f"<{email_id}@assessai.com>"

        body = f"""
Dear Hiring Manager,

Please find attached the comprehensive interview assessment report for {candidate_name}.

Best regards,
Lsoys Apps & Games
AI Interviewer System
"""
        msg.attach(MIMEText(body, 'plain'))

        if report_pdf:
            part = MIMEApplication(report_pdf.getvalue(), Name=f"{candidate_name}_Interview_Report.pdf")
            part['Content-Disposition'] = f'attachment; filename="{candidate_name}_Interview_Report.pdf"'
            msg.attach(part)

        gmail_password = os.getenv('GMAIL_PASS')
        if not gmail_password:
            return False

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login('piyushkrishna11@gmail.com', gmail_password)
            smtp.send_message(msg)
            db.sent_emails.insert_one({
                'candidate_name': candidate_name,
                'recipient': recipient_email,
                'subject': f"Interview Assessment Report - {candidate_name}",
                'sent_at': datetime.now(timezone.utc),
                'email_id': email_id
            })
        return True
    except Exception:
        return False


