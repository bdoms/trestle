# the base file and class for all controllers to inherit from

# python imports
import http.client
import json
import logging

# library imports
from gae_validators import validateRequiredInt
from tornado import escape, web
from peewee import OperationalError

# local imports
import helpers
import model
from config.constants import AUTH_EXPIRES_DAYS, HOST, SUPPORT_EMAIL
from tasks import TaskConsumer, EmailTask


class BaseController(web.RequestHandler):

    # a mapping of field names to their validator functions
    FIELDS = {}

    def prepareSession(self):
        # get a session store for this request
        session = self.get_secure_cookie('session')
        if session:
            self.session = json.loads(session)
        else:
            self.session = {}
        self.orig_session = dict(self.session)

    async def prepare(self):
        self.prepareSession()

        # do this before `before` so that that method can use the db
        try:
            model.peewee_db.connect()
        except OperationalError:
            # this should not generally happen, but it is possible
            # extreme example: the process gets killed mid request, so it doesn't have a chance to cleanup
            # logging.warning('Database connection already open')
            pass

        if hasattr(self, "before"):
            # NOTE that self.path_args and self.path_kwargs are set as part of execute, so they aren't available here
            #      shouldn't be too much of a problem because any before method can inspect the entire request
            try:
                self.before(*self.path_args, **self.path_kwargs)
            except Exception as e:
                if not isinstance(e, web.Finish):
                    # if this isn't closing the request then the finish code is never called, so we do it here as well
                    model.peewee_db.close()
                raise

        # don't run the regular action if there's already an error or redirect
        status_int = self.get_status()
        if status_int < 200 or status_int > 299:
            raise web.Finish

    # override to do cleanup
    def on_finish(self):
        # NOTE that cookies set here aren't returned in the response, so they won't be set
        # this should be used for server-side cleanup only - assume that the response cannot be modified at this point
        # sadly attempts to do so won't throw any errors, and the browser won't see the changes (silent failure)
        model.peewee_db.close()

    def saveSession(self):
        # this needs to be called anywhere we're finishing the response (rendering, redirecting, etc.)
        if self.session != self.orig_session:
            self.set_secure_cookie('session', json.dumps(self.session), expires_days=AUTH_EXPIRES_DAYS,
                domain=self.host, httponly=True, samesite='strict', secure=not self.debug)

    @property
    def logger(self):
        return logging.getLogger('tornado.application')

    @property
    def base_url(self):
        return self.request.protocol + '://' + self.request.host

    @property
    def debug(self):
        return self.settings.get('debug')

    @property
    def host(self):
        return self.debug and self.request.host.split(':', 1)[0] or HOST

    def flash(self, message, level='info'):
        self.session["flash"] = {"level": level, "message": message}

    def compileTemplate(self, filename, **kwargs):

        # add some standard variables
        kwargs["is_admin"] = self.current_user and self.current_user.is_admin
        kwargs["is_dev"] = self.current_user and self.current_user.is_dev
        kwargs["debug"] = self.debug
        kwargs["form"] = self.session.pop("form_data", {})
        kwargs["errors"] = self.session.pop("errors", {})
        kwargs["h"] = helpers
        kwargs["static"] = self.static_url
        kwargs["page_title"] = kwargs.get("page_title", "")
        kwargs["xsrf"] = self.xsrf_token

        # flashes are a dict with two properties: {"level": "info|success|error", "message": "str"}
        kwargs["flash"] = self.session.pop("flash", {})

        return self.render_string(filename, **kwargs)

    def set_default_headers(self):
        # set any headers that should be present with all request types
        self.set_header('X-Content-Type-Options', 'nosniff')
        self.set_header('X-Frame-Options', 'deny') # deprecated in favor of CSP, but better safe than sorry
        self.set_header('X-XSS-Protection', '1')

    def securityHeaders(self):
        # uncomment to enable HSTS - note that it can have permanent consequences for your domain
        # self.set_header('Strict-Transport-Security', 'max-age=86400; includeSubDomains')

        # this is purposefully strict by default
        # you can change site-wide or add logic for different environments or actions as needed

        CSP = "default-src 'self'; form-action 'self'; "
        if self.debug:
            # unsafe-eval is needed here for Vue - to remove it you need to compile
            # svelte uses parcel JS, which serves locally on port 1234
            CSP += "script-src 'self' 'unsafe-eval' " + self.host + ":1234; "
            # parcel HMR uses random ports for a web socket connection
            CSP += "connect-src http://" + self.host + ":* ws://" + self.host + ":*; "
            CSP += "style-src 'self' 'unsafe-inline'; " # needed for inline svelte styles

        CSP += "base-uri 'none'; frame-ancestors 'none'; object-src 'none';"
        CSP += "report-uri " + self.base_url + "/policyviolation"
        self.set_header('Content-Security-Policy', CSP)

    def renderTemplate(self, filename, **kwargs):
        if filename.endswith('.xml'):
            self.set_header('Content-Type', 'application/xml')

        if self.request.method != 'HEAD':
            self.securityHeaders()
            # could have compile call `self.render` but it looks like a lot of extra processing we don't need
            self.write(self.compileTemplate(filename, **kwargs))
            self.saveSession()

    # FUTURE: JSON version of this?
    def renderError(self, status_int, stacktrace=None):
        self.set_status(status_int)
        page_title = "Error " + str(status_int) + ": " + http.client.responses[status_int]
        self.renderTemplate("error.html", stacktrace=stacktrace, page_title=page_title)

    def renderJSON(self, data):
        self.set_header('Content-Type', 'application/json')
        if self.request.method != 'HEAD':
            # auto add the xsrf token in to every response
            self.set_header('X-Xsrf-Token', self.xsrf_token)
            self.write(data)
            self.saveSession()

    async def head(self, *args):
        # support HEAD requests in a generic way
        if hasattr(self, 'get'):
            self.get(*args)
            # the output may be cached, but don't send it to save bandwidth
            self.clear()
        else:
            self.renderError(405)

    def redirect(self, *args, **kwargs):
        # saving the session needs to happen before the redirect for the cookies to be set
        self.saveSession()
        super(BaseController, self).redirect(*args, **kwargs)

    def redisplay(self, form_data=None, errors=None, url=None):
        """ redirects to the current page by default """
        if form_data is not None:
            self.session["form_data"] = form_data
        if errors is not None:
            self.session["errors"] = errors

        if url:
            self.redirect(url)
        else:
            self.redirect(self.request.path)

    # this overrides the base class for handling things like 500 errors
    def write_error(self, status_code, exc_info=None):
        # if this is development, then include a stack trace
        stacktrace = None
        message = None
        if exc_info and (self.settings.get('debug') or (self.current_user and self.current_user.is_admin)):
            import traceback
            stacktrace = ''.join(traceback.format_exception(*exc_info))
            message = exc_info[0].__name__

        # this can be called before the request is even prepared (e.g. by @web.authenticated)
        # in which case the session won't exist yet, but we expect it to when we render things
        if not hasattr(self, 'session'):
            self.prepareSession()

        self.renderError(status_code, stacktrace=stacktrace)

        # send an email notifying about this error if it's in the 500 range
        if status_code > 499:
            self.deferEmail([SUPPORT_EMAIL], "Error Alert", "error_alert.html", message=message,
                user=self.current_user, url=self.request.full_url(), method=self.request.method)

    # this is called automatically to set the current_user property
    def get_current_user(self):
        user = None
        slug = self.get_secure_cookie('auth_key')
        if slug:
            # secure cookies appear to always return bytes, and we need a string, so force it here
            slug = slug.decode()

            valid, int_slug = validateRequiredInt(slug)

            if valid:
                # NOTE: there's a minor performance hit here for creating a nested function
                #       this can be eliminated by refactoring the cache function to pass args and kwargs through
                def getUser():
                    return model.User.getByAuth(int_slug)
                user = helpers.cache('auth_' + slug, getUser, debug=self.debug)

            if not user:
                self.clear_cookie('auth_key', domain=self.host)
                self.flash('You have been logged out.')
                if self.request.path.startswith('/data/'):
                    self.renderJSONError(401)
                    raise web.Finish

        return user

    def deferEmail(self, to, subject, filename, reply_to=None, attachments=None, **kwargs):
        # FUTURE: should HTML rendering be done in the queue rather than here?
        params = {'to': to, 'subject': subject, 'callback': EmailTask.sendEmail}

        if reply_to:
            params['reply_to'] = reply_to

        # this supports passing a template as well as a file
        if isinstance(filename, str):
            filename = "emails/" + filename

        # support passing in a custom host to prefix link
        if "host" not in kwargs:
            kwargs["host"] = self.base_url
        params['html'] = self.render_string(filename, **kwargs).decode('utf-8')

        if attachments:
            params['attachments'] = attachments

        TaskConsumer.TASKQ.put_nowait(params)

    # FUTURE: look at schema for this https://github.com/keleshev/schema
    def validate(self, fields=None):
        form_data = {} # all the original request data, for potentially re-displaying
        errors = {} # only fields with errors
        valid_data = {} # only valid fields

        data = None
        if 'application/json' in self.request.headers.get('content-type', ''):
            try:
                data = escape.json_decode(self.request.body)
            except (UnicodeDecodeError, json.decoder.JSONDecodeError):
                self.set_status(400)
                return {}, {'request': 'bad data'}, {}

        if not fields:
            fields = self.FIELDS

        for name, validator in fields.items():
            if data:
                form_data[name] = data.get(name, None)
            else:
                form_data[name] = self.get_argument(name, None)

            valid, value = validator(form_data[name])
            if valid:
                valid_data[name] = value
            else:
                errors[name] = True

        return form_data, errors, valid_data


def withoutUser(action):
    def decorate(*args, **kwargs):
        controller = args[0]
        if not controller.current_user:
            return action(*args, **kwargs)
        else:
            url = "/home"
            return controller.redirect(url)
    return decorate


def removeSlash(action):
    def decorate(*args, **kwargs):
        controller = args[0]
        if controller.request.path.endswith("/"):
            return controller.redirect(controller.request.path[:-1], permanent=True)
        return action(*args, **kwargs)
    return decorate


def validateReferer(action):
    def decorate(*args, **kwargs):
        controller = args[0]
        referer = controller.request.headers.get("referer")
        if not referer or not referer.startswith(controller.base_url):
            return controller.renderError(400)
        return action(*args, **kwargs)
    return decorate
