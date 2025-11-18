import smtplib
import configparser
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(subject, plain_message, html_message, to_addr, file_path):
    """
    Send email notification with vehicle details
    
    Args:
        subject: Email subject line
        plain_message: Plain text message body
        html_message: HTML formatted message body
        to_addr: Recipient email address
        file_path: Path to file attachment
    """
    # Load email credentials from secrets.ini file
    config = configparser.ConfigParser()
    config.read('secrets.ini')
    
    from_addr = config.get('EMAIL', 'from_email')
    password = config.get('EMAIL', 'password')
    msg = MIMEMultipart('alternative')  # Use 'alternative' to support both plain and HTML content
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr

    # Attach plain text message
    part1 = MIMEText(plain_message, 'plain')
    msg.attach(part1)

    # Attach HTML message
    part2 = MIMEText(html_message, 'html')
    msg.attach(part2)

    # File attachment
    with open(file_path, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename={file_path}')
    msg.attach(part)

    # SMTP configuration
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(from_addr, password)
    server.send_message(msg)
    server.quit()


