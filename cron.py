from datetime import datetime, timedelta, time
import logging

from tornado import ioloop
from tornado.options import define, options

import model


class Cron(object):

    RUN_AT = None
    FREQUENCY = None

    @classmethod
    def run(cls, debug=False):
        raise NotImplementedError

    @classmethod
    async def first(cls, debug=False):
        def closure():
            logging.info('Running cron job: ' + cls.__name__)
            cls.run(debug=debug)

        async def runWrapper():
            # WARNING! running without a specified executor might not put a limit on the number of threads
            await ioloop.IOLoop.current().run_in_executor(None, closure)

        # after the first run this sets up the recurring call
        ioloop.PeriodicCallback(runWrapper, cls.FREQUENCY).start()

        # do the first run - this must come after setting up the callback
        # otherwise the timing is delayed by how long it takes to run this
        await runWrapper()

    @classmethod
    def setup(cls, debug=False):
        logging.info('Cron started, debug is ' + str(debug))

        # the first callback gets added with a timer so it runs at the correct time
        jobs = [AuthCron]

        now = datetime.utcnow()
        today = now.date()
        for job in jobs:
            run_at = datetime.combine(today, job.RUN_AT)
            if run_at > now:
                diff = run_at - now
            else:
                # it's in the past today, so switch it to be tomorrow
                diff = run_at + timedelta(days=1) - now

            ioloop.IOLoop.current().add_timeout(diff, job.first, debug=debug)


class AuthCron(Cron):

    RUN_AT = time(8) # time of day, assumed to be UTC
    FREQUENCY = 86400000 # in ms

    # this job's specific config
    MAX_DAYS = 30

    @classmethod
    def run(cls, debug=False):

        days_ago = datetime.utcnow() - timedelta(cls.MAX_DAYS)
        total = model.Auth.delete().where(model.Auth.modified_dt < days_ago).execute()

        logging.info('Removed ' + str(total) + ' old auths.')


if __name__ == '__main__':
    define('debug', default=False, help='enable debug')

    options.parse_command_line()

    ioloop.IOLoop.current().add_callback(Cron.setup, debug=options.debug)

    ioloop.IOLoop.current().start()
