import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
from dotenv import load_dotenv
load_dotenv()

msg = MIMEMultipart()
msg['Subject'] = "Interview Summary - John Doe"
msg['From'] = 'areendeshpande@gmail.com'
msg['To'] = 'areendeshpande@gmail.com'

with open(r"backend\sample.pdf", "rb") as file:
    part = MIMEApplication(file.read(), Name="report.pdf")
    part['Content-Disposition'] = 'attachment; filename="report.pdf"'
    msg.attach(part)

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    smtp.login('areendeshpande@gmail.com',os.getenv("GMAIL_PASS"))
    smtp.send_message(msg)
    print("Email sent successfully!")
