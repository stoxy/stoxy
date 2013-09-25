Using Stoxy
===========

libcdmi-python
--------------

A python library (`libcdmi-python`_) was written to simplify interactions with Stoxy. Examples of usage can be directly taken
from `unit tests`_.

cURL
----

You can use `curl <http://curl.haxx.se/>`_ for constructing a valid CDMI request.
For example, to create a new container, run the following command (replace port 8080 for the one where your Stoxy instance
is listening):

.. code-block:: sh

   $ curl -v -u username:pass \
        -H 'x-cdmi-specification-version: 1.0.2' \
        -H 'content-type: application/cdmi-container' \
        -H 'accept:application/cdmi-container' \
        -X PUT http://cdmiserver:8080/storage/newcontainer

Create an object with non-CDMI data object (more efficient):

.. code-block:: sh

   $ curl -u username:pass \
          --data-binary @/path/to/big/big/file.iso \
          -v -X PUT localhost:8080/storage/larger-file

Refer to `CDMI reference <http://cdmi.sniacloud.com/>`_ for more precise header/body specification. 


.. _libcdmi-python: https://github.com/stoxy/libcdmi-python
.. _unit tests: https://github.com/stoxy/libcdmi-python/blob/master/test/test_basic.py