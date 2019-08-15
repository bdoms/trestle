import base64
import json
import logging
import urllib.error

from config.constants import SENDGRID_API_KEY, SENDER_EMAIL
import helpers

import sendgrid
from sendgrid.helpers import mail as sgmail
from tornado import gen
from tornado.queues import Queue


class TaskConsumer(object):

    LOGGER = logging.getLogger('tornado.application')

    TASKQ = Queue()

    @classmethod
    async def consumer(cls, debug=False):
        async for item in cls.TASKQ:
            # NOTE: sleeping is required to allow for context shifting away from this
            await gen.sleep(.001)
            try:
                # cls.LOGGER.info('Doing work on %s' % item)
                callback = item.pop('callback')
                callback(item, debug=debug)
            finally:
                cls.TASKQ.task_done()


class Task(object):

    LOGGER = logging.getLogger('tornado.application')


class EmailTask(Task):

    SENDGRID = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)

    @classmethod
    def sendEmail(cls, params, debug=False):
        to = params['to']
        subject = params['subject']
        html = params['html']
        attachments_json = params.get('attachments')
        reply_to = params.get('reply_to')

        # make to a list if it isn't already
        if isinstance(to, str):
            to = [to]

        body = helpers.strip_html(html)

        # attachments had to be encoded to send properly, so we decode them here
        attachments = attachments_json and json.loads(attachments_json) or None

        message = sgmail.Mail()
        message.from_email = sgmail.Email(SENDER_EMAIL)
        message.subject = subject

        if attachments:
            for data in attachments:
                attachment = sgmail.Attachment()
                attachment.content = base64.b64decode(data['content'])
                attachment.content_id = data['content_id']
                attachment.disposition = data.get('disposition', 'inline') # 'attachment' for non-embedded
                attachment.filename = data['filename']
                attachment.type = data['type']
                message.add_attachment(attachment)

        # NOTE that plain must come first
        message.add_content(sgmail.Content('text/plain', body))
        message.add_content(sgmail.Content('text/html', html))

        personalization = sgmail.Personalization()
        for to_email in to:
            personalization.add_to(sgmail.Email(to_email))
        message.add_personalization(personalization)

        if reply_to:
            message.reply_to = sgmail.Email(reply_to)

        if not debug:
            # an error here logs the status code but not the message
            # which is way more helpful, so we get it manually
            try:
                cls.SENDGRID.client.mail.send.post(request_body=message.get())
            except urllib.error.HTTPError as e:
                cls.LOGGER.error(e.read())
        else:
            kwargs = {
                'sender': SENDER_EMAIL,
                'subject': subject,
                'body': body,
                'html': html
            }

            if attachments:
                mail_attachments = []
                for data in attachments:
                    mail_attachment = [data['filename'], base64.b64decode(data['content']), data['content_id']]
                    mail_attachments.append(mail_attachment)
                kwargs['attachments'] = mail_attachments

            if reply_to:
                kwargs['reply_to'] = reply_to

            for to_email in to:
                kwargs['to'] = to_email
                cls.LOGGER.info(kwargs)
