from datetime import datetime, timedelta, time
import logging

import tornado.ioloop

import model


class Cron(object):

    LOGGER = logging.getLogger('tornado.application')
    RUN_AT = None
    FREQUENCY = None

    @classmethod
    def run(cls, debug=False):
        raise NotImplementedError

    @classmethod
    def first(cls, debug=False):
        cls.run(debug=debug)

        def closure():
            cls.run(debug=debug)

        async def runWrapper():
            # WARNING! running without a specified executor might not put a limit on the number of threads
            await tornado.ioloop.IOLoop.current().run_in_executor(None, closure)

        # after the first run this sets up the recurring call
        tornado.ioloop.PeriodicCallback(runWrapper, cls.FREQUENCY).start()

    @classmethod
    def setup(cls, debug=False):
        # the first callback gets added with a timer so it runs at the correct time
        now = datetime.utcnow()
        jobs = [AuthCron]
        for job in jobs:
            run_at = datetime.combine(now.date(), job.RUN_AT)
            if run_at > now:
                diff = run_at - now
            else:
                # it's in the past today, so switch it to be tomorrow
                diff = run_at + timedelta(days=1) - now

            tornado.ioloop.IOLoop.current().add_timeout(diff, job.first, debug=debug)


class AuthCron(Cron):

    RUN_AT = time(8) # time of day, assumed to be UTC
    FREQUENCY = 86400000 # in ms

    # this job's specific config
    MAX_DAYS = 30

    @classmethod
    def run(cls, debug=False):

        days_ago = datetime.utcnow() - timedelta(cls.MAX_DAYS)
        total = model.Auth.delete().where(model.Auth.modified_dt < days_ago).execute()

        cls.LOGGER.info('Removed ' + str(total) + ' old auths.')
