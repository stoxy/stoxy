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

