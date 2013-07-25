import logging
import unittest
import os
import requests
import tempfile

from mock import MagicMock

import libcdmi


log = logging.getLogger(__name__)
_server_is_up = False


def server_is_up():
    global _server_is_up
    return _server_is_up


def setUpModule():
    global _server_is_up
    response = requests.get(TestBasic._endpoint)
    if response.status_code >= 400:
        _server_is_up = False
        log.debug('Server is down!')
    else:
        _server_is_up = True
        log.debug('Server is up!')


def tearDownModule():
    pass


class TestBasic(unittest.TestCase):
    _endpoint = 'http://localhost:8080/storage'
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
    def test_create_and_get_container(self):
        c = libcdmi.open(self._endpoint)
        container_create = c.create_container('/testcontainer')
        container_get = c.get('/testcontainer/', accept=libcdmi.common.CDMI_CONTAINER)
        self.assertEqual(container_create, container_get)
