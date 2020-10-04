from datetime import datetime

from gae_validators import validateRequiredString, validateRequiredEmail, validateBool, validateRequiredInt
import httpagentparser
from tornado import web

from config.constants import AUTH_EXPIRES_DAYS, HOST
from controllers._base import BaseController, withoutAccount
import model
import helpers

# IMAGE_TYPES = ["gif", "jpg", "jpeg", "png"]


def validatePassword(source):
    return validateRequiredString(source, min_length=8)


class BaseLoginController(BaseController):

    def login(self, user, new=False, remember=False):
        ua = self.request.headers.get('User-Agent', '')
        ip = self.request.remote_ip or ''
        # reject a login attempt without a user agent or IP address
        if not ua or not ip:
            return self.renderJSON({'errors': 'Invalid client.'})

        auth = None
        if not new:
            auth = user.getAuth(ua)

        if auth:
            # note that we want to save this even if it isn't different because it updates the last modified
            auth.ip = ip
            auth.save()
        else:
            parsed = httpagentparser.detect(ua)
            os = browser = device = ''
            if 'os' in parsed:
                # shows up as Linux for Android, Mac OS for iOS
                os = parsed['os']['name']
            if 'browser' in parsed:
                browser = parsed['browser']['name']
            if 'dist' in parsed:
                # "dist" stands for "distribution" - like Android, iOS
                device = parsed['dist']['name']
            auth = model.Auth(user_agent=ua, os=os, browser=browser, device=device, ip=ip, account=user)
            auth.save()

        expires_days = remember and AUTH_EXPIRES_DAYS or None
        self.set_secure_cookie('auth_key', auth.slug, expires_days=expires_days, domain=HOST,
            httponly=True, samesite='strict', secure=not self.debug)

        self.redirect("/home")


class IndexController(BaseController):

    @web.authenticated
    async def get(self):

        self.renderTemplate('account/index.html')

    # @web.authenticated
    # def post(self):

    #     # FUTURE: this needs to be adapted to not use the blob store at all
    #     if self.get_argument('delete', None):
    #         if self.current_user.pic_url:
    #             # FUTURE: remove the file from disk or wherever it's saved

    #         self.current_user.pic_gcs = None
    #         self.current_user.pic_url = None
    #     else:
    #         errors = {}
    #         # FUTURE: file upload example
    #         # for upload in uploads:
    #         #     # enforce file type based on extension
    #         #     name, ext = upload.filename.rsplit(".", 1)
    #         #     ext = ext.lower()
    #         #     if ext not in IMAGE_TYPES:
    #         #         upload.delete()
    #         #         errors = {'type': True}
    #         #         continue

    #         if errors:
    #             return self.redisplay({}, errors)

    #     self.current_user.save()
    #     helpers.uncache(self.current_user.slug)
    #     self.redisplay()


class AuthsController(BaseController):

    FIELDS = {'auth_key': validateRequiredString}

    @web.authenticated
    async def get(self):

        auths = self.current_user.auths
        current_auth_key = self.get_secure_cookie('auth_key').decode()

        if self.get_argument('app', None):
            return self.renderJSON({'auths': [auth.toDict() for auth in auths], 'current_auth_id': current_auth_key})

        self.renderTemplate('account/auths.html', auths=auths, current_auth_key=current_auth_key)

    @web.authenticated
    async def post(self):

        app = self.get_argument('app', None)
        form_data, errors, valid_data = self.validate()

        if errors:
            if app:
                return self.renderJSONError(400, {'errors': errors})

            return self.redisplay(form_data, errors)

        auth = model.Auth.getBySlug(valid_data['auth_key'])
        if not auth:
            if app:
                self.renderJSONError(404)

            return self.renderError(404)

        if auth.account_id != self.current_user.id:
            if app:
                return self.renderJSONError(403)

            return self.renderError(403)

        auth.delete_instance()
        helpers.uncache(valid_data['auth_key'])

        if app:
            return self.renderJSON({'ok': '1'})

        self.flash('Access revoked.', level='success')

        self.redisplay()


class EmailController(BaseController):

    FIELDS = {"email": validateRequiredEmail, "password": validatePassword}

    @web.authenticated
    async def get(self):

        self.renderTemplate('account/email.html')

    @web.authenticated
    async def post(self):

        app = self.get_argument('app', None)
        form_data, errors, valid_data = self.validate()

        hashed_password = model.Account.hashPassword(valid_data["password"],
            self.current_user.password_salt.encode('utf8'))

        if hashed_password != self.current_user.hashed_password:
            errors["match"] = True

        # extra validation to make sure that email address isn't already in use
        if not errors:
            # note that emails are supposed to be case sensitive according to RFC 5321
            # however in practice users consistenly expect them to be case insensitive
            email = valid_data["email"].lower()
            user = model.Account.getByEmail(email)
            if user:
                errors["exists"] = True

        if errors:
            if "password" in form_data:
                del form_data["password"] # never send password back for security

            if app:
                return self.renderJSONError(400, {'errors': errors})

            return self.redisplay(form_data, errors)

        self.current_user.email = email
        self.current_user.save()
        helpers.uncache(self.current_user.slug)

        if app:
            return self.renderJSON({'ok': '1'})

        self.flash("Email changed successfully.", level="success")
        self.redirect("/account")


