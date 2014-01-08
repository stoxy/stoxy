Deployment
==========

List of known Stoxy deployments
-------------------------------

* http://demo.stoxy.net:8080/storage - demo instance, reset and upgraded every day. Demo user: **stoxy:stoxy**
* https://egi-cloud43.zam.kfa-juelich.de/stoxy/storage - Forschungszentrum Jülich testbed
* https://stoxy.pdc.kth.se - KTH PDC testbed (down till mid January)


Limiting listening ports to localhost
-------------------------------------

Add to stoxy.conf::

    [rest]
    port = 8080
    interface=127.0.0.1

    [ssh]
    interface=127.0.0.1


Disabling PAM backend
---------------------

Add to stoxy.conf::

    [auth]
    use_pam = no

If PAM is not used for authentication, this will greatly improve the performance of operations.

Resolving setuptools/distribute conflict
----------------------------------------

In some cases system packages are conflicting with buildout's requested version
of setuptools. An easy fix is to use virtualenv::

    $ virtualenv -p /usr/bin/python27 stoxyenv
    $ . ./stoxyenv/bin/activate
    $ #proceed with initial deployments instructions

Deploying on a clean Ubuntu 13.10
---------------------------------

Verified on an AWS instance of Ubuntu 13.10::

    $ sudo apt-get install git gcc python-dev libssl-dev python-virtualenv
    $ git clone https://github.com/stoxy/stoxy.git
    $ . stoxyenv/bin/activate
    $ cd stoxy && python bootstrap.py && ./bin/buildout -N
    $ ./bin/omspasswd -a stoxy  # to add a user
    $ ./bin/omspasswd -g cdmiusers -a stoxy  # to add a user with cdmiusers group
    $ ./bin/stoxy  # start a process
