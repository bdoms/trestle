from tornado import web

from controllers._base import BaseController
import helpers


class StaticController(BaseController):
    """ handles any page that doesn't need to render with custom variables """

    @helpers.cacheAndRender()
    async def get(self, *args):

        path = self.request.path
        filename = "static/" + path + ".html"
        page_title = path.replace("/", " ").strip().title()

        self.renderTemplate(filename, page_title=page_title)


class StaticFileController(web.StaticFileHandler):

    def set_default_headers(self):
        self.set_header('X-Content-Type-Options', 'nosniff')
