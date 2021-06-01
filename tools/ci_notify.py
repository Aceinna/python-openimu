import os
import platform
import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

try:
    from aceinna import VERSION
except:  # pylint: disable=bare-except
    sys.path.append('./src')
    from aceinna import VERSION

SYS = platform.system()
SENDER = os.environ['EMAIL_ADDRESS']
RECEIVERS = ['ywsong@aceinna.com']
PASSWORD = os.environ['EMAIL_PASSWORD']

MESSAGE = MIMEMultipart()
MESSAGE['From'] = Header("notifications@aceinna.com", 'utf-8')
MESSAGE['To'] = ";".join(RECEIVERS)
SUBJECT = '[{0}] CI Executable'.format(SYS)
MESSAGE['Subject'] = Header(SUBJECT, 'utf-8')

MESSAGE.attach(
    MIMEText('<p>[Inceptio Branch] Built executable on {0}</p><p>Version: {1}</p>'.format(SYS, VERSION), 'html', 'utf-8'))

FILE_NAME = 'ans-devices.exe' if SYS == "Windows" else 'ans-devices'

ATTACHMENT = MIMEText(open(os.path.join(os.getcwd(), 'dist', FILE_NAME),
                           'rb').read(), 'base64', 'utf-8')
ATTACHMENT["Content-Type"] = 'application/octet-stream'
ATTACHMENT["Content-Disposition"] = 'attachment; filename="{0}"'.format(
    FILE_NAME)
MESSAGE.attach(ATTACHMENT)

try:
    smtp_client = smtplib.SMTP('smtp.office365.com', 587)
    smtp_client.ehlo()
    smtp_client.starttls()
    smtp_client.login(SENDER, PASSWORD)
    smtp_client.sendmail(SENDER, RECEIVERS, MESSAGE.as_string())
except smtplib.SMTPException as error:
    print(error)