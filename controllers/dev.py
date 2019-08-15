from gae_validators import validateEmail

from controllers._base import BaseController
import helpers
import model


class DevController(BaseController):
    """ handles request for the dev page """

    FIELDS = {'email': validateEmail}

    def before(self):
        if (not self.current_user or not self.current_user.is_dev) and not self.debug:
            return self.renderError(403)

    def get(self):
        self.renderTemplate('dev.html')

    def post(self):

        if self.get_argument('clear_cache', None):
            helpers.clear_cache()
            self.logger.info('Cleared cache.')
            self.flash('Cache Cleared')

        elif self.get_argument('make_admin', None):
            form_data, errors, valid_data = self.validate()
            if not errors:
                user = model.User.getByEmail(valid_data["email"])
                if user:
                    user.is_admin = True
                    user.save()

                    # the user may currently be signed in so invalidate its cache to get the new permissions
                    helpers.uncache(user.slug)
                    self.logger.info('Made user admin: ' + valid_data['email'])
                    self.flash('User successfully made admin.', level='success')
                else:
                    errors['exists'] = True
            if errors:
                return self.redisplay(form_data, errors)

        elif self.get_argument('migrate', None):
            self.logger.info('Beginning migration.')

            # FUTURE: probably want to move this to a script outside the webserver
            # change and uncomment to do migration work
            # can also use a dictionary instead of kwargs here
            # q = model.User.update(model.User.prop='value').where()
            total = 0 # q.execute()

            self.logger.info('Migration finished. Modified ' + str(total) + ' items.')
            self.flash('Migrations Complete', level='success')

        elif self.get_argument('reset', None) and self.debug:
            # use model.py to reset the db, then you can run this to add fixture data
            model.reset()

            # add any fixtures needed for development here
            password_salt, hashed_password = model.User.changePassword('test')
            user = model.User(first_name='Test', last_name='Testerson', email='test@test.com',
                password_salt=password_salt, hashed_password=hashed_password)
            user.save()

            # auto signout since the IDs and keys have all changed
            self.clear_all_cookies()
            helpers.clear_cache()
            self.flash('Data Reset')

        self.redisplay()
