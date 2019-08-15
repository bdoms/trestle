from datetime import datetime, timedelta

from _base import BaseTestCase
from cron import AuthCron
import model


class TestCron(BaseTestCase):

    def test_auth(self):

        auth = self.createAuth()
        auth2 = self.createAuth()

        # make one of them be old enough to get cleared
        auth2.modified_dt = datetime.utcnow() - timedelta(days=AuthCron.MAX_DAYS + 1)
        super(model.BaseModel, auth2).save() # normal save overrides modified_dt, so we call the original directly

        assert model.Auth.select().count() == 2

        AuthCron.run()
        assert model.Auth.select().count() == 1
        assert auth.id == model.Auth.select().first().id
