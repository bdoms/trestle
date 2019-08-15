# this is the main entry point for the application
import logging
import os

from tornado import web
from tornado.ioloop import IOLoop
from tornado.log import enable_pretty_logging

from config import constants
from cron import Cron
from tasks import TaskConsumer

# URL routes
from controllers import admin, api, app, dev, error, home, index, sitemap, static, user

handlers = [
    ('/', index.IndexController),
    ('/home', home.HomeController),

    # svelte routes
    ('/svelte/home', app.SvelteController),
    ('/svelte/user', app.SvelteController),
    ('/svelte/user/auths', app.SvelteController),
    ('/svelte/user/email', app.SvelteController),
    ('/svelte/user/password', app.SvelteController),

    # vue routes
    ('/vue/home', app.VueController),
    ('/vue/user', app.VueController),
    ('/vue/user/auths', app.VueController),
    ('/vue/user/email', app.VueController),
    ('/vue/user/password', app.VueController),

    ('/user', user.IndexController),
    ('/user/auths', user.AuthsController),
    ('/user/email', user.EmailController),
    ('/user/password', user.PasswordController),
    ('/user/signup', user.SignupController),
    ('/user/login', user.LoginController),
    ('/user/logout', user.LogoutController),
    ('/user/forgotpassword', user.ForgotPasswordController),
    ('/user/resetpassword', user.ResetPasswordController),
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


# FUTURE: add this once Tornady implements it: xsrf_cookie_kwargs={'samesite': 'strict'}
def makeApp(debug=False, autoreload=False, level=logging.INFO):
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

    return web.Application(handlers=handlers, template_path=views_path, debug=debug, autoreload=autoreload,
        static_path=static_path, cookie_secret=constants.SESSION_KEY, xsrf_cookies=True, login_url='/user/login')


# see https://www.tornadoweb.org/en/stable/guide/running.html
if __name__ == "__main__":
    debug = True
    port = 8888

    # FUTURE: this should probably be run in a separate process, especially in production
    IOLoop.current().add_callback(TaskConsumer.consumer, debug=debug)

    # FUTURE: this should probably also be in a separate process
    IOLoop.current().add_callback(Cron.setup, debug=debug)

    if debug:
        app = makeApp(debug=True, autoreload=True, level=logging.DEBUG)
    else:
        app = makeApp()

    app.listen(port)

    application_log = logging.getLogger('tornado.access')
    application_log.info('Server running at http://localhost:' + str(port))

    IOLoop.current().start()
