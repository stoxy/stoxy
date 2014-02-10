import base64
import json
import logging
import unittest
import os
import requests
import tempfile

from mock import MagicMock

import config

from opennode.oms.config import get_config

from stoxy.server.tests.common import server_is_up
from stoxy.server.tests.common import NotThere


try:
    import libcdmi
except ImportError:
    print ('You need to enable libcdmi-python in development mode (see docs)')
    libcdmi = MagicMock()


log = logging.getLogger(__name__)


class TestSwift(unittest.TestCase):
    _endpoint = config.DEFAULT_ENDPOINT
    _mock_up_marker = object()
    _credentials = config.CREDENTIALS
    _base_headers = libcdmi.common.HEADER_CDMI_VERSION

    def setUp(self):
        self._cleanup = []
        fh, self._filename = tempfile.mkstemp(prefix='libcdmi-test-')
        with open(self._filename, 'w') as f:
            f.write('\xff\x12\0\0asdfgkasdlkasdlaskdlas\x91\x01\x03\0\0\0\0')
        os.close(fh)  # allow opening by the library

    def tearDown(self):
        os.unlink(self._filename)

        for method, args, kwargs in reversed(self._cleanup):
            method(*args, **kwargs)

    def addToCleanup(self, method, *args, **kw):
        self._cleanup.append((method, args, kw))

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

    @unittest.skipUnless(server_is_up(), 'Requires a running Stoxy server')
    def test_create_and_get_container(self):
        c = libcdmi.open(self._endpoint, credentials=self._credentials)

        self.addToCleanup(self.cleanup_object, '/swift')

        self.cleanup_object('/swift')
        container_create = c.create_container('/swift',
                                              metadata={
                                                  'stoxy_backend': 'swift',
                                                  'stoxy_backend_base':
                                                  'swift.example.com/v1.0/account/container/'
                                              })
        container_get = c.get('/swift/', accept=libcdmi.common.CDMI_CONTAINER)

        self.assertEqual(dict, type(container_create))
        self.assertEqual(dict, type(container_get))

        for key, value in container_create.iteritems():
            self.assertEqual(value, container_get.get(key, NotThere),
                             'Expected: %s, but received: %s in %s' %
                             (value, container_get.get(key, NotThere), key))

    @unittest.skipUnless(server_is_up(), 'Requires a running Stoxy server')
    def test_swift_create_object(self):
        c = libcdmi.open(self._endpoint, credentials=self._credentials)
        self.addToCleanup(self.cleanup_object, '/swift/')
        self.addToCleanup(self.cleanup_object, '/swift/testobject')
        c.create_container('/swift',
                           metadata={'stoxy_backend': 'swift',
                                     'stoxy_backend_base': 'swift.example.com/v1.0/account/container/'})

        data = {'metadata': {'event name': 'SNIA SDC 2013',
                             'event location': 'Santa Clara, CA'},
                'mimetype': 'text/plain'}

        object_headers = self._make_headers({'Accept': libcdmi.common.CDMI_OBJECT,
                                             'Content-Type': libcdmi.common.CDMI_OBJECT,
                                             'X-Auth-Token': 'TEST'})

        with open(self._filename, 'rb') as input_file:
            try:
                content = input_file.read()
                unicode(content, 'utf-8')
                data['valuetransferencoding'] = 'utf-8'
            except UnicodeDecodeError:
                input_file.seek(0)
                content = base64.b64encode(input_file.read())
                data['valuetransferencoding'] = 'base64'

        data.update({'value': content})

        response = requests.put(self._endpoint + '/swift/testobject',
                                json.dumps(data),
                                auth=self._credentials,
                                headers=object_headers)

        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual(response.headers['X-CDMI-Specification-Version'], '1.0.1')
        self.assertEqual(response.headers['Content-Type'], 'application/cdmi-object')

        result_data = response.json()
        self.assertEqual('application/cdmi-object', result_data['objectType'])
        self.assertEqual('testobject', result_data['objectName'])

        response = requests.get(self._endpoint + '/swift/testobject',
                                auth=self._credentials,
                                headers=object_headers)

        result_data = response.json()
        self.assertTrue('value' in result_data, 'No value field in response: %s' % result_data.keys())
        self.assertTrue(len(result_data['value']) > 0, 'Result value length is zero!')
        self.assertEqual(base64.b64decode(content),
                         base64.b64decode(result_data['value']))
        self.assertEqual(content, result_data['value'])
