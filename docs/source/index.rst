
STOrage proXY (STOXY)
=====================

Stoxy is a web storage server exposing a common interface (`CDMI protocol`_) for accessing multiple data source backends.
It's a continuation of a `CDMI-Proxy`_ project building on top of a `Twisted`_, `OMS`_, ZCA and ZODB.

Stoxy supports read-write operations for data objects (aka files) and containers (aka folders) and integrates with
the following backend systems:

Support for additional backend systems is on-going, for tutorial for adding new backends, see below.

Source code
-----------
Source code is available at `https://github.com/stoxy/stoxy <https://github.com/stoxy/stoxy>`_.

License
-------
Stoxy is released under open-source Apache v2 license.

Documentation
-------------

.. toctree::
   :maxdepth: 2

   intro
   usage
   swift
   upgrade
   cli_usage
   security
   deployments
   backend_tutorial

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
