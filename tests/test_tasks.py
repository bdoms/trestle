import base64
import json
import logging

from _base import BaseTestCase, UCHAR
from config.constants import SENDER_EMAIL
from tasks import EmailTask


class TestTasks(BaseTestCase):

    def test_email(self):

        logger = logging.getLogger('tornado.application')
        orig_info = logger.info
        self.message = ''

        def info(message):
            self.message = message

        logger.info = info

        data = {
            'to': 'test' + UCHAR + '@example.com',
            'subject': 'Subject' + UCHAR,
            'html': '<p>Test body' + UCHAR + '</p>'
        }
        EmailTask.sendEmail(data, debug=True)

        assert self.message['sender'] == SENDER_EMAIL
        assert self.message['to'] == data['to']
        assert self.message['subject'] == data['subject']
        assert self.message['html'] == data['html']
        assert self.message['body'] == 'Test body' + UCHAR # plaintext non-html version
        assert not self.message.get('reply_to')
        assert not self.message.get('attachments')

        raw_content = b'content'
        content = base64.b64encode(raw_content).decode()
        cid = 'content-id'
        filename = 'file.ext'
        attachments = [{'content': content, 'content_id': cid, 'filename': filename, 'type': 'mime/type'}]
        data['attachments'] = json.dumps(attachments)
        data['reply_to'] = 'test.reply' + UCHAR + '@example.com'
        EmailTask.sendEmail(data, debug=True)

        assert self.message['sender'] == SENDER_EMAIL
        assert self.message['to'] == data['to']
        assert self.message['subject'] == data['subject']
        assert self.message['html'] == data['html']
        assert self.message['body'] == 'Test body' + UCHAR # plaintext non-html version
        assert self.message.get('reply_to') == data['reply_to']

        assert len(self.message.get('attachments', [])) == 1
        original = self.message['attachments'][0]
        assert raw_content in original
        assert cid in original
        assert filename in original

        logger.info = orig_info
