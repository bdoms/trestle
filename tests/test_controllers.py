import json
import logging
from datetime import timedelta
from urllib.parse import urlencode

from tornado.httputil import HTTPServerRequest
from tornado.testing import AsyncHTTPTestCase
from tornado import web

from _base import BaseTestCase, UCHAR # _base import MUST come before model import to set up test DB properly
from controllers import _base as controller_base
import model

# needed to log in properly
HEADERS = {'User-Agent': 'Test Python UA'}


class BaseTestController(BaseTestCase, AsyncHTTPTestCase):

    def get_app(self):
        from main import makeApp
        return makeApp(debug=True, autoreload=False, level=logging.CRITICAL)

    def setUp(self):
        BaseTestCase.setUp(self)
        AsyncHTTPTestCase.setUp(self)
        # this must be imported after the above setup in order for the stubs to work
        self.controller_base = controller_base

    def fetch(self, *args, **kwargs):
        assert ' ' not in args[0], 'Unescaped space in URL'

        # having to manually open and close a db connection when writing tests would be a pain
        # but the controllers manage their own connection and they're called from the same process
        # so we go through the trouble of overwriting this method to manage the connection automatically
        model.peewee_db.close()

        # network_interface gets passed through and eventually mapped directly to remote_ip on the request object
        # but there are also some fallback headers that would achieve the same thing, e.g. X-Forwarded-For
        headers = kwargs.pop('headers', HEADERS.copy())
        if hasattr(self, 'cookies'):
            headers['Cookie'] = '; '.join([key + '=' + value for key, value in self.cookies.items()])
        kwargs['headers'] = headers

        # split up redirects here to capture the cookie after the first one
        response = AsyncHTTPTestCase.fetch(self, *args, network_interface='127.0.0.1',
            follow_redirects=False, **kwargs)
        self.setCookie(response)
        redirect = response.headers.get('Location')

        if redirect:
            # cookie might have been updated since last request in setCookie call above
            if hasattr(self, 'cookies'):
                headers['Cookie'] = '; '.join([key + '=' + value for key, value in self.cookies.items()])
            kwargs['headers'] = headers

            # never POSTing twice in a row
            kwargs['method'] = 'GET'
            kwargs['body'] = None

            response = AsyncHTTPTestCase.fetch(self, redirect, network_interface='127.0.0.1',
                follow_redirects=True, **kwargs)

        model.peewee_db.connect()
        response.body_string = response.body.decode() # for convenience
        return response

    def setCookie(self, response):
        if 'Set-Cookie' in response.headers:
            cookies = {}
            if hasattr(self, 'cookies'):
                cookies = self.cookies

            response_cookies = response.headers.get_list('Set-Cookie')
            for cookie in response_cookies:
                if ';' in cookie:
                    pair, remainder = cookie.split(';', 1)
                    if '=' in pair:
                        key, value = pair.strip().split('=', 1)
                        cookies[key] = value

            self.cookies = cookies

    def sessionGet(self, *args, **kwargs):
        # properly sets cookies for the session to work so that it doesn't have to be done every time
        response = self.fetch(*args, **kwargs)
        if response.code == 200:
            self.prior_response = response
            self.setCookie(response)
        return response

    def sessionPost(self, *args, **kwargs):
        # properly sets cookies for the session to work so that it doesn't have to be done every time
        args = list(args) # convert from tuple so we can modify below
        data = args[1]

        # note: you must send both the cookie, and the token somehow (header or body should both work)
        token = self.getXsrf(args[0])
        headers = kwargs.pop('headers', HEADERS.copy())
        headers['X-XSRFToken'] = token

        data = urlencode(data)
        headers['Content-Type'] = 'application/x-www-form-urlencoded'

        # data = json.dumps(data)
        # headers['Content-Type'] = 'application/json'

        response = self.fetch(args[0], method='POST', body=data, headers=headers, **kwargs)
        return response

    def getXsrf(self, url):
        if hasattr(self, 'prior_response') and self.prior_response:
            response = self.prior_response
            self.prior_response = None
        else:
            response = self.fetch(url)
            assert response.code == 200
            self.setCookie(response)

        value_split = response.body_string.split('name="_xsrf" value="', 1)[1]
        return value_split.split('"', 1)[0]

    def login(self, user=None):
        if not user and hasattr(self, "user"):
            user = self.user
        assert user, "A user is required to sign in."
        return self.sessionPost('/user/login', {'email': user.email, 'password': user.password})

    def logout(self):
        self.sessionGet('/home')
        response = self.sessionPost('/user/logout', {})
        self.prior_response = None
        self.cookies = {}
        return response


