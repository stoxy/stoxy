
STOrage proXY (STOXY)
=====================

Stoxy is a web storage server talking `CDMI protocol`_. It's a continuation of a `CDMI-Proxy`_ project building
on top of a `Twisted`_, `OMS`_, ZCA and ZODB.

Stoxy supports CRUD operations for data objects and containers.

Source code
-----------
Source code is available at `https://github.com/stoxy <https://github.com/stoxy>`_.

License
-------
Stoxy is released under open-source Apache v2 license.

Quickstart
==========

Installation
------------

Stoxy comes with a buildout configuration file that defines all requires dependencies.

.. code-block:: sh

  $ git clone https://github.com/stoxy/stoxy.git
  $ cd stoxy
  $ python bootstrap.py
  $ ./bin/buildout -N
 
User accounts
-------------

Before starting we need at least an admin user account:

.. code-block:: sh

  $ bin/omspasswd -a john -g admins

You can change the password later on with the same `bin/omspasswd` utility, see
`bin/omspasswd --help` for additional info.

Starting up
-----------

Now you can start Stoxy daemon with:

.. code-block:: sh

  $ bin/stoxy
  
Connecting
----------

You can connect to the Stoxy via ssh:

.. code-block:: sh

  $ ssh john@localhost -p 6022

or REST:

.. code-block:: sh

  $ curl -u john:john localhost:8080/storage


Module documentation
====================

.. toctree::
   :maxdepth: 2
   
   gen/modules

.. _CDMI protocol: http://cdmi.sniacloud.com
.. _CDMI-Proxy: http://resources.venus-c.eu/cdmiproxy/docs/
.. _OMS: opennodecloud.com/docs/opennode.oms.core/
.. _Twisted: http://twistedmatrix.com


Credits
-------

Development of Stoxy is supported by `EGI <http://egi.eu>`_, `KTH PDC <http://www.pdc.kth.se>`_ and `OpenNode <http://opennodecloud.com>`_.
Contributors can be seen from the git log or `on Github <https://github.com/stoxy/stoxy/contributors>`_.

:ref:`search`
