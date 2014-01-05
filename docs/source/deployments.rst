List of known Stoxy deployments
===============================


* https://demo.stoxy.net - demo instance, reset and upgraded every day. Demo user: **stoxy:stoxy**
* https://egi-cloud43.zam.kfa-juelich.de/stoxy - Forschungszentrum Jülich testbed
* https://stoxy.pdc.kth.se - KTH PDC testbed


Limiting listening ports to localhost
=====================================

Add to stoxy.conf::

    [rest]
    port = 8080
    interface=127.0.0.1

    [ssh]
    interface=127.0.0.1


Disabling PAM backend
=====================

Add to stoxy.conf::

    [auth]
    use_pam = no

If PAM is not used for authentication, this will greatly improve the performance of operations.