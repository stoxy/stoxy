import json
import logging
import unittest
import os
import requests
import tempfile

from mock import MagicMock

try:
    import libcdmi
except ImportError:
    print ('To test, you need to enable libcdmi-python in development mode (see docs)')
    libcdmi = MagicMock()


log = logging.getLogger(__name__)
_server_is_up = False


DEFAULT_ENDPOINT = 'http://localhost:8080/storage'


def server_is_up():
    try:
        response = requests.get(DEFAULT_ENDPOINT, auth=('admin', 'admin'))
    except requests.ConnectionError:
        _server_is_up = False
        log.debug('Server is down: connection error!')
    else:
        if response.status_code >= 400:
            _server_is_up = False
            log.debug('Server returned status code %s' % response.status_code)
        elif type(libcdmi) is MagicMock:
            _server_is_up = False
            log.debug('libcdmi-python is unavailable -- server is "down"')
        else:
            _server_is_up = True
            log.debug('Server is up!')
    return _server_is_up


NotThere = '<NotThere>'


class TestBasic(unittest.TestCase):
    _endpoint = DEFAULT_ENDPOINT
    _mock_up_marker = object()
    _credentials = ('admin', 'admin')
    _base_headers = libcdmi.common.HEADER_CDMI_VERSION

    def setUp(self):
        self._cleanup = []
        fh, self._filename = tempfile.mkstemp(prefix='libcdmi-test-')
        os.close(fh)  # allow opening by the library

    def tearDown(self):
        os.unlink(self._filename)

        for method, args, kwargs in self._cleanup:
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

    def _make_headers(self, headers):
        final_headers = {}
        final_headers.update(self._base_headers)
        final_headers.update(headers)
        return final_headers

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

        self.assertEqual(200, response.status_code)
        self.assertEqual(response.headers['X-CDMI-Specification-Version'], '1.0.2')
        self.assertEqual(response.headers['Content-Type'], 'application/cdmi-container')

        result_data = response.json()
        self.assertEqual('application/cdmi-container', result_data['objectType'])
        self.assertEqual('testcontainer', result_data['objectName'])
