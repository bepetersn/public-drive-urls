
"""
    Failing tests because I don't have time,
    but you can at least imagine which units
    of code these tests map to.
"""

from mock import Mock, MagicMock
from unittest import TestCase
from public_drive_urls2 import DriveResourceFinder, ResourceNotFoundException


EXAMPLE_RESOURCE = (
  "https://drive.google.com/file/d/1BBBmV5VdyZLMSqLCA5OY-_I9dyaf379"
  "Qw1UAshvtmbvic7RGmiTBLoCjvxn26TAp-bVwEyFaFEo4kE6X/view?usp=sharing"
)
EXAMPLE_GOOGLE_LOGIN_URL = "https://accounts.google.com/blah/blah/blah"

class DriveDocumentValidatorTestCase(TestCase):

    def test_google_drive_url_is_considered_accessible_if_accessing_returns_200(self):
        finder = DriveResourceFinder()
        finder.session.get = lambda url, **_: Mock(status_code=200)
        result = finder.get_drive_resource_url_if_accessible(EXAMPLE_RESOURCE)
        assert result == EXAMPLE_RESOURCE, (
           'When `drive_resource_is_publicly_accessible` is given '
           'a url, and accessing it gives a 200 response, '
           'we should automatically consider that url accessible')

    def test_google_drive_url_is_not_accessible_if_it_redirects_to_a_google_domain(self):
        finder = DriveResourceFinder()
        finder.session.get = lambda url, **_: Mock(status_code=302, headers={
            'location': EXAMPLE_GOOGLE_LOGIN_URL
        })
        result = finder.get_drive_resource_url_if_accessible(EXAMPLE_RESOURCE)
        assert result is None, (
           'When `drive_resource_is_publicly_accessible` is '
           'given a url, and accessing it gives a 302 response '
           '(redirection), we should consider the redirect '
           'location accessible only if it is not under the '
           "'google' domain. Somehow, we considered this "
           "url accessible, even though it did 'redirect' to"
           " a google login")

    def test_ResourceNotFoundException_occurs_if_a_website_redirects_to_nowhere(self):
        finder = DriveResourceFinder()
        finder.session.get = lambda url, **_: Mock(status_code=302, headers={
            'location': None
        })
        with self.assertRaises(ResourceNotFoundException):
            finder.get_drive_resource_url_if_accessible(EXAMPLE_RESOURCE)


    def test_ResourceNotFoundException_occurs_if_the_url_yields_404(self):
        finder = DriveResourceFinder()
        finder.session.get = lambda url, **_: MagicMock(status_code=404)
        with self.assertRaises(ResourceNotFoundException):
            finder.get_drive_resource_url_if_accessible(EXAMPLE_RESOURCE)
