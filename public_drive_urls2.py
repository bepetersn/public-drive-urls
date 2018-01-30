
import requests
import sys
if sys.version_info[0] < 3:
    from urlparse import urlsplit
else:
    from urllib.parse import urlsplit

LOGIN_REDIRECTION_HOST = 'google.com'


class ResourceNotFoundException(RuntimeError):
    pass


class DriveDocumentResource(object):
    pass


class DriveResourceFinder(object):

    """
    This class is responsible for taking a Google Drive url
    that conforms to one of the formats defined in ACCESS_URLS
    and seeing to where it ultimately redirects.

    If accessing the URL results in anything but a 200 or 302
    response, (404, etc.) it will raise a ResourceNotFoundException.
    If the URL returns a 302 response but doesn't redirect anywhere,
    the same error will be raised. Most importantly, if the URL
    resolves to anything at google.com, assumes that it redirected
    to a sign-in page, and returns None.
    """

    def __init__(self):
        self.session = requests.Session()

    def get_drive_resource_url_if_accessible(self, url):

        # Don't allow implicit redirection because we want
        # to manage it a little more carefully than usual
        response = self.session.get(url, allow_redirects=False)
        if response.status_code is requests.codes.ok:
            return url

        elif response.status_code == 302:
            # if there is a redirection, this might mean we are being
            # redirected to the real resource, or to a login page --
            # we need to check out where it's taking us
            return self.get_redirect_location_if_accessible(response)

        else:
            # Here, we got a bad response
            raise ResourceNotFoundException

    def get_redirect_location_if_accessible(self, response):
        """
        Get the redirect location from the given response's
        location header. If the redirect location does not
        require Google account sign-in, return it--this
        should mean it's publicly accessible. Otherwise,
        return None. If there was no location header,
        raise ResourceNotFoundException.
        """

        redirect_location = response.headers.get('location')
        if redirect_location is not None:
            if self.is_accessible_location(redirect_location):
                return redirect_location
        else:
            # When we looked for a redirect location,
            # we didn't find one, which goes against HTTP.
            raise ResourceNotFoundException

    @staticmethod
    def is_accessible_location(url):
        # If the host is google.com, this means they tried to
        # redirect us to a login page, so it's not accessible.
        return LOGIN_REDIRECTION_HOST not in urlsplit(url).hostname.lower()