class BaseMockController(BaseTestController):
    """ abstract base class for tests that need request, response, and session mocking """

    def getMockRequest(self):
        class MockConnection(object):
            def finish(self):
                pass

            def set_close_callback(self, callback):
                pass

            def write_headers(self, start_line, headers, chunk, callback=None):
                pass

        return HTTPServerRequest(uri='/test-path', connection=MockConnection())

    def mockSessions(self):
        # this is used by tests that want to bypass needing to perform session-dependent actions within a request
        self.controller.session = {}
        self.controller.orig_session = {}

    def mockLogin(self):
        self.auth = self.createAuth(self.user)
        self.controller.session["auth_key"] = self.auth.slug


class TestBase(BaseMockController):

    def setUp(self):
        super(TestBase, self).setUp()

        self.controller = self.controller_base.BaseController(self._app, self.getMockRequest())

    def test_prepare(self):

        # these get set by tornado and we depend on them, so add in some blank fixtures here
        self.controller.path_args = []
        self.controller.path_kwargs = {}

        def before():
            self.called = True

        self.controller.before = before

        # before should be called if it exists
        self.called = False
        model.peewee_db.close()
        self.controller.prepare()
        assert self.called

        # if there is an error or redirect in before then the request should be finished
        model.peewee_db.close()
        self.controller.set_status(500)
        try:
            self.controller.prepare()
        except web.Finish:
            pass
        else:
            assert False

    def test_saveSession(self):

        # sessions can only be used during a request, so we prepare for one
        model.peewee_db.close()
        self.controller.prepare()

        def set_secure_cookie(name, data, **kwargs):
            self.name = name
            self.data = data

        self.name = self.data = None
        self.controller.set_secure_cookie = set_secure_cookie
        self.controller.session["test key"] = "test value" + UCHAR
        self.controller.saveSession()
        assert self.name == 'session'
        assert self.data == json.dumps({"test key": "test value" + UCHAR})

    def test_logger(self):
        logger = self.controller.logger
        assert logger

    def test_flash(self):
        self.mockSessions()
        self.controller.flash("test flash" + UCHAR)
        assert self.controller.session.get("flash") == {"level": "info", "message": "test flash" + UCHAR}

    def test_compileTemplate(self):
        self.mockSessions()
        result = self.controller.compileTemplate('index.html')
        assert b'<h2>Index Page</h2>' in result

    def test_securityHeaders(self):
        assert not self.controller._headers.get('Content-Security-Policy')
        self.controller.securityHeaders()
        assert '/policyviolation' in self.controller._headers.get('Content-Security-Policy', '')

    def test_renderTemplate(self):
        self.mockSessions()
        self.controller.renderTemplate('index.html')
        assert self.controller._headers['Content-Type'] == "text/html; charset=UTF-8"
        found = False
        for part in self.controller._write_buffer:
            if b'<h2>Index Page</h2>' in part:
                found = True
                break
        assert found

        # a HEAD request should not actually render anything, but the type should still be there
        self.controller._write_buffer = []
        self.controller.request.method = 'HEAD'
        self.controller.renderTemplate('index.html')
        assert self.controller._headers['Content-Type'] == "text/html; charset=UTF-8"
        assert not self.controller._write_buffer

    def test_renderError(self):
        self.mockSessions()
        self.controller.renderError(500)
        found = False
        for part in self.controller._write_buffer:
            if b"Error 500:" in part:
                found = True
                break
        assert found

    def test_renderJSON(self):
        self.mockSessions()
        data = {"test key": "test value" + UCHAR}
        self.controller.renderJSON(data)
        assert self.controller._headers['Content-Type'] == "application/json; charset=UTF-8"
        found = False
        for part in self.controller._write_buffer:
            if b'{"test key": "test value\\u03b4"}' in part:
                found = True
                break
        assert found

        # a HEAD request should not actually render anything, but the type should still be there
        self.controller._write_buffer = []
        self.controller.request.method = 'HEAD'
        self.controller.renderJSON(data)

        # note that charset is not set because no unicode was rendered
        assert self.controller._headers['Content-Type'] == "application/json"
        assert not self.controller._write_buffer

    def test_head(self):

        def get():
            self.called = True

        self.controller.get = get

        # HEAD should just call the GET version
        self.called = False
        self.controller.head()
        assert self.called

        # but not have a response body
        assert not self.controller._write_buffer

    def test_redirect(self):
        model.peewee_db.close()
        self.controller.prepare()
        self.controller._transforms = [] # normally done in execute, so we have to do it manually

        self.controller.redirect('/test-redirect-url')

        assert self.controller.get_status() == 302
        assert "Location: /test-redirect-url" in str(self.controller._headers)

    def test_redisplay(self):
        model.peewee_db.close()
        self.controller.prepare()
        self.controller._transforms = [] # normally done in execute, so we have to do it manually

        self.controller.redisplay("form_data", "errors", "/test-redirect-url")

        assert self.controller.session.get("form_data") == "form_data"
        assert self.controller.session.get("errors") == "errors"

        assert self.controller.get_status() == 302
        assert "Location: /test-redirect-url" in str(self.controller._headers)

    def test_write_error(self):
        self.mockSessions()
        # temporarily disable exception logging for this test to avoid messy printouts
        self.controller.write_error(500, False)
        found = False
        for part in self.controller._write_buffer:
            if b"Error 500:" in part:
                found = True
                break
        assert found

        # move mails out of the queue so we can test them
        # self.executeDeferred(name="mail")
        #
        # messages = self.mail_stub.get_sent_messages()
        # assert len(messages) == 1
        # assert messages[0].to == SUPPORT_EMAIL
        # assert messages[0].subject == "Error Alert"
        # assert "A User Has Experienced an Error" in str(messages[0].html)

    def test_get_current_user(self):
        user = self.createUser()
        auth = self.createAuth(self.user)

        self.mockSessions()

        # need to hold on to the original (messes up other tests other wise)
        orig_cookie = self.controller.get_secure_cookie

        cookie = ''

        def get_secure_cookie(name):
            return cookie

        self.controller.get_secure_cookie = get_secure_cookie

        # to begin with the user should return nothing
        assert self.controller.current_user is None

        # if an invalid auth key is added it should still return none without errors
        cookie = b"99.99"

        # because of the way cached properties work we have to do a little hack to re-evaluate
        self.controller.current_user = self.controller.get_current_user()

        assert self.controller.current_user is None

        # check a valid but non-existent integer
        cookie = b"9999"
        self.controller.current_user = self.controller.get_current_user()
        assert self.controller.current_user is None

        # finally if a valid keys is added to the session it should return the user object
        cookie = auth.slug.encode() # needs to be bytes, not string
        self.controller.current_user = self.controller.get_current_user()

        assert self.controller.current_user is not None
        assert self.controller.current_user.id == user.id

        self.controller.get_secure_cookie = orig_cookie

    def test_deferEmail(self):
        to = 'test' + UCHAR + '@example.com'
        subject = 'Subject' + UCHAR
        # html = '<p>A User Has Experienced an Error</p>'
        self.controller.deferEmail([to], subject, 'error_alert.html', user=None, url='', method='', message='')

        # move mails out of the queue so we can test them
        # self.executeDeferred(name='mail')
        #
        # messages = self.mail_stub.get_sent_messages()
        # assert len(messages) == 1
        # assert messages[0].to == to
        # assert messages[0].subject == subject
        #
        # having a unicode char triggers base64 encoding
        # assert html.encode('utf-8').encode('base64') in str(messages[0].html)
        # assert not hasattr(messages[0], 'reply_to')

        reply_to = 'test.reply' + UCHAR + '@example.com'
        content = b'content'
        cid = 'content-id'
        filename = 'file.ext'
        attachments = [{'content': content, 'content_id': cid, 'filename': filename, 'type': 'mime/type'}]
        self.controller.deferEmail([to], subject, 'error_alert.html', attachments=attachments, reply_to=reply_to,
            user=None, url='', method='', message='')

        # self.executeDeferred(name='mail')
        # messages = self.mail_stub.get_sent_messages()
        # assert len(messages) == 2
        # assert hasattr(messages[1], 'reply_to')
        # assert messages[1].reply_to == reply_to
        #
        # original = str(messages[1].original)
        # assert content.encode('base64') in original
        # assert cid in original
        # assert filename in original

    def test_validate(self):
        self.mockSessions()

        arguments = {"valid_field": "value" + UCHAR, "invalid_field": "value" + UCHAR}
        self.controller.request.body = json.dumps(arguments)
        self.controller.request.headers = {'content-type': 'application/json'}
        self.controller.FIELDS = {"valid_field": lambda x: (True, x + "valid"), "invalid_field": lambda x: (False, "")}
        form_data, errors, valid_data = self.controller.validate()

        assert form_data["valid_field"] == arguments["valid_field"]
        assert form_data["invalid_field"] == arguments["invalid_field"]
        assert errors == {"invalid_field": True}
        assert valid_data == {"valid_field": "value" + UCHAR + "valid"}
        assert self.controller.get_status() != 400

        # invalid unicode
        self.controller.request.body = b"\xff"
        self.controller.validate()
        assert self.controller.get_status() == 400

        # invalid json
        self.controller.set_status(200)
        self.controller.request.body = "this is not json"
        self.controller.validate()
        assert self.controller.get_status() == 400


