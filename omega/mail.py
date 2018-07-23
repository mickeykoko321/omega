import email.mime.multipart
import email.mime.text
import logging
import smtplib


def send_email(subject, body, receiver, text_only=False):
    """Function to send an email using the account Ticker Central (which was created for another application)

    :param subject: Email subject
    :param body: Body of the email
    :param receiver: Email destination
    :param text_only: Set to true if the format of the email if for text only (or plain)
    """
    log = logging.getLogger(__name__)

    try:
        log.debug('Create email')
        sender = 'tickercentral@gmail.com'
        # Create message container - the correct MIME type is multipart/alternative.
        msg = email.mime.multipart.MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = receiver
        # Create the body of the message (a plain-test and an HTML version).
        text = body
        html = """\
        <html>
            <head></head>
            <body>
                <p>
                    """ + body + """
                </p>
            </body>
        </htm>
        """
        # Record the MIME types of both parts - text/plain and text/html.
        part1 = email.mime.text.MIMEText(text, 'plain')
        part2 = email.mime.text.MIMEText(html, 'html')
        # Attach parts into message container
        msg.attach(part1)
        if not text_only:
            msg.attach(part2)
        # Send the message
        s = smtplib.SMTP('smtp.gmail.com:587')
        s.ehlo()
        s.starttls()
        s.login(sender, 'T1ckerCentral!')
        s.sendmail(sender, receiver, msg.as_string())
        s.quit()
        log.debug('Successfully send email!')
    except smtplib.SMTPException as ex:
        log.error('Unable to send email: {}'.format(ex), exc_info=True)


