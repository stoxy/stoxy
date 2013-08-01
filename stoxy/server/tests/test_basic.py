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


class TestBasic(unittest.TestCase):
    _endpoint = DEFAULT_ENDPOINT
    _mock_up_marker = object()

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

    @unittest.skipUnless(server_is_up(), 'Requires a running Stoxy server')
    def test_update(self):
        c = libcdmi.open(self._endpoint, credentials=('admin', 'admin'))

        def cleanup_container(c, name):
            try:
                c.delete(name)
            except Exception:
                pass

        self.addToCleanup(cleanup_container, c, '/testcontainer')
        container_create_1 = c.create_container('/testcontainer')
        container_create_2 = c.create_container('/testcontainer', metadata={'owner': 'nobody'})
        container_get = c.get('/testcontainer/', accept=libcdmi.common.CDMI_CONTAINER)
        self.assertEqual(dict, type(container_create_2))
        self.assertEqual(dict, type(container_create_1))
        self.assertEqual(dict, type(container_get))
        NotThere = '<NotThere>'
        for key, value in container_create_2.iteritems():
            self.assertEqual(value, container_get.get(key, NotThere),
                             'Expected: %s, but received: %s in %s' %
                             (value, container_get.get(key, NotThere), key))

    @unittest.skipUnless(server_is_up(), 'Requires a running Stoxy server')
    def test_create_new_and_get_container(self):
        c = libcdmi.open(self._endpoint, credentials=('admin', 'admin'))

        def cleanup_objects(c, name):
            try:
                c.delete(name)
            except Exception:
                pass

        self.addToCleanup(cleanup_objects, c, '/testcontainer')

        cleanup_objects(c, '/testcontainer')
        container_create = c.create_container('/testcontainer', metadata={'test': 'blah'})
        container_get = c.get('/testcontainer/', accept=libcdmi.common.CDMI_CONTAINER)
        self.assertEqual(dict, type(container_create))
        self.assertEqual(dict, type(container_get))
        NotThere = '<NotThere>'
        for key, value in container_create.iteritems():
            self.assertEqual(value, container_get.get(key, NotThere),
                             'Expected: %s, but received: %s in %s' %
                             (value, container_get.get(key, NotThere), key))
