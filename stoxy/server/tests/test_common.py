import re
import struct
import unittest

from stoxy.server.common import generate_guid
from stoxy.server.common import generate_guid_b64


class GuidGenTestCase(unittest.TestCase):
    def testGuidIsTimeDependent(self):
        guid1 = generate_guid()
        guid2 = generate_guid()
        self.assertNotEqual(guid1, guid2)

    def testBasic64Conversion(self):
        guid = generate_guid_b64()
        self.assertTrue(re.match('[0-9A-Za-z=\\/\\w]+', guid))

    def testMustBeVendorDependent(self):
        guid1 = generate_guid(entnumber=32012)
        guid2 = generate_guid(entnumber=15232)
        self.assertNotEqual(guid1[0:4], guid2[0:4])

    def testSizeMustReflectTheGuidSize(self):
        guid = generate_guid()
        guiddata = struct.unpack('!LBBH' + 'p' * (len(guid) - 8), guid)
        self.assertEqual(len(guid), guiddata[2])
