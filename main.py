# this is the main entry point for the application
from http.cookies import Morsel
import logging
import os

from tornado import web
from tornado.ioloop import IOLoop
from tornado.log import enable_pretty_logging
from tornado.options import define, options

from config import constants
from cron import Cron
from tasks import TaskConsumer

# URL routes
from controllers import account, admin, api, app, dev, error, home, index, sitemap, static

# this is a monkey-patch to support the samesite cookie option
# FUTURE: this can be removed if using Python 3.8+, as support for this was added there
Morsel._reserved['samesite'] = 'SameSite'

handlers = [
    ('/', index.IndexController),
    ('/home', home.HomeController),

    # svelte routes
    ('/svelte/home', app.SvelteController),
    ('/svelte/account', app.SvelteController),
    ('/svelte/account/auths', app.SvelteController),
    ('/svelte/account/email', app.SvelteController),
    ('/svelte/account/password', app.SvelteController),

    # vue routes
    ('/vue/home', app.VueController),
    ('/vue/account', app.VueController),
    ('/vue/account/auths', app.VueController),
    ('/vue/account/email', app.VueController),
    ('/vue/account/password', app.VueController),

    ('/account', account.IndexController),
    ('/account/auths', account.AuthsController),
    ('/account/email', account.EmailController),
    ('/account/password', account.PasswordController),
    ('/account/signup', account.SignupController),
    ('/account/login', account.LoginController),
    ('/account/logout', account.LogoutController),
    ('/account/forgotpassword', account.ForgotPasswordController),
    ('/account/resetpassword', account.ResetPasswordController),
    ('/terms', static.StaticController),
    ('/privacy', static.StaticController),
    ('/sitemap.xml', sitemap.SitemapController),
    ('/admin', admin.AdminController),
    ('/api/upload', api.UploadController),
    ('/dev', dev.DevController),
    ('/logerror', error.LogErrorController),
    ('/policyviolation', error.PolicyViolationController),
    ('/(.*)', error.ErrorController)
]


class webApp(web.Application):

    # this overrides tornado's logging so we can customize it
    def log_request(self, handler):
        # they're logging is pretty good - just want to a add a line about user agent
        logging.info(handler.request.headers.get('user-agent'))
        super(webApp, self).log_request(handler)


# FUTURE: add this once Tornady implements it: xsrf_cookie_kwargs={'samesite': 'strict'}
def makeApp(domain=None, debug=False, autoreload=False, level=logging.INFO):
    # logging setup
    access_log = logging.getLogger('tornado.access')
    access_log.setLevel(level)
    application_log = logging.getLogger('tornado.application')
    application_log.setLevel(level)
    general_log = logging.getLogger('tornado.general')
    general_log.setLevel(level)

    if level == logging.DEBUG:
        # this prints to stdout by default
        enable_pretty_logging()

    app_path = os.path.dirname(os.path.realpath(__file__))
    views_path = os.path.join(app_path, 'views')
    static_path = os.path.join(app_path, 'static')

    if not domain:
        domain = constants.HOST

    return webApp(handlers=handlers, template_path=views_path, debug=debug, autoreload=autoreload,
        compress_response=True,
        static_path=static_path, static_handler_class=static.StaticFileController,
        cookie_secret=constants.SESSION_KEY, xsrf_cookies=True,
        xsrf_cookie_kwargs={'domain': domain, 'httponly': True, 'secure': not debug, 'samesite': 'strict'},
        login_url='/account/login')


# see https://www.tornadoweb.org/en/stable/guide/running.html
if __name__ == "__main__":
    define('debug', default=False, help='enable debug')
    define('port', default=8888, help='port to listen on')
    define('address', default=constants.HOST, help='address to listen on')

    # NOTE that for cookies to work correctly with other computers connecting over the LAN
    # the address should be set to the LAN IP, e.g. 192.168... or 10.0...., NOT localhost or 0.0.0.0

    options.parse_command_line()

    # FUTURE: this should probably be run in a separate process, especially in production
    IOLoop.current().add_callback(TaskConsumer.consumer, debug=options.debug)

    # CAREFUL only run this during development - supervisor should run this separately in production
    if options.debug:
        IOLoop.current().add_callback(Cron.setup, debug=options.debug)

    if options.debug:
        app = makeApp(domain=options.address, debug=True, autoreload=True, level=logging.DEBUG)
    else:
        app = makeApp()

    # xheaders enables forwarded headers from nginx
    app.listen(options.port, address=options.address, xheaders=True)

    application_log = logging.getLogger('tornado.access')
    application_log.info('Debug is ' + str(options.debug))
    application_log.info('Server running at http://' + options.address + ':' + str(options.port))

    IOLoop.current().start()
