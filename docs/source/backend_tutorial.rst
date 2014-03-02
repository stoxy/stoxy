Adding a new backend support
============================

Preliminary knowledge
---------------------

The reader should have a preliminary knoweldge of the following concepts:

- `Twisted`_ - an event-based networking framework
- `ZCA`_ - Zope Component Architecture, a python library for creating decoupled applications

.. _Twisted: http://twistedmatrix.com
.. _ZCA: http://docs.zope.org/zope.component/

The rest of the concepts are introduced as part of the tutorial.

Where data is stored
--------------------
Stoxy imposes a logical structure on the data, a kind of a virtual file path. The 'folders' of this filesystems, aka
containers, are stored in Stoxy database (ZODB). Actual object content is stored in the configured backend.


Implementation of the backend operations
----------------------------------------

An example implementation of the simple file backend follows. The self.context variable represents a
a data object stored inside Stoxy DB.::

   class FileStore(Adapter):
       implements(IDataStore)
       context(IDataObject)
       name('file')
   
       def save(self, datastream, encoding, credentials=None):
           protocol, schema, host, path = parse_uri(self.context.value)
           b = 6 * 1024
           with open(path, 'wb') as f:
               d = datastream.read(b)
               if encoding == 'base64':
                   d = base64.b64decode(d)
               f.write(d)
               while len(d) == b and not datastream.closed:
                   d = datastream.read(b)
                   f.write(d)
   
       def load(self, credentials=None):
           protocol, schema, host, path = parse_uri(self.context.value)
           return open(path, 'rb')
   
       def delete(self, credentials=None):
           protocol, schema, host, path = parse_uri(self.context.value)
           os.unlink(path)


