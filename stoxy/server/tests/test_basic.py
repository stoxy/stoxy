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
from stoxy.server.tests.common import libcdmi_available
from stoxy.server.tests.common import NotThere


try:
    import libcdmi
except ImportError:
    print ('You need to enable libcdmi-python in development mode (see docs)')
    libcdmi = MagicMock()


log = logging.getLogger(__name__)


class TestBasic(unittest.TestCase):
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

    def mockUp(self, container, object_name, new_value=_mock_up_marker):
        if new_value is self._mock_up_marker:
            new_value = MagicMock()
        old_value = getattr(container, object_name)
        setattr(container, object_name, new_value)
        self.addToCleanup(setattr, container, object_name, old_value)
        return new_value

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

    @unittest.skipUnless(libcdmi_available(), 'libcdmi is not in the path')
    @unittest.skipUnless(server_is_up(), 'Requires a running Stoxy server')
    def test_update_container(self):
        c = libcdmi.open(self._endpoint, credentials=self._credentials)

        self.addToCleanup(self.cleanup_object, '/testcontainer')
        container_1 = c.create_container('/testcontainer')
        container_2 = c.update_container('/testcontainer', metadata={'owner': 'nobody'})
        container_get = c.get('/testcontainer/', accept=libcdmi.common.CDMI_CONTAINER)

        self.assertEqual(dict, type(container_2))
        self.assertEqual(dict, type(container_1))
        self.assertEqual(dict, type(container_get))

        for key, value in container_2.iteritems():
            self.assertEqual(value, container_get.get(key, NotThere),
                             'Expected: %s, but received: %s in %s' %
                             (value, container_get.get(key, NotThere), key))

    @unittest.skipUnless(libcdmi_available(), 'libcdmi is not in the path')
    @unittest.skipUnless(server_is_up(), 'Requires a running Stoxy server')
    def test_create_and_get_container(self):
        c = libcdmi.open(self._endpoint, credentials=self._credentials)

        self.addToCleanup(self.cleanup_object, '/testcontainer')

        self.cleanup_object('/testcontainer')
        container_create = c.create_container('/testcontainer', metadata={'test': 'blah'})
        container_get = c.get('/testcontainer/', accept=libcdmi.common.CDMI_CONTAINER)

        self.assertEqual(dict, type(container_create))
        self.assertEqual(dict, type(container_get))

        for key, value in container_create.iteritems():
            self.assertEqual(value, container_get.get(key, NotThere),
                             'Expected: %s, but received: %s in %s' %
                             (value, container_get.get(key, NotThere), key))

    @unittest.skipUnless(server_is_up(), 'Requires a running Stoxy server')
    def test_create_container_detailed(self):
        self.addToCleanup(self.cleanup_object, '/testcontainer')
        headers = self._make_headers({'Accept': libcdmi.common.CDMI_CONTAINER,
                                      'Content-Type': libcdmi.common.CDMI_CONTAINER})
        data = {'metadata': {}}

        response = requests.put(self._endpoint + '/testcontainer',
                                json.dumps(data),
                                auth=self._credentials,
                                headers=headers)

        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual(response.headers['X-CDMI-Specification-Version'], '1.0.1')
        self.assertEqual(response.headers['Content-Type'], 'application/cdmi-container')

        result_data = response.json()
        self.assertEqual('application/cdmi-container', result_data['objectType'])
        self.assertEqual('testcontainer', result_data['objectName'])

    @unittest.skipUnless(libcdmi_available(), 'libcdmi is not in the path')
    @unittest.skipUnless(server_is_up(), 'Requires a running Stoxy server')
    def test_create_object_detailed(self):
        c = libcdmi.open(self._endpoint, credentials=self._credentials)
        self.addToCleanup(self.cleanup_object, '/testcontainer/')
        self.addToCleanup(self.cleanup_object, '/testcontainer/testobject')
        c.create_container('/testcontainer/')

        data = {'metadata': {},
                'mimetype': 'text/plain'}

        object_headers = self._make_headers({'Accept': libcdmi.common.CDMI_OBJECT,
                                             'Content-Type': libcdmi.common.CDMI_OBJECT})

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

        response = requests.put(self._endpoint + '/testcontainer/testobject',
                                json.dumps(data),
                                auth=self._credentials,
                                headers=object_headers)

        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual(response.headers['X-CDMI-Specification-Version'], '1.0.1')
        self.assertEqual(response.headers['Content-Type'], 'application/cdmi-object')

        result_data = response.json()
        self.assertEqual('application/cdmi-object', result_data['objectType'])
        self.assertEqual('testobject', result_data['objectName'])

        response = requests.get(self._endpoint + '/testcontainer/testobject',
                                auth=self._credentials,
                                headers=object_headers)

        result_data = response.json()
        self.assertTrue('value' in result_data, result_data)
        self.assertTrue(len(result_data['value']) > 0, result_data)
        self.assertEqual(base64.b64decode(content),
                         base64.b64decode(result_data['value']))
        self.assertEqual(content, result_data['value'])

    @unittest.skipUnless(libcdmi_available(), 'libcdmi is not in the path')
    @unittest.skipUnless(server_is_up(), 'Requires a running Stoxy server')
    def test_create_object_non_cdmi_detailed(self):
        c = libcdmi.open(self._endpoint, credentials=self._credentials)
        self.addToCleanup(self.cleanup_object, '/testcontainer/')
        self.addToCleanup(self.cleanup_object, '/testcontainer/testobject')
        c.create_container('/testcontainer/')

        object_headers = self._make_headers({'Accept': libcdmi.common.CDMI_OBJECT,
                                             'Content-Type': 'application/binary'},
                                            cdmi=False)

        with open(self._filename, 'rb') as input_file:
            content = input_file.read()

        response = requests.put(self._endpoint + '/testcontainer/testobject',
                                content,
                                auth=self._credentials,
                                headers=object_headers)

        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual(response.headers['X-CDMI-Specification-Version'], '1.0.1')
        self.assertEqual(response.headers['Content-Type'], 'application/cdmi-object')

        result_data = response.text  # Response body is not required
        self.assertTrue(len(result_data) == 0)

    @unittest.skipUnless(libcdmi_available(), 'libcdmi is not in the path')
    @unittest.skipUnless(server_is_up(), 'Requires a running Stoxy server')
    def test_get_object_non_cdmi_detailed(self):
        c = libcdmi.open(self._endpoint, credentials=self._credentials)
        self.addToCleanup(self.cleanup_object, '/testcontainer/')
        self.addToCleanup(self.cleanup_object, '/testcontainer/testobject')
        c.create_container('/testcontainer/')

        object_headers = self._make_headers({'Accept': libcdmi.common.CDMI_OBJECT,
                                             'Content-Type': 'application/octet-stream'},
                                            cdmi=False)

        with open(self._filename, 'rb') as input_file:
            content = input_file.read()

        response = requests.put(self._endpoint + '/testcontainer/testobject',
                                content,
                                auth=self._credentials,
                                headers=object_headers)

        self.assertEqual(200, response.status_code, response.text)

        # TODO: test non-CDMI request optional Range header functionality
        noncdmi_headers = {'Range': '10-15'}
        response = requests.get(self._endpoint + '/testcontainer/testobject',
                                auth=self._credentials,
                                headers=noncdmi_headers)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.text), 5, response.text)
        self.assertEqual(response.text, content[10:15])
        self.assertEqual(response.headers['content-type'], object_headers['Content-Type'])

        # TODO: test non-CDMI request optional Range header functionality
        noncdmi_headers = {'Range': '1-6'}
        response = requests.get(self._endpoint + '/testcontainer/testobject',
                                auth=self._credentials,
                                headers=noncdmi_headers)

        self.assertEqual(5, len(response.text))
        self.assertEqual(response.text, content[1:6])
        self.assertEqual(response.headers['content-type'], object_headers['Content-Type'])

    @unittest.skipUnless(libcdmi_available(), 'libcdmi is not in the path')
    @unittest.skipUnless(server_is_up(), 'Requires a running Stoxy server')
    def test_delete_object(self):
        c = libcdmi.open(self._endpoint, credentials=self._credentials)
        self.addToCleanup(self.cleanup_object, '/testcontainer/')
        self.addToCleanup(self.cleanup_object, '/testcontainer/testobject')
        c.create_container('/testcontainer/')
        object_headers = self._make_headers({'Accept': libcdmi.common.CDMI_OBJECT,
                                             'Content-Type': 'application/octet-stream'})

        with open(self._filename, 'rb') as input_file:
            content = input_file.read()

        response = requests.put(self._endpoint + '/testcontainer/testobject',
                                content,
                                auth=self._credentials,
                                headers=object_headers)

        self.assertEqual(200, response.status_code, response.text)

        # XXX: when used from the unit test, get_config() gives only the OMS config, so need to specify
        # the base path in OMS config too
        stoxy_filepath = '%s/%s' % (get_config().getstring('store', 'file_base_path', '/tmp'),
                                    'testobject')

        self.assertTrue(os.path.exists(stoxy_filepath),
                        'File "%s" does not exist after creation of model object!' % stoxy_filepath)

        delete_response = requests.delete(self._endpoint + '/testcontainer/testobject',
                                          auth=self._credentials,)
        self.assertEqual(200, delete_response.status_code, delete_response.text)

        response = requests.get(self._endpoint + '/testcontainer/testobject',
                                auth=self._credentials,)
        self.assertEqual(404, response.status_code, 'Object was not deleted!')

        self.assertTrue(not os.path.exists(stoxy_filepath),
                        'File "%s" exists after deletion of model object!' % stoxy_filepath)

    @unittest.skipUnless(config.FULL_TEST, 'Known to be broken: TODO: implement custom arguments parsing')
    @unittest.skipUnless(libcdmi_available(), 'libcdmi is not in the path')
    @unittest.skipUnless(server_is_up(), 'Requires a running Stoxy server')
    def test_get_specific_fields_using_get_cdmi_params(self):
        c = libcdmi.open(self._endpoint, credentials=self._credentials)
        self.addToCleanup(self.cleanup_object, '/testcontainer/')
        self.addToCleanup(self.cleanup_object, '/testcontainer/testobject')
        c.create_container('/testcontainer/')
        object_headers = self._make_headers({'Accept': libcdmi.common.CDMI_OBJECT,
                                             'Content-Type': 'application/octet-stream'})

        with open(self._filename, 'rb') as input_file:
            content = input_file.read()

        response = requests.put(self._endpoint + '/testcontainer/testobject',
                                content,
                                auth=self._credentials,
                                headers=object_headers)

        self.assertEqual(200, response.status_code, response.text)

        response = requests.get(self._endpoint + '/testcontainer/testobject?objectID;parentURI;value:1-6',
                                auth=self._credentials,
                                headers=object_headers)

        self.assertEqual(200, response.status_code, response.text)
        self.assertTrue(len(response.text) > 0, 'Response was empty!')
        data = response.json()
        self.assertEqual(3, len(data), 'There were <> 3 keys in the response data: %s' % response.json())
        self.assertTrue('value' in data.keys(), 'value is not in data (%s)!' % data)
        self.assertTrue('objectID' in data.keys(), 'objectID is not in data (%s)!' % data)
        self.assertTrue('parentURI' in data.keys(), 'parentURI is not in data (%s)!' % data)
        self.assertEqual('EgAAYXM=', data['value'], data['value'])
        self.assertEqual(content[1:6], base64.b64decode(data['value']))

    @unittest.skipUnless(libcdmi_available(), 'libcdmi is not in the path')
    @unittest.skipUnless(server_is_up(), 'Requires a running Stoxy server')
    def test_get_specific_fields_using_get_http_params(self):
        c = libcdmi.open(self._endpoint, credentials=self._credentials)
        self.addToCleanup(self.cleanup_object, '/testcontainer/')
        self.addToCleanup(self.cleanup_object, '/testcontainer/testobject')
        c.create_container('/testcontainer/')
        object_headers = self._make_headers({'Accept': libcdmi.common.CDMI_OBJECT,
                                             'Content-Type': 'application/octet-stream'})

        with open(self._filename, 'rb') as input_file:
            content = input_file.read()

        response = requests.put(self._endpoint + '/testcontainer/testobject',
                                content,
                                auth=self._credentials,
                                headers=object_headers)

        self.assertEqual(200, response.status_code, response.text)

        response = requests.get(self._endpoint + ('/testcontainer/testobject?'
                                                  'objectID=true&parentURI=true&value=1&value=6'),
                                auth=self._credentials,
                                headers=object_headers)

        self.assertEqual(200, response.status_code, response.text)
        self.assertTrue(len(response.text) > 0, 'Response was empty!')
        data = response.json()
        self.assertEqual(3, len(data), 'There were <> 3 keys in the response data: %s' % response.json())
        self.assertTrue('value' in data.keys(), 'value is not in data (%s)!' % data)
        self.assertTrue('objectID' in data.keys(), 'objectID is not in data (%s)!' % data)
        self.assertTrue('parentURI' in data.keys(), 'parentURI is not in data (%s)!' % data)
        self.assertEqual(content[1:6], base64.b64decode(data['value']))
        self.assertEqual('EgAAYXM=', data['value'], 'Value in response did not match the requested range')

    @unittest.skipUnless(libcdmi_available(), 'libcdmi is not in the path')
    @unittest.skipUnless(server_is_up(), 'Requires a running Stoxy server')
    def test_cdmi_objectid(self):
        c = libcdmi.open(self._endpoint, credentials=self._credentials)
        self.addToCleanup(self.cleanup_object, '/testcontainer/')
        self.addToCleanup(self.cleanup_object, '/testcontainer/testobject')
        c.create_container('/testcontainer/')

        data = {'metadata': {},
                'mimetype': 'text/plain'}

        object_headers = self._make_headers({'Accept': libcdmi.common.CDMI_OBJECT,
                                             'Content-Type': libcdmi.common.CDMI_OBJECT})

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

        response = requests.put(self._endpoint + '/testcontainer/testobject',
                                json.dumps(data),
                                auth=self._credentials,
                                headers=object_headers)

        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual(response.headers['X-CDMI-Specification-Version'], '1.0.1')
        self.assertEqual(response.headers['Content-Type'], 'application/cdmi-object')

        result_data = response.json()
        self.assertEqual('application/cdmi-object', result_data['objectType'])
        self.assertEqual('testobject', result_data['objectName'])

        self.assertTrue(len(response.text) > 0, 'Response was empty!')
        data = response.json()

        self.assertTrue('objectID' in data.keys(), 'objectID is not in data (%s)!' % data)

        response = requests.get(self._endpoint + ('/cdmi_objectid/%s/' % data['objectID']),
                                auth=self._credentials,
                                headers=object_headers)

        self.assertEqual(200, response.status_code, response.text)
        self.assertTrue(len(response.text) > 0, 'Response was empty!')
        data = response.json()
        self.assertEqual(9, len(data), 'There were <> 9 keys in the response data: %s' % response.json())
        self.assertTrue('value' in data.keys(), 'value is not in data (%s)!' % data)
        self.assertTrue('objectID' in data.keys(), 'objectID is not in data (%s)!' % data)
        self.assertTrue('parentURI' in data.keys(), 'parentURI is not in data (%s)!' % data)
        self.assertEqual(base64.b64decode(content), base64.b64decode(data['value']), content)
