
import requests
import re
import sys
from contextlib import closing
from requests import session
if sys.version_info[0] < 3:
    from urlparse import urlsplit
else:
    from urllib.parse import urlsplit

LOGIN_REDIRECTION_HOST = 'accounts.google.com'
ACCESS_URLS = {
    # These files are accessed through google drive
    'file': "https://drive.google.com/uc?export=download&id={}",

    # These files are accessed through google docs and have a slightly
    # different structure, especially in how you specify an export format
    'document': "https://docs.google.com/document/d/{}/export?format={}",
    'presentation': "https://docs.google.com/presentation/d/{}/export/{}",
    'spreadsheets': "https://docs.google.com/spreadsheets/d/{}/export?format={}",
    'drawings': "https://docs.google.com/drawings/d/{}/export/{}"
}
SHARE_URL_REGEXES = (
    re.compile(
        "https://(?:docs|drive)\.google\.com/"
        # possible domain if using google apps, etc.
        "(?:a/[a-zA-Z0-9\-.]+/)?"
        # below is the document's hosting type
        "(file|document|presentation|spreadsheets|drawings)/d/"
        # below is the drive ID, it can contain letters,
        # digits, hyphens, and underscores
        "([a-zA-Z0-9\-_]+)"
        "/.*"
    ),
    re.compile(
        "https://(?:docs|drive)\.google\.com/"
        "(open)\?id="
        # below is the drive ID
        "([a-zA-Z0-9\-_]+)"
    )
)
DEFAULT_EXPORT_FORMAT = 'pdf'
NATIVE_GOOGLE_DOC_TYPES = {'document', 'presentation',
                           'spreadsheets', 'drawings'}
REDIRECT_LIMIT = 20
OPEN_HOSTING_TYPE = 'open'


class ResourceNotFoundException(RuntimeError):
    pass


class NotPublicResourceException(Exception):
    pass


class DriveResource(object):
    """
    DriveResources represent resources hosted at docs.google.com
    or drive.google.com, and how they can be accessed (assuming
    they are publicly accessible).

    Typically, a user might share their document online using
    a certain URL available from the web UI at these sites
    by an action called sharing (sending a "share url"). While
    the share url is all you need to access these resources if
    you are using a browser, it isn't very helpful if you need
    to download the resource directly, e.g. from a script --
    HTML, javascript and CSS will all get in the way.

    This class allows you to go from a share url to the url
    needed to download your document ("access url").

    Code like the following exemplifies this class's intended usage:

    ```
    r = DriveResource.from_share_url('http://drive.google.com/file/d/foo/')
    access_url = r.get_access_url()

    # print the documents contents
    requests.get(access_url).content
    ```

    Alternatively, if you knew the DriveResource's hosting
    type and id (by doing your own parsing, etc), you could
    instantiate this class more directly as follows:

    ```
    r = DriveResource(id='foo', hosting_type='file')
    access_url = r.get_access_url()
    ```

    """

    def __init__(self, id, hosting_type=OPEN_HOSTING_TYPE, session=None):
        self.id = id
        self.session = session or requests.Session()
        # OPEN_HOSTING_TYPE is a for-the-moment valid
        # hosting_type that basically means we need to
        # guess the real hosting_type
        self.hosting_type = None
        self.hosting_type = hosting_type if \
                hosting_type != OPEN_HOSTING_TYPE \
                else self.guess_hosting_type()

    def guess_hosting_type(self):

        for hosting_type in ACCESS_URLS.keys():
            # Try accessing possible URLs
            # until we find one that works
            with closing(
                self.session.get(
                    self.get_access_url(hosting_type=hosting_type),
                    # We're not going to download these responses,
                    # as we're just looking at status codes.
                    stream=True
                )
            ) as response:
                if response.ok:
                    break
        else:
            # No hosting type found which
            # yields an actual document
            return None

        # Return what worked
        return hosting_type

    def get_access_url(self, hosting_type=None, export_format=None):

        """
            Pre-condition: At least one of self.hosting_type
                           and hosting_type is neither None
                           nor OPEN_HOSTING_TYPE (not valid
                           at this point)
            NOTE: Always specify hosting_type and
                  export_format by keyword argument if you
                  are going to, to avoid ambiguity
        """

        hosting_type = self.hosting_type or hosting_type
        export_format = export_format or DEFAULT_EXPORT_FORMAT

        # this file is hosted at Google Docs, despite
        # being accessible through Google Drive
        if hosting_type in NATIVE_GOOGLE_DOC_TYPES:

            return ACCESS_URLS[hosting_type]\
                .format(self.id, export_format)

        # this file is actually hosted by the Google Drive service
        else:
            return ACCESS_URLS[hosting_type].format(self.id)

    @classmethod
    def from_share_url(cls, share_url, session=session):
        for regex in SHARE_URL_REGEXES:
            match = regex.match(share_url)
            if match is not None:
                drive_id = match.group(2)
                hosting_type = match.group(1)
                if None not in (drive_id, hosting_type):
                    return cls(drive_id, hosting_type, session=session)


class DriveURLResolver(object):

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

    The main use case here is knowing when a NotPublicResourceException
    has occurred, because this is a very specific user error that
    can be handled in an application flow.
    """

    def __init__(self, session=None):
        self.session = session or requests.Session()

    def resolve_from_share_url(
                self, share_url, export_format=None):
        resource = DriveResource.from_share_url(share_url)
        access_url = resource.get_access_url(export_format=export_format)
        return self.resolve_from_access_url(access_url)

    def resolve_from_access_url(self, url):
        """
        This function takes a Google Drive resource url that
        conforms to one of the formats defined in ACCESS_URLS
        and returns to where it ultimately redirects.

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
        while redirection <= REDIRECT_LIMIT:

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
                # Here, we got a bad response, i.e. 4xx
                # and 5xx status codes
                raise ResourceNotFoundException

        # Here, we got into an infinite redirection
        raise ResourceNotFoundException

    @staticmethod
    def get_redirect_location(response):
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
        # If the host is accounts.google.com, this means they tried to
        # redirect us to a login page, so it's not accessible.
        return LOGIN_REDIRECTION_HOST not in urlsplit(url).hostname.lower()
