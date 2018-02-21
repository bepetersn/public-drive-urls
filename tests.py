
"""
    Failing tests because I don't have time,
    but you can at least imagine which units
    of code these tests map to.
"""

import requests
from mock import Mock, MagicMock
from unittest import TestCase
from public_drive_urls2 import DriveURLResolver, DriveResource, \
        ResourceNotFoundException, NotPublicResourceException, \
        ACCESS_URLS, DEFAULT_EXPORT_FORMAT

EXAMPLE_RESOURCE_1_ID = (
    "1BBBmV5VdyZLMSqLCA5OY-_I9dyaf379"
    "Qw1UAshvtmbvic7RGmiTBLoCjvxn26TAp-bVwEyFaFEo4kE6X"
)
EXAMPLE_RESOURCE_1_HOSTING_TYPE = 'file'
EXAMPLE_RESOURCE_1 = (
    "https://drive.google.com/{}/d/{}/view?usp=sharing".format(
        EXAMPLE_RESOURCE_1_HOSTING_TYPE,
        EXAMPLE_RESOURCE_1_ID
    )
)
EXAMPLE_RESOURCE_2_HOSTING_TYPE = 'open'
EXAMPLE_RESOURCE_2_ID = 'blahblahblah'
EXAMPLE_RESOURCE_2 = (
    "https://docs.google.com/{}?id={}".format(
        EXAMPLE_RESOURCE_2_HOSTING_TYPE,
        EXAMPLE_RESOURCE_2_ID
    )
)
EXAMPLE_GOOGLE_LOGIN_URL = "https://accounts.google.com/blah/blah/blah"


class DriveResourceTestCase(TestCase):

    def test_when_session_returns_ok_resp_on_certain_type_access_url_follows(self):
        session = requests.Session()
        self.our_type = 'document'

        def mock_get(url, **kwargs):
            return Mock(ok=self.our_type in url)

        session.get = mock_get
        test_id = '12345'
        resource = DriveResource(test_id, 'open', session=session)
        self.assertEqual(
            resource.get_access_url(),
            ACCESS_URLS[resource.hosting_type].format(
                test_id, DEFAULT_EXPORT_FORMAT
            )
        )

        # Try again with a different hosting_type so that we
        # know it isn't just always returning that type
        self.our_type = 'spreadsheets'
        resource = DriveResource(test_id, 'open', session=session)
        self.assertEqual(
            resource.get_access_url(),
            ACCESS_URLS[resource.hosting_type].format(
                test_id, DEFAULT_EXPORT_FORMAT
            )
        )

    def test_when_session_returns_ok_resp_on_certain_type_guess_hosting_type_guesses_those_types(self):
        session = requests.Session()
        self.our_type = 'document'

        def mock_get(url, **kwargs):
            return Mock(ok=self.our_type in url)

        session.get = mock_get
        test_id = '12345'
        resource = DriveResource(test_id, 'open', session=session)
        self.assertEqual(resource.hosting_type, self.our_type)

        self.our_type = 'spreadsheets'
        resource = DriveResource(test_id, 'open', session=session)
        self.assertEqual(resource.hosting_type, self.our_type)

    def test_get_access_url_returns_given_id_as_part_of_url(self):
        session = requests.Session()
        self.our_type = 'document'

        def mock_get(url, **kwargs):
            return Mock(ok=self.our_type in url)

        session.get = mock_get
        test_id = '12345'
        resource = DriveResource(test_id, 'open', session=session)
        self.assertIn(
            test_id,
            resource.get_access_url()
        )

    def test_get_access_url_returns_specified_export_format_as_part_of_url(self):
        session = requests.Session()
        self.our_type = 'document'

        def mock_get(url, **kwargs):
            return Mock(ok=self.our_type in url)

        session.get = mock_get
        self.our_type = 'spreadsheets'
        test_id = '12345'
        test_export_format = 'png'
        resource = DriveResource(test_id, 'open', session=session)
        self.assertEqual(resource.hosting_type, self.our_type)
        self.assertIn(
            test_export_format,
            resource.get_access_url(export_format=test_export_format)
        )

    def test_get_access_url_returns_default_export_format_as_default(self):
        session = requests.Session()
        self.our_type = 'document'

        def mock_get(url, **kwargs):
            return Mock(ok=self.our_type in url)

        session.get = mock_get
        self.our_type = 'spreadsheets'
        test_id = '12345'
        resource = DriveResource(test_id, 'open', session=session)
        self.assertEqual(resource.hosting_type, self.our_type)
        self.assertIn(
            DEFAULT_EXPORT_FORMAT,
            resource.get_access_url()
        )

    def test_instiantiating_resource_from_share_url_gets_id_and_hosting_type_twice(self):
        session = requests.Session()
        session.get = MagicMock()

        resource = DriveResource.from_share_url(
            EXAMPLE_RESOURCE_1, session=session
        )
        self.assertEqual(resource.id, EXAMPLE_RESOURCE_1_ID)
        self.assertEqual(resource.hosting_type, EXAMPLE_RESOURCE_1_HOSTING_TYPE)

        resource = DriveResource.from_share_url(
            EXAMPLE_RESOURCE_2, session=session
        )
        self.assertEqual(resource.id, EXAMPLE_RESOURCE_2_ID)
        # 'open' hosting_type becomes whatever type we guess
        # that works first--in this case we don't care--but
        # it shouldn't be 'open'
        self.assertNotEqual(resource.hosting_type, EXAMPLE_RESOURCE_2_HOSTING_TYPE)


