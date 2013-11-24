Using Stoxy
===========

libcdmi-python
--------------

A python library (`libcdmi-python`_) was written to simplify interactions with
Stoxy. Examples of usage can be directly taken from `unit tests`_.

.. code-block: py
   #!/usr/bin/env python
   import sys
   import json
      
   import libcdmi
   
   server = 'http://localhost:8080'
   
   c = libcdmi.open(server, credentials=('john', 'john'))
   
   response = c.create_object('/storage/path/on/storage', 'local-file-for-upload',
                               metadata={'event name': 'SNIA SDC 2013',
                                         'event location': 'Santa Clara, CA'})
   
   print json.dumps(response, sort_keys=True,
                   indent=4, separators=(',', ': '))


cURL
----

You can use `curl <http://curl.haxx.se/>`_ for constructing a valid CDMI request.
For example, to create a new container, run the following command (replace port
8080 for the one where your Stoxy instance is listening):


Creating/updating a container with CDMI content-type
----------------------------------------------------

.. code-block:: sh

   $ curl -v -u username:pass \
        -H 'x-cdmi-specification-version: 1.0.2' \
        -H 'content-type: application/cdmi-container' \
        -H 'accept:application/cdmi-container' \
        -X PUT http://cdmiserver:8080/newcontainer

Refer to `CDMI reference <http://cdmi.sniacloud.com/>`_ for more precise header/body specification.


Creating/updating an object with CDMI content-type
--------------------------------------------------

.. code-block:: sh

  $ curl -v -u username:pass \
        -H 'x-cdmi-specification-version: 1.0.2' \
        -H 'content-type: application/cdmi-object' \
        -H 'accept: application/cdmi-object' \
        -X PUT http://cdmiserver:8080/containername/objectname

Request body is expected to be a JSON-encoded data structure, with ''value'' attribute set to the object
(file) contents, encoded as either a UTF-8 string with Unicode escape sequences or base64.
''valuetransferencoding'' field must then describe the encoding as either 'utf-8' or 'base64' respectively.

Note, that creating and updating objects is performed using virtually the same request structure. If the
object being sent with the request already exists, it will be updated by Stoxy.


Creating/updating an object with non-CDMI content-type
------------------------------------------------------

.. code-block:: sh

  $ curl -v -u username:pass \
        -H 'x-cdmi-specification-version: 1.0.2' \
        -H 'content-type: application/octet-stream' \
        -X PUT http://cdmiserver:8080/containername/objectname

Request body is expected to be the object (file) contents.

Deleting an object
------------------

.. code-block:: sh

  $ curl -v -u username:pass \
        -H 'x-cdmi-specification-version: 1.0.2' \
        -X DELETE http://cdmiserver:8080/containername/objectname


.. _libcdmi-python: https://github.com/stoxy/libcdmi-python
.. _unit tests: https://github.com/stoxy/libcdmi-python/blob/master/test/test_basic.py
