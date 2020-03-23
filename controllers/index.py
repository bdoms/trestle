from controllers._base import BaseController
import helpers


class IndexController(BaseController):
    """ handles request for the main index page of the site """

    @helpers.cacheAndRender()
    async def get(self):

        self.renderTemplate('index.html')
