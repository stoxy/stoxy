import logging
import requests

from mock import MagicMock

import config

try:
    import libcdmi
except ImportError:
    print ('You need to enable libcdmi-python in development mode (see docs)')
    libcdmi = MagicMock()


log = logging.getLogger(__name__)
_server_is_up = False


def server_is_up():
    try:
        response = requests.get(config.DEFAULT_ENDPOINT, auth=config.CREDENTIALS)
    except requests.ConnectionError:
        _server_is_up = False
        log.debug('Server is down: connection error!')
    else:
        if response.status_code >= 400:
            _server_is_up = False
            log.debug('Server returned status code %s' % response.status_code)
            print ('Server returned status code %s' % response.status_code)
        elif type(libcdmi) is MagicMock:
            _server_is_up = False
            log.debug('libcdmi-python is unavailable -- server is "down"')
        else:
            _server_is_up = True
            log.debug('Server is up!')
    return _server_is_up


NotThere = '<NotThere>'