class DriveURLResolverTestCase(TestCase):

    def test_google_drive_url_is_considered_accessible_if_accessing_returns_200(self):
        resolver = DriveURLResolver()
        resolver.session.get = lambda url, **_: Mock(status_code=200)
        result = resolver.resolve_from_access_url(EXAMPLE_RESOURCE_1)
        assert result == EXAMPLE_RESOURCE_1, (
           'When `drive_resource_is_publicly_accessible` is given '
           'a url, and accessing it gives a 200 response, '
           'we should automatically consider that url accessible')

    def test_NotPublicResourceException_occurs_if_it_redirects_to_accounts_google_domain(self):
        resolver = DriveURLResolver()

        # Use a mutable value so we can access and persist
        # changes in py2; in py3, we'd use 'nonlocal'
        # keyword in enclosed function
        num_get_calls = [0]

        def mock_get(url, **kwargs):
            num_get_calls[0] += 1
            if num_get_calls[0] == 1:
                return Mock(status_code=302, headers={
                    'location': EXAMPLE_GOOGLE_LOGIN_URL
                })
            if num_get_calls[0] == 2:
                return Mock(status_code=200)

        resolver.session.get = mock_get

        with self.assertRaises(NotPublicResourceException):

            # When `drive_resource_is_publicly_accessible` is
            # given a url, and accessing it gives a 302 response
            # (redirection), we should consider the redirect
            # location accessible only if it is not under the
            # 'accounts.google' domain.

            result = resolver.resolve_from_access_url(EXAMPLE_RESOURCE_1)

    def test_NotPublicResourceException_occurs_if_it_redirects_once_then_redirects_to_accounts_google_domain(self):
        resolver = DriveURLResolver()
        num_get_calls = [0]

        def mock_get(url, **kwargs):
            num_get_calls[0] += 1
            if num_get_calls[0] == 1:
                return Mock(status_code=302, headers={
                    'location': 'http://example.com'
                })
            if num_get_calls[0] == 2:
                return Mock(status_code=302, headers={
                    'location': EXAMPLE_GOOGLE_LOGIN_URL
                })
            if num_get_calls[0] == 3:
                return Mock(status_code=200)

        resolver.session.get = mock_get
        with self.assertRaises(NotPublicResourceException):
            resolver.resolve_from_access_url(EXAMPLE_RESOURCE_1)

    def test_ResuorceNotFoundException_occurs_if_it_redirects_forever(self):

        resolver = DriveURLResolver()
        resolver.session.get = lambda url, **_: Mock(status_code=302, headers={
            'location': 'http://example.com'
        })
        with self.assertRaises(ResourceNotFoundException):
            resolver.resolve_from_access_url(EXAMPLE_RESOURCE_1)
    def test_ResourceNotFoundException_occurs_if_a_website_redirects_to_nowhere(self):
        resolver = DriveURLResolver()
        resolver.session.get = lambda url, **_: Mock(status_code=302, headers={

            'location': None
        })
        with self.assertRaises(ResourceNotFoundException):
            resolver.resolve_from_access_url(EXAMPLE_RESOURCE_1)

    def test_ResourceNotFoundException_occurs_if_the_url_yields_404(self):
        resolver = DriveURLResolver()
        resolver.session.get = lambda url, **_: MagicMock(status_code=404)
        with self.assertRaises(ResourceNotFoundException):
            resolver.resolve_from_access_url(EXAMPLE_RESOURCE_1)
