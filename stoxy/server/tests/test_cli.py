import logging
import unittest
import os
import requests
import tempfile

from mock import MagicMock

from stoxy.server.tests import config
from stoxy.server.tests.common import server_is_up

try:
    import libcdmi
except ImportError:
    print ('You need to enable libcdmi-python in development mode (see docs)')
    libcdmi = MagicMock()


log = logging.getLogger(__name__)


class TestCLITool(unittest.TestCase):
    tool = 'cdmiclient'
    _endpoint = config.DEFAULT_ENDPOINT
    _mock_up_marker = object()
    _credentials = config.CREDENTIALS
    _base_headers = libcdmi.common.HEADER_CDMI_VERSION

    def setUp(self):
        self._cleanup = []
        fh, self._filename = tempfile.mkstemp(prefix='libcdmi-test-')
        with open(self._filename, 'w') as f:
            f.write('\xff\xff\x12\0\0asdfgkasdlkasdlaskdlas\x91\x01\x03\0\0\0\0')
        os.close(fh)  # allow opening by the library

    def tearDown(self):
        os.unlink(self._filename)

        for method, args, kwargs in reversed(self._cleanup):
            method(*args, **kwargs)

    def addToCleanup(self, method, *args, **kw):
        self._cleanup.append((method, args, kw))

    def mockUp(self, container, object_name, new_value=_mock_up_marker):
        if new_value is self._mock_up_marker:
            new_value = MagicMock()
        old_value = getattr(container, object_name)
        setattr(container, object_name, new_value)
        self.addToCleanup(setattr, container, object_name, old_value)
        return new_value

    def run_cli_with_args(self, raw_args, print_=False):
        parser = libcdmi.cli.create_parser()
        args = parser.parse_args(raw_args)
        response = libcdmi.cli.run(args, print_=print_)
        return response

    def cleanup_object(self, name):
        try:
            requests.delete(self._endpoint + name, auth=self._credentials)
        except Exception:
            pass

    def _make_headers(self, headers, cdmi=True):
        final_headers = {}
        if cdmi:
            final_headers.update(self._base_headers)
        final_headers.update(headers)
        return final_headers

    @unittest.skipUnless(server_is_up(), 'Server is not running!')
    def test_create_container(self):
        raw_args = ['create_container',
                    self._endpoint + '/testcontainer123123/',
                    '-u', ':'.join(self._credentials)]
        response = self.run_cli_with_args(raw_args)
        self.assertEqual('testcontainer123123', response.get('objectName'))

    @unittest.skipUnless(server_is_up(), 'Server is not running!')
    def test_create_object(self):
        raw_args = ['create_object',
                    self._endpoint + '/testobject12312',
                    '-u', ':'.join(self._credentials),
                    '-f', self._filename]
        response = self.run_cli_with_args(raw_args)
        self.assertEqual('testobject12312', response.get('objectName'))

    @unittest.skipUnless(server_is_up(), 'Server is not running!')
    def test_get_object(self):
        raw_args = ['create_object',
                    self._endpoint + '/testobject',
                    '-u', ':'.join(self._credentials),
                    '-f', self._filename]

        response = self.run_cli_with_args(raw_args)
        orig_objectid = response.get('objectID')

        raw_args = ['get',
                    self._endpoint + '/testobject',
                    '-u', ':'.join(self._credentials),
                    '-f', self._filename]

        response = self.run_cli_with_args(raw_args)

        self.assertEqual('testobject', response.get('objectName'))
        self.assertEqual(orig_objectid, response.get('objectID'))

    @unittest.skip('HEAD is not implemented in Stoxy yet')
    @unittest.skipUnless(server_is_up(), 'Server is not running!')
    def test_head_object(self):
        raw_args = ['create_object',
                    self._endpoint + '/testobject',
                    '-u', ':'.join(self._credentials),
                    '-f', self._filename]

        response = self.run_cli_with_args(raw_args)
        orig_objectid = response.get('objectID')

        raw_args = ['head',
                    self._endpoint + '/testobject',
                    '-u', ':'.join(self._credentials),
                    '-f', self._filename]

        response = self.run_cli_with_args(raw_args)

        self.assertEqual('testobject', response.get('objectName'))
        self.assertEqual(orig_objectid, response.get('objectID'))

    @unittest.skipUnless(server_is_up(), 'Server is not running!')
    def test_delete_object_and_container(self):
        raw_args = ['create_container',
                    self._endpoint + '/testcontainertodelete/',
                    '-u', ':'.join(self._credentials)]
        response = self.run_cli_with_args(raw_args)

        raw_args = ['create_object',
                    self._endpoint + '/testcontainertodelete/testobjecttodelete',
                    '-u', ':'.join(self._credentials),
                    '-f', self._filename]
        response = self.run_cli_with_args(raw_args)

        raw_args = ['delete',
                    self._endpoint + '/testcontainertodelete/testobjecttodelete',
                    '-u', ':'.join(self._credentials)]

        response = self.run_cli_with_args(raw_args)

        self.assertEqual(None, response)

        raw_args = ['get',
                    self._endpoint + '/testcontainertodelete/testobjecttodelete',
                    '-u', ':'.join(self._credentials)]

        self.assertRaises(libcdmi.HTTPError, self.run_cli_with_args, raw_args)

        raw_args = ['delete',
                    self._endpoint + '/testcontainertodelete/',
                    '-u', ':'.join(self._credentials),
                    '-f', self._filename]

        response = self.run_cli_with_args(raw_args)

        self.assertEqual(None, response)

        raw_args = ['get',
                    self._endpoint + '/testcontainertodelete/',
                    '-u', ':'.join(self._credentials)]

        self.assertRaises(libcdmi.HTTPError, self.run_cli_with_args, raw_args)

    @unittest.skipUnless(server_is_up(), 'Server is not running!')
    def test_create_object_no_filename_meaningful_error(self):
        raw_args = ['create_object',
                    self._endpoint + '/testobject',
                    '-u', ':'.join(self._credentials)]

        try:
            response = self.run_cli_with_args(raw_args)
        except TypeError:
            self.fail('Wrong arguments not handled correctly')

        self.assertTrue('_error' in response, '_error element was not in response!')
        self.assertEqual('Filename is mandatory with create_object', response['_error'])
