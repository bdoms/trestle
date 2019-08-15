from controllers._base import BaseController

SIZE_LIMIT = 10 * (2 ** 20) # 10 MB


class UploadController(BaseController):

    def post(self):

        # TODO: update this to provide a signed URL for uploading from the service of your choice
        url = ''

        self.renderJSON({'url': url})
