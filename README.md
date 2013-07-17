Storage Proxy
=============

CDMI-compliant storage proxy.

Buildout deployment
===================
    python bootstrap.py -v 1.7.1
    ./bin/buildout -N
    # run tests
    bin/coverage run --source=stoxy bin/test --with-xunit


Building documentation
======================
    export PYTHONPATH=$PYTHONPATH:$PWD
    bin/buildout -N install docs
    bin/docs

Development setup
=================
To install it:

    python setup.py develop


To uninstall it:

    pip uninstall stoxy
