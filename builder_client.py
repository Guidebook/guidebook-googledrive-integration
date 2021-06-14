import requests


class BuilderClient(object):
    """
    Helper class for making requests to the Builder API which handles things like raising exceptions on invalid 
    responses etc.
    """
    def __init__(self, api_key):
        self.builder_session = requests.Session()
        self.builder_session.headers.update({"Authorization": f"JWT {api_key}"})

    def post(self, url, data=None, files=None, raise_error=True):
        if data and files:
            response = self.builder_session.post(url, data=data, files=files)
        elif data:
            response = self.builder_session.post(url, data=data)
        else:
            response = self.builder_session.post(url)

        if raise_error:
            response.raise_for_status()
        return response

    def patch(self, url, data=None, files=None):
        if data and files:
            response = self.builder_session.patch(url, data=data, files=files)
        elif data:
            response = self.builder_session.patch(url, data=data)
        else:
            response = self.builder_session.patch(url)

        return response

    def get(self, url):
        response = self.builder_session.get(url)
        response.raise_for_status()

        return response

    def delete(self, url):
        response = self.builder_session.delete(url)
        return response
