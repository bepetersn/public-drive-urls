
"""
Use this module to turn a Google Drive-provided
share url for a public file into a url pointing to
the actual resource. Raises exceptions if the URL
either doesn't resolve, or appears to point to a
file that isn't publicly accessible.
"""

from urlparse import urlsplit
import requests
import re

LOGIN_REDIRECTION_HOST = 'google.com'

ACCESS_URLS = {
    # These files are accessed through google drive
    'file': "https://drive.google.com/uc?export=download&id={}",

    # These files are accessed through google docs and have a slightly
    # different structure, especially in how you specify an export format
    'document': "https://docs.google.com/document/d/{}/export?format={}",
    'presentation': "https://docs.google.com/presentation/d/{}/export/{}",
    'spreadsheets': "https://docs.google.com/spreadsheets/d/{}/export?format={}"
}


SHARE_URL_REGEXES = (
    re.compile(
        "https://(?:docs|drive)\.google\.com/"
        # possible domain if using google apps, etc.
        "(?:a/[a-zA-Z0-9\-.]+/)?"
        # below is the document's hosting type
        "(file|document|presentation|spreadsheets)/d/"
        # below is the drive ID, it can contain letters,
        # digits, hyphens, and underscores
        "([a-zA-Z0-9\-_]+)"
        "/.*"
    ),
    re.compile(
        "https://docs\.google\.com/"
        "(open)\?id="
        # below is the drive ID
        "([a-zA-Z0-9\-_]+)"
    )
)


NATIVE_GOOGLE_DOC_TYPES = {'document', 'presentation', 'spreadsheets', 'drawings'}


# Define some export formats in which to 
# to retrieve documents from Google Drive 
class ExportFormats(object):
    PDF = 'pdf'
    DOCX = 'docx'
    PNG = 'png'
    DEFAULT = 'pdf'


class NotPublicResourceException(Exception):
    pass


class DriveDocumentResource(object):

    """
    This class is primarily responsible for knowing how
    to turn a URL provided by the Google Drive service
    for the purpose of sharing, into a URL of one of the
    formats defined in ACCESS_URLS, provided by Google
    for exporting documents.
    """

    def __init__(self, drive_id, hosting_type=None, export_format=None):
        self.drive_id = drive_id
        # "open" hosting type really means we don't
        # know what type it is, & should guess
        self.hosting_type = hosting_type if \
            hosting_type != 'open' else self.guess_hosting_type()
        self.export_format = None
        self.access_url = self.get_access_url(
            self.hosting_type, export_format
        )

    def guess_hosting_type(self):
        for hosting_type in NATIVE_GOOGLE_DOC_TYPES:
            # Try accessing possible URLs
            # until we find one that works
            response = requests.get(self.get_access_url(hosting_type))
            if response.status_code == requests.codes.ok:
                break
        else:
            # No hosting type found which
            # yields an actual document
            return None

        # Return what worked
        return hosting_type

    def get_access_url(self, hosting_type=None, export_format=None):

        # this file is hosted at Google Docs, despite
        # being accessible through Google Drive
        if hosting_type in NATIVE_GOOGLE_DOC_TYPES:

            # If it's a native Google Doc, we can choose
            # an export format; otherwise, it comes out
            # as it was stored, and we don't guess that.
            self.export_format = self.get_export_format(export_format)

            return ACCESS_URLS[hosting_type]\
                .format(self.drive_id, self.export_format)

        # this file is actually hosted by the Google Drive service
        else:
            return ACCESS_URLS[hosting_type]\
                .format(self.drive_id)

    @staticmethod
    def get_export_format(format_override=None):
        if format_override is None:
            return ExportFormats.DEFAULT
        else:
            return format_override

    @classmethod
    def from_share_url(cls, share_url, export_format=None):
        for regex in SHARE_URL_REGEXES:
            # parse drive id and document type from share url
            match = regex.match(share_url)
            if match is not None:
                drive_id = match.group(2)
                hosting_type = match.group(1)
                if drive_id is not None and hosting_type is not None:
                    return DriveDocumentResource(drive_id, hosting_type, export_format)
                else:
                    # if we're here, either the drive_id or hosting_type
                    # weren't able to be parsed
                    pass
            else:
                # If we're here, we just couldn't find a valid Google Drive
                # share URL, though it might indicate a parse error too.
                pass


class DriveDocumentFinder(object):

    """
    This class is responsible primarily for taking any URL
    that conforms to the formats defined by the ACCESS_URLS
    variable and seeing where it redirects to. There is also
    a method for turning a URL provided by Google Drive for
    sharing directly into its actual location, for which
    this class delegates to the DriveDocumentResource class.

    If we can't parse the share URL, return None. If the URL
    doesn't redirect, (i.e. returns 200, 404, etc.) it will
    raise a BadUrlException. If the URL resolves to anything
    at google.com, assumes that it redirected to a sign-in
    page, and raises NotPublicResourceException.

    The `from_share_url` method is the primary interface of this
    class, and is responsible for returning a `DriveDocumentResource`.
    """

    LOGIN_REDIRECTION_HOST = 'google.com'

    def from_share_url(self, shared_url, export_format=None):
        resource = DriveDocumentResource.from_share_url(shared_url, export_format)
        if resource is not None:
            return self.try_resolve_url(resource.access_url)
        else:
            return None

    def try_resolve_url(self, access_url):
        response = requests.get(access_url, allow_redirects=False)
        # if there is a redirection, this might mean we are being
        # redirected to the real resource, or to a login page
        if response.status_code == 302:
            return self._find_redirect_location(response)
        elif response.status_code == 200:
            # It's only acceptable to get a 200 if we did not
            # allow redirection, so there are no false positives;
            # in this case, we already have the real URL.
            return access_url
        else:
            # Here, we got a bad response
            return None

    def _find_redirect_location(self, response):
        possible_url = response.headers.get('location')
        if possible_url is not None:
            if self._is_valid_redirect_url(possible_url):
                return possible_url
            else:
                raise NotPublicResourceException
        else:
            # Here there was a weird error, which is
            # that when we looked for a redirect location,
            # we didn't find one.
            return None

    @staticmethod
    def _is_valid_redirect_url(url):
        # If the host is google.com, this means they tried to
        # redirect us to a login page, so it's not accessible.
        return LOGIN_REDIRECTION_HOST not in urlsplit(url).hostname.lower()