class TestDecorators(BaseMockController):

    def setUp(self):
        super(TestDecorators, self).setUp()

        self.controller = self.controller_base.BaseController(self._app, self.getMockRequest())

    def test_withoutUser(self):
        self.mockSessions()
        self.createUser()
        model.peewee_db.close()
        self.controller.prepare()
        self.controller._transforms = [] # normally done in execute, so we have to do it manually

        def action(x):
            return 'action'

        decorator = self.controller_base.withoutUser(action)

        # without a user the action should complete without a redirect
        response = decorator(self.controller)
        assert response == "action"
        assert self.controller.get_status() != 302

        # with a user the action should not complete and it should redirect
        self.mockLogin()
        self.controller.current_user = self.user
        response = decorator(self.controller)
        assert response != "action"
        assert self.controller.get_status() == 302
        assert "Location: /home" in str(self.controller._headers)

    def test_removeSlash(self):
        model.peewee_db.close()
        self.controller.prepare()
        self.controller._transforms = [] # normally done in execute, so we have to do it manually

        def action(x):
            return 'action'

        decorator = self.controller_base.removeSlash(action)

        # without a slash it should not redirect
        self.controller.request.path = "/no-slash"
        response = decorator(self.controller)
        assert response == "action"
        assert self.controller.get_status() != 301

        # with a slash it should
        self.controller.request.path = "/with-slash/"
        response = decorator(self.controller)
        assert response != "action"
        assert self.controller.get_status() == 301
        assert "Location: /with-slash" in str(self.controller._headers)

    def test_validateReferer(self):
        self.mockSessions()
        model.peewee_db.close()
        self.controller.prepare()

        def action(x):
            return 'action'

        decorator = self.controller_base.validateReferer(action)

        # with a valid referer the action should complete
        self.controller.request.host = 'valid'
        self.controller.request.headers = {"referer": "http://valid"}
        response = decorator(self.controller)
        assert response == "action"
        assert self.controller.get_status() != 400

        # without a valid referer the request should not go through
        self.controller.request.headers = {"referer": "http://invalid"}
        response = decorator(self.controller)
        assert response != "action"
        assert self.controller.get_status() == 400


