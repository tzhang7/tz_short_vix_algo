__author__ = "Tao Zhang"
__copyright__ = "Copyright 2019, The VIX short Strategy"
__email__ = "uncczhangtao@yahoo.com"

from config import user_config
import smtplib

class EmailNotification(object):

    @classmethod
    def send_email(cls, recipient,
                   subject,
                   body,
                   user=user_config.email_sender['account'],
                   pwd=user_config.email_sender['pwd']):
        FROM = user
        TO = recipient if isinstance(recipient, list) else [recipient]
        SUBJECT = subject
        TEXT = body

        # Prepare actual message
        message = """From: %s\nTo: %s\nSubject: %s\n\n%s
        """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
        try:
            # SMTP_SSL Example
            server_ssl = smtplib.SMTP_SSL("smtp.gmail.com", 465)
            server_ssl.ehlo()  # optional, called by login()
            server_ssl.login(user, pwd)
            # ssl server doesn't support or need tls, so don't call server_ssl.starttls()
            server_ssl.sendmail(FROM, TO, message)
            # server_ssl.quit()
            server_ssl.close()
            print('successfully sent the mail')
        except Exception as ex:
            # TODO if failed try another account and resend
            print("failed to send mail")
            print(str(ex))



