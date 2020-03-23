from controllers._base import BaseController

from tornado import web


class SvelteController(BaseController):

    @web.authenticated
    async def get(self):

        self.renderTemplate('svelte.html', host=self.host)


class VueController(BaseController):

    @web.authenticated
    async def get(self):

        self.renderTemplate('vue.html')