class TestError(BaseTestController):

    def test_error(self):
        # this just covers any URL not handled by something else - always produces 404
        response = self.fetch('/nothing-to-see-here')
        assert response.code == 404

    def test_logError(self):
        # static error pages call this to log to try to log themselves
        assert self.fetch('/logerror', method='POST', body=json.dumps({'reason': 'Default'}), raise_error=True)

        # move mails out of the queue so we can test them
        # self.executeDeferred(name="mail")
        #
        # messages = self.mail_stub.get_sent_messages()
        # assert len(messages) == 1
        # assert messages[0].to == SUPPORT_EMAIL
        # assert messages[0].subject == "Error Alert"
        # assert "Error Message: Static Error Page: Default" in str(messages[0].html)

        # javascript errors also call this to log errors
        assert self.fetch('/logerror', method='POST', body=json.dumps({'javascript': 'error'}), raise_error=True)

        # move mails out of the queue so we can test them
        # self.executeDeferred(name="mail")
        #
        # messages = self.mail_stub.get_sent_messages()
        # assert len(messages) == 2
        # assert messages[1].to == SUPPORT_EMAIL
        # assert messages[1].subject == "Error Alert"
        # assert "Error Message: JavaScript Error: error" in str(messages[1].html)

    def test_policyViolation(self):
        # csp violations are reported directly from browsers
        assert self.fetch('/policyviolation', method='POST', body='CSP JSON', raise_error=True)

        # move mails out of the queue so we can test them
        # self.executeDeferred(name="mail")
        #
        # messages = self.mail_stub.get_sent_messages()
        # assert len(messages) == 1
        # assert messages[0].to == SUPPORT_EMAIL
        # assert messages[0].subject == "Error Alert"
        # assert "Error Message: Content Security Policy Violation: CSP JSON" in str(messages[0].html)


