__author__ = "Tao Zhang"
__copyright__ = "Copyright 2019, The VIX short Strategy"
__email__ = "uncczhangtao@yahoo.com"
import smtplib
from email.mime.multipart import MIMEMultipart  # 构建邮件头信息，包括发件人，接收人，标题等
from email.mime.text import MIMEText  # 构建邮件正文，可以是text，也可以是HTML
from email.mime.application import MIMEApplication  # 构建邮件附件，理论上，只要是文件即可，一般是图片，Excel表格，word文件等
from email.header import Header  # 专门构建邮件标题的，这样做，可以支持标题中文

class EmailNotification(object):

    @classmethod
    def send_email(cls, recipient,
                   subject,
                   body,
                   sender='short.vix.notification@gmail.com',
                   pwd=''):
        FROM = sender
        TO = recipient if isinstance(recipient, list) else [recipient]

        # Prepare actual message
        # 邮件头信息
        msg = MIMEMultipart('related')
        msg['Subject'] = Header(subject)
        msg["From"] = sender
        msg['To'] = ','.join(TO)  # 这里要注意

        # html 内容
        content_html = MIMEText(body, "html", "utf-8")

        msg.attach(content_html)

        try:
            # SMTP_SSL Example
            server_ssl = smtplib.SMTP_SSL("smtp.gmail.com", 465)
            server_ssl.ehlo()  # optional, called by login()
            server_ssl.login(sender, pwd)
            # ssl server doesn't support or need tls, so don't call server_ssl.starttls()
            server_ssl.sendmail(FROM, TO, msg.as_string())
            # server_ssl.quit()
            server_ssl.close()
            print('successfully sent the mail to {0}'.format(recipient))
        except Exception as ex:
            # TODO if failed try another account and resend
            print("failed to send mail")
            print(str(ex))

    @classmethod
    def covert_df_to_html(cls, df):
        HEADER = '''
        <html>
            <head>

            </head>
            <body>
        '''
        FOOTER = '''
            </body>
        </html>
        '''

        body = HEADER + df.to_html(classes='df', index=False) + FOOTER

        return body



