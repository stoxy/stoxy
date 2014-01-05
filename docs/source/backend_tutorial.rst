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
Stoxy imposes a logical structure on the data, a kind of a virtual file path.


Implementation of the backend operations
----------------------------------------

An example implementation of the simple file backend follows. Will walk through the non-trivial aspects below.::

    class FileStore(Adapter):
        implements(IDataStore)
        context(IDataObject)
        name('file')

        def save(self, datastream, encoding):
            protocol, host, path = parse_uri(self.context.value)
            assert protocol == 'file', protocol
            assert not host, host
            b = 6 * 1024
            log.debug('Writing file: "%s"' % path)
            with open(path, 'wb') as f:
                d = datastream.read(b)
                if encoding == 'base64':
                    d = base64.b64decode(d)
                f.write(d)
                while len(d) == b and not datastream.closed:
                    d = datastream.read(b)
                    f.write(d)

        def load(self):
            protocol, host, path = parse_uri(self.context.value)
            assert protocol == 'file', protocol
            assert not host, host
            return open(path, 'rb')

        def delete(self):
            protocol, host, path = parse_uri(self.context.value)
            assert protocol == 'file', protocol
            assert not host, host
            log.debug('Unlinking "%s"' % path)
            os.unlink(path)


