
import requests
import sys
if sys.version_info[0] < 3:
    from urlparse import urlsplit
else:
    from urllib.parse import urlsplit

LOGIN_REDIRECTION_HOST = 'accounts.google.com'


class ResourceNotFoundException(RuntimeError):
    pass


class NotPublicResourceException(Exception):
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
    the same error will be raised. If the URL resolves to anything
    at accounts.google.com, assumes that it redirected to a sign-in
    page, and raises a NotPublicResourceException. If the URL
    doesn't resolve but redirects over and over, at the 20th time
    it will fail.
    """

    def __init__(self):
        self.session = requests.Session()

    def try_resolve_url(self, url):
        """
        This function takes a Google Drive resource url that
        conforms to one of the formats defined in ACCESS_URLS
        and seeing to where it ultimately redirects.

        If accessing the URL results in anything but a 200
        or 302 response, (404, etc.) it will raise a
        ResourceNotFoundException. If anything funny happens,
        (redirect to nowhere, infinite redirection), the same
        error will be raised.

        Finally, if the URL resolves to anything at
        accounts.google.com, we assume that it redirected to
        a sign-in page, and raise a NotPublicResourceException.
        """

        # Don't allow infinite redirection;
        # 20 is what chrome uses as a limit
        redirection = 0
        while redirection <= 20:

            # Don't allow implicit redirection because we want
            # to manage it a little more carefully than usual
            response = self.session.get(url, allow_redirects=False)
            if response.status_code is requests.codes.ok:

                # If we get a 200 response, this means
                # we have the url to the real resource or
                # possibly, a Google Accounts login page:
                # we have to see which it is
                if self.is_accessible_location(url):
                    return url
                else:
                    raise NotPublicResourceException

            elif response.status_code == 302:
                url = self.get_redirect_location(response)
                redirection += 1

            else:
                # Here, we got a bad response
                raise ResourceNotFoundException

        # If we get into an infinite redirection
        raise ResourceNotFoundException

    def get_redirect_location(self, response):
        """
        Return the redirect location from the given response's
        location header. If there was no location header,
        raise ResourceNotFoundException.
        """

        redirect_location = response.headers.get('location')
        if redirect_location is not None:
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
