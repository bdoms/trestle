import asyncio
import os
import unittest
import sys

from peewee import OperationalError

# set environment variables before importing app code so it connects to the test database
# this MUST come before any model import
os.environ['DB_NAME'] = 'trestle_test'
os.environ['DB_USER'] = 'trestle_test'
os.environ['DB_PASS'] = 'trestle_test'

app_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(app_path)

import model # NOQA: E402

UCHAR = u"\u03B4" # lowercase delta


# this effectively syncs an async coroutine
# see https://stackoverflow.com/questions/23033939/how-to-test-python-3-4-asyncio-code
def async_test(coro):
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(coro(*args, **kwargs))
    return wrapper


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        # an error in a previous test could prevent this from shutting down correctly
        try:
            model.peewee_db.connect()
        except OperationalError:
            pass

        model.reset()

        import helpers
        helpers.clear_cache()

    def tearDown(self):
        model.peewee_db.close()

    # fixtures
    def createUser(self, email=None, is_admin=False, **kwargs):
        display_name = "Test display name" + UCHAR
        email = email or "test" + UCHAR + "@example.com"
        password = "Test password" + UCHAR

        other_user = model.User.getByEmail(email)
        assert not other_user, "That email address is already in use."

        # NOTE that username is lowercased here - it maybe should not be in the future
        password_salt, hashed_password = model.User.changePassword(password)
        user = model.User.create(display_name=display_name, email=email,
            password_salt=password_salt, hashed_password=hashed_password, is_admin=is_admin, **kwargs)

        user.password = password # for convenience with signing in during testing

        if not hasattr(self, 'user'):
            # this is the default, so add an easy reference to it
            self.user = user

        return user

    def createAuth(self, user=None):
        if not user:
            if not hasattr(self, 'user'):
                self.createUser()
            user = self.user

        auth = model.Auth.create(user_agent='test user agent' + UCHAR, os='test os' + UCHAR,
            browser='test browser' + UCHAR, device='test device' + UCHAR, ip='127.0.0.1', user=user)

        if not hasattr(self, 'auth'):
            self.auth = auth

        return auth