class PasswordController(BaseController):

    FIELDS = {"password": validatePassword, "new_password": validatePassword}

    @web.authenticated
    async def get(self):

        self.renderTemplate('account/password.html')

    @web.authenticated
    async def post(self):

        app = self.get_argument('app', None)
        form_data, errors, valid_data = self.validate()

        if not errors:
            hashed_password = model.Account.hashPassword(valid_data["password"],
                self.current_user.password_salt.encode('utf8'))

            if hashed_password != self.current_user.hashed_password:
                errors["match"] = True

        if errors:
            if "password" in form_data:
                del form_data["password"]
            if "new_password" in form_data:
                del form_data["new_password"]

            if app:
                return self.renderJSONError(400, {'errors': errors})

            return self.redisplay(form_data, errors)

        password_salt, hashed_password = model.Account.changePassword(valid_data["new_password"])

        self.current_user.password_salt = password_salt
        self.current_user.hashed_password = hashed_password
        self.current_user.save()
        helpers.uncache(self.current_user.slug)

        if app:
            return self.renderJSON({'ok': '1'})

        self.flash("Password changed successfully.", level="success")
        self.redirect("/account")


class SignupController(BaseLoginController):

    FIELDS = {
        "email": validateRequiredEmail,
        "password": validatePassword
    }

    @withoutAccount
    async def get(self):

        self.renderTemplate('account/signup.html')

    @withoutAccount
    async def post(self):

        form_data, errors, valid_data = self.validate()

        # extra validation to make sure the username isn't already in use at creation time
        if not errors:
            # FUTURE: keep an un-lowered copy of this for potential display?
            valid_data["email"] = valid_data["email"].lower()
            user = model.Account.getByEmail(valid_data["email"])
            if user:
                errors["exists"] = True

        if errors:
            if "password" in form_data:
                del form_data["password"] # never send password back for security
            self.redisplay(form_data, errors)
        else:
            password_salt, hashed_password = model.Account.changePassword(valid_data["password"])
            del valid_data["password"]

            user = model.Account(password_salt=password_salt, hashed_password=hashed_password, **valid_data)
            user.save()
            self.login(user, new=True)


class LoginController(BaseLoginController):

    FIELDS = {"email": validateRequiredEmail, "password": validatePassword, "remember": validateBool}

    @withoutAccount
    async def get(self):

        self.renderTemplate('account/login.html')

    @withoutAccount
    async def post(self):

        form_data, errors, valid_data = self.validate()

        # check that the user exists and the password matches
        user = None
        if not errors:
            user = model.Account.getByEmail(valid_data["email"].lower())
            if user:
                hashed_password = model.Account.hashPassword(valid_data["password"], user.password_salt.encode('utf8'))
                if hashed_password != user.hashed_password:
                    # note that to dissuade brute force attempts the error for not finding the user
                    # and not matching the password should be the same
                    errors["match"] = True
            else:
                errors["match"] = True

        if errors:
            if "password" in form_data:
                del form_data["password"] # never send password back for security
            self.redisplay(form_data, errors)
        else:
            self.login(user, remember=valid_data["remember"])


class LogoutController(BaseController):

    @web.authenticated
    async def post(self):
        slug = self.get_secure_cookie('auth_key').decode()
        model.Auth.delete().where(model.Auth.id == slug).execute()
        helpers.uncache('auth_' + slug)

        self.clear_all_cookies(domain=self.host)
        self.redirect("/")


class ForgotPasswordController(BaseController):

    FIELDS = {"email": validateRequiredEmail}

    @withoutAccount
    async def get(self):

        self.renderTemplate('account/forgot_password.html')

    @withoutAccount
    async def post(self):

        form_data, errors, valid_data = self.validate()

        if errors:
            self.redisplay(form_data, errors)
        else:
            # for security, don't alert them if the user doesn't exist
            user = model.Account.getByEmail(valid_data["email"].lower())
            if user:
                token = user.resetPassword()
                self.deferEmail([user.email], "Reset Password", "reset_password.html",
                    key=user.slug, token=token)

            message = "Your password reset email has been sent. "
            message += "For security purposes it will expire in one hour."
            self.flash(message, level='success')
            self.redisplay()


class ResetPasswordController(BaseLoginController):

    FIELDS = {"key": validateRequiredInt, "token": validateRequiredString, "password": validatePassword}

    @withoutAccount
    def before(self):
        is_valid = False

        valid, key = validateRequiredInt(self.get_argument("key", None))
        self.key = key

        valid, token = validateRequiredString(self.get_argument("token", None))
        self.token = token

        if self.key and self.token:
            self.reset_user = model.Account.getBySlug(self.key)
            if self.reset_user and self.reset_user.hashed_token and self.reset_user.token_dt:
                hashed_token = self.reset_user.hashToken(self.token)
                if hashed_token == self.reset_user.hashed_token:
                    # token is valid for one hour
                    if (datetime.utcnow() - self.reset_user.token_dt).total_seconds() < 3600:
                        is_valid = True

        if not is_valid:
            self.flash("That reset password link has expired.", level="error")
            self.redirect("/account/forgotpassword")

    async def get(self):

        self.renderTemplate('account/reset_password.html', key=self.key, token=self.token)

    async def post(self):

        form_data, errors, valid_data = self.validate()

        if errors:
            self.redisplay(form_data, errors, "/account/resetpassword?key=" + self.key + "&token=" + self.token)
        else:
            password_salt, hashed_password = model.Account.changePassword(valid_data["password"])
            del valid_data["password"]
            self.reset_user.password_salt = password_salt
            self.reset_user.hashed_password = hashed_password
            self.reset_user.hashed_token = None
            self.reset_user.token_dt = None
            self.reset_user.save()

            # need to uncache so that changes to the user object get picked up by the cache
            helpers.uncache(self.reset_user.slug)
            self.flash("Your password has been changed. You have been logged in with your new password.",
                level="success")
            self.login(self.reset_user)
