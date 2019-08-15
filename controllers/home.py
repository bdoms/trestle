from tornado import web

from controllers._base import BaseController


class HomeController(BaseController):

    @web.authenticated
    def get(self):

        self.renderTemplate('home.html')

    @web.authenticated
    def post(self):

        self.renderJSON({'user': self.current_user.toDict()})