class TestIndex(BaseTestController):

    def test_index(self):
        response = self.fetch('/')
        assert '<h2>Index Page</h2>' in response.body_string


class TestHome(BaseTestController):

    def setUp(self):
        super(TestHome, self).setUp()
        self.createUser()

    def test_home(self):
        response = self.sessionGet('/home')
        assert '<h2>Log In</h2>' in response.body_string

        response = self.login()

        response = self.sessionGet('/home')
        assert '<h2>Logged In Home Page</h2>' in response.body_string


class TestSitemap(BaseTestController):

    def test_sitemap(self):
        response = self.fetch('/sitemap.xml')
        assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in response.body_string


class TestStatic(BaseTestController):

    def test_static(self):
        # loop through and test every known static page
        pages = {'/terms': 'Terms of Service', '/privacy': 'Privacy Policy'}
        for page in pages:
            response = self.fetch(page)
            assert "<h2>" + pages[page] + "</h2>" in response.body_string, pages[page] + " not found"


class TestUser(BaseTestController):

    def setUp(self):
        super(TestUser, self).setUp()
        self.createUser()
        self.other_user = self.createUser(email='test2@test.com')
        self.other_auth = self.createAuth(user=self.other_user)

    def test_user(self):
        self.login()

        response = self.fetch('/user')
        assert '<h2>Account Settings</h2>' in response.body_string
        # assert 'alt="Profile Pic"' not in response.body_string

        # test upload - upload_files doesn't actually seem to work, so we test what we can
        # upload_files = [("profile_pic", "profile.jpg", b"file content", "")]
        # response = self.sessionPost('/user', {}, upload_files=upload_files)
        # assert '<h2>Account Settings</h2>' in response.body_string

        # test delete
        # response = self.sessionPost('/user', {'delete': '1'})
        # assert '<h2>Account Settings</h2>' in response.body_string

    def test_auths(self):
        self.login()
        user_auth = self.createAuth(self.user)

        response = self.sessionGet('/user/auths')
        assert '<h2>Active Sessions</h2>' in response.body_string
        assert user_auth.modified_dt.isoformat() in response.body_string
        assert 'Current Session' in response.body_string

        # test that the user is not allowed to remove another's auth
        data = {'auth_key': self.other_auth.slug}

        response = self.sessionPost('/user/auths', data)
        assert response.code == 403

        data['auth_key'] = user_auth.slug
        response = self.sessionPost('/user/auths', data)
        assert '<h2>Active Sessions</h2>' in response.body_string
        assert user_auth.modified_dt.isoformat() not in response.body_string

    def test_changeEmail(self):
        self.login()

        response = self.fetch('/user/email')
        assert '<h2>Change Email</h2>' in response.body_string

        data = {}
        data["email"] = self.user.email
        data["password"] = "wrong password"

        response = self.sessionPost('/user/email', data)
        assert 'Invalid current password.' in response.body_string

        data["password"] = self.user.password
        response = self.sessionPost('/user/email', data)
        assert 'That email address is already in use.' in response.body_string

        data["email"] = "changeemail.test" + UCHAR + "@example.com"
        response = self.sessionPost('/user/email', data)
        assert 'Email changed successfully.' in response.body_string

    def test_changePassword(self):
        self.login()

        response = self.fetch('/user/password')
        assert '<h2>Change Password</h2>' in response.body_string

        data = {}
        data["new_password"] = "Test change password" + UCHAR
        data["password"] = "wrong password"

        response = self.sessionPost('/user/password', data)
        assert 'Invalid current password.' in response.body_string

        data["password"] = self.user.password
        response = self.sessionPost('/user/password', data)
        assert 'Password changed successfully.' in response.body_string

    def test_signup(self):
        response = self.fetch('/user/signup')
        assert '<h2>Sign Up</h2>' in response.body_string

        data = {}
        data["first_name"] = "Test first name" + UCHAR
        data["last_name"] = "Test last name" + UCHAR
        data["email"] = self.user.email
        data["password"] = "Test password" + UCHAR

        response = self.sessionPost('/user/signup', data)
        assert 'That email address is already in use.' in response.body_string

        # signup succeeds but won't login without valid user agent or IP address
        data["email"] = "signup.test" + UCHAR + "@example.com"

        response = self.sessionPost('/user/signup', data, headers={})
        assert 'Invalid client.' in response.body_string

        # success - use a new email address to avoid conflict with the previous partial success
        data["email"] = "signup2.test" + UCHAR + "@example.com"

        response = self.sessionPost('/user/signup', data)
        assert '<h2>Logged In Home Page</h2>' in response.body_string

    def test_login(self):
        response = self.sessionGet('/user/login')
        assert '<h2>Log In</h2>' in response.body_string

        # using an email address not associated with a user should fail silently
        data = {}
        data["email"] = "doesnt.exist" + UCHAR + "@test.com"
        data["password"] = "wrong password"

        response = self.sessionPost('/user/login', data)
        assert 'Email and password do not match.' in response.body_string

        # a wrong password should also not succeed, even when the email exists
        data["email"] = self.user.email

        response = self.sessionPost('/user/login', data)
        assert 'Email and password do not match.' in response.body_string

        # login fails without a user agent or IP address even when password is correct
        data["password"] = self.user.password

        response = self.sessionPost('/user/login', data, headers={})
        assert 'Invalid client.' in response.body_string

        # success
        response = self.sessionPost('/user/login', data)
        assert 'id' in response.body_string

        # get another page to confirm it works on subsequent requests
        response = self.sessionGet('/home')
        assert '<h2>Logged In Home Page</h2>' in response.body_string

    def test_logout(self):
        self.login()

        # should not allow logging out via GET
        response = self.fetch('/user/logout')
        assert response.code == 405

        # get another page so logout can use the xsrf token
        response = self.sessionGet('/home')

        response = self.sessionPost('/user/logout', {})
        assert '<h2>Index Page</h2>' in response.body_string

    def test_forgotPassword(self):
        response = self.fetch('/user/forgotpassword')
        assert '<h2>Forget Your Password?</h2>' in response.body_string

        # using an email address not associated with a user should fail silently
        data = {"email": "doesnt.exist" + UCHAR + "@example.com"}
        response = self.sessionPost('/user/forgotpassword', data)
        assert 'Your password reset email has been sent.' in response.body_string

        # but the mail queue should be empty
        # self.executeDeferred(name="mail")
        # messages = self.mail_stub.get_sent_messages()
        # assert len(messages) == 0

        # an email address that is associated with a user should respond the same
        data = {"email": self.user.email}
        response = self.sessionPost('/user/forgotpassword', data)
        assert 'Your password reset email has been sent.' in response.body_string

        # except this time the mail queue should have something
        # self.executeDeferred(name="mail")
        # messages = self.mail_stub.get_sent_messages()
        # assert len(messages) == 1
        # assert messages[0].to == self.user.email
        # assert messages[0].subject == "Reset Password"

    def test_resetPassword(self):
        key = self.user.slug

        # without the right authorization this page should redirect with a warning
        response = self.fetch('/user/resetpassword')
        assert 'That reset password link has expired.' in response.body_string

        # even if the user is found the token needs to be right
        response = self.fetch('/user/resetpassword?key=' + key + '&token=wrong')
        assert 'That reset password link has expired.' in response.body_string

        # with the right auth this page should display properly
        self.user = self.user.resetPassword()
        token = self.user.token
        response = self.sessionGet('/user/resetpassword?key=' + key + '&token=' + token)
        assert '<h2>Reset Password</h2>' in response.body_string

        # posting a new password but without user agent or IP address won't log in
        new_password = "Test password2" + UCHAR
        data = {}
        data["password"] = new_password
        data["key"] = key
        data["token"] = token

        response = self.sessionPost('/user/resetpassword', data, headers={})
        assert 'Invalid client.' in response.body_string

        # posting a new password should log the user in - reset again to get a new token
        self.user = self.user.resetPassword()
        data["token"] = self.user.token

        # generate a new xsrf after the successful post above
        self.sessionGet('/user/resetpassword?key=' + key + '&token=' + self.user.token)

        response = self.sessionPost('/user/resetpassword', data)
        assert '<h2>Logged In Home Page</h2>' in response.body_string

        # should be able to log in with the new password now too
        self.logout()
        self.user.password = new_password
        response = self.login()
        assert '<h2>Logged In Home Page</h2>' in response.body_string

        # test that we can't reset a second time
        self.logout()
        response = self.fetch('/user/resetpassword?key=' + key + '&token=' + token)
        assert 'That reset password link has expired.' in response.body_string

        # test that an expired token actually fails
        self.user = self.user.resetPassword()
        token = self.user.token

        # works the first time
        response = self.fetch('/user/resetpassword?key=' + key + '&token=' + token)
        assert '<h2>Reset Password</h2>' in response.body_string

        # fails when we move back the date
        self.user.token_dt = self.user.token_dt - timedelta(seconds=3600)
        self.user.save()
        response = self.fetch('/user/resetpassword?key=' + key + '&token=' + token)
        assert 'That reset password link has expired.' in response.body_string


