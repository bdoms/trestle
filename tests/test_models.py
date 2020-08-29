from datetime import datetime

from _base import BaseTestCase, UCHAR # this MUST come before model import to set up test DB properly

import model


class TestBaseModel(BaseTestCase):

    def test_slug(self):
        self.createUser()
        assert self.user.slug
        assert isinstance(self.user.slug, str)

    def test_getBySlug(self):
        created_user = self.createUser()
        gotten_user = model.User.getBySlug(created_user.slug)
        assert gotten_user
        assert created_user.id == gotten_user.id

    def test_save(self):
        # TODO
        pass


class TestUser(BaseTestCase):

    def stubUrandom(self, n):
        return b"constant"

    def test_auths(self):
        self.createAuth()
        auths = list(self.user.auths)
        assert len(auths) == 1
        assert isinstance(auths[0], model.Auth)

    def test_getByAuth(self):
        auth = self.createAuth()
        user = model.User.getByAuth(auth.slug)
        assert user
        assert user.id == auth.user_id

    def test_getByEmail(self):
        created_user = self.createUser()
        queried_user = model.User.getByEmail(created_user.email)
        assert queried_user
        assert created_user.id == queried_user.id

    def test_hashPassword(self):
        result = model.User.hashPassword("test password" + UCHAR, ("test salt" + UCHAR).encode('utf8'))

        hsh = "4ac2a746698395e501c1f5f271a6e99db751112b9af5fb0dc2240393c1ea"
        hsh += "658971913b3799023c948aa9c1b2fad8da75051f7f25103d4bcf3b106b52cd317be4"
        assert result == hsh

    def test_changePassword(self):
        # stub so we get constant results
        orig_random = model.os.urandom
        model.os.urandom = self.stubUrandom

        password_salt, hashed_password = model.User.changePassword("test password" + UCHAR)

        # revert the stub to the original now that the method has been called
        model.os.urandom = orig_random

        assert password_salt == b"Y29uc3RhbnQ=" # "constant" base64 encoded

        hsh = "9a079faf77c18c1d4169bfa9bc77a1216e2a9ecfd6537db0c1e21dcaaf0bbb"
        hsh += "8d5f62749c0602c8a31edff2a6b9a5ac91df84ebff9581131ba648af7263e1bd62"
        assert hashed_password == hsh

    def test_getAuth(self):
        self.createAuth()
        auth = self.user.getAuth(self.auth.user_agent)
        assert auth
        assert auth.id == self.auth.id

    def test_resetPassword(self):
        user = self.createUser()

        # stub the os urandom method so that we get constant results
        orig = model.os.urandom
        model.os.urandom = self.stubUrandom

        token = user.resetPassword()

        # revert the stub to the original now that the method has been called
        model.os.urandom = orig

        assert token == "Y29uc3RhbnQ" # "constant" base64 encoded for URLs
        assert (datetime.utcnow() - user.token_dt).total_seconds() < 1 # should be very fresh
