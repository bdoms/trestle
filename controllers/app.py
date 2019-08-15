from controllers._base import BaseController

from tornado import web


class SvelteController(BaseController):

    @web.authenticated
    def get(self):

        self.renderTemplate('svelte.html')


class VueController(BaseController):

    @web.authenticated
    def get(self):

        self.renderTemplate('vue.html')