class TestAdmin(BaseTestController):

    def setUp(self):
        super(TestAdmin, self).setUp()
        self.normal_user = self.createUser()
        self.admin_user = self.createUser(email="admin.test@example.com", is_admin=True)

    def test_admin(self):
        response = self.sessionGet('/admin')
        assert '<h2>Log In</h2>' in response.body_string

        response = self.login(self.normal_user)

        response = self.sessionGet('/admin')
        assert response.code == 403

        self.logout()
        self.login(self.admin_user)

        response = self.sessionGet('/admin')
        assert '<h2>Admin</h2>' in response.body_string


class TestAPI(BaseTestController):

    def setUp(self):
        super(TestAPI, self).setUp()
        self.createUser()

    def test_upload(self):
        self.login()

        # get a page first so the XSRF is generated (no get action for api)
        self.sessionGet('/home')

        response = self.sessionPost('/api/upload', {'url': '/user'})
        assert 'url' in response.body_string


class TestDev(BaseTestController):

    def setUp(self):
        super(TestDev, self).setUp()
        self.createUser()
        self.dev_user = self.createUser(email='dev@test.com', is_dev=True)

    # override this to turn debug off to ensure protections on the dev page
    def get_app(self):
        from main import makeApp
        return makeApp(debug=False, autoreload=False, level=logging.CRITICAL)

    def test_dev(self):
        response = self.sessionGet('/dev')
        assert response.code == 403

        self.login()
        response = self.sessionGet('/dev')
        assert response.code == 403

        self.logout()
        self.login(self.dev_user)

        response = self.sessionGet('/dev')
        assert '<h2>Dev</h2>' in response.body_string

        # test clearing memcache out
        response = self.sessionPost('/dev', {'clear_cache': '1'})
        assert 'Cache Cleared' in response.body_string
