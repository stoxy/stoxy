Authentication
--------------

Out of the box Stoxy comes with basic and digest REST authentication mechanisms. It is also possible to enable
Keystone token-based authentication. Only CMS (aka PKI tokens) are supported. For more information check OpenStack
`documentation <https://wiki.openstack.org/wiki/PKI>`_.

In order to access Stoxy using X.509/VOMS credentials, Keystone should have
`VOMS-support <https://github.com/IFCA/keystone-voms/>`_. Username will be taken from the provided 'username' field, groups - from
the provided roles in the token.


Keystone token setup
====================

Edit ``stoxy.conf`` and add the following sections:

.. code-block:: sh

   [auth]
   use_keystone = yes
   
   [keystone]
   # filename with a certificate of the keypair used for signing keystone CMS token
   signing_cert_file_name = /path/to/keystone/certs/signing_cert.pem
   
   # filename of a CA certificate for validation
   ca_file_name = /path/to/keystone/certs/cacert.pem
   
   # CLI command for running openssl. It has to be sufficienty new to support cms commands.
   # E.g. default version on OS X 10.8 is older, a newer can be installed via homebrew:
   # 'brew install openssl' and would be located at /usr/local/Cellar/openssl/1.0.1e/bin/openssl .
   openssl_cmd = /usr/local/Cellar/openssl/1.0.1e/bin/openssl

Example Keystone CAs could be taken from ``Keystone's repository <https://github.com/openstack/keystone/tree/master/examples/pki>`_.

Keystone usage example
======================

Once Keystone support is enabled, it's enough to set 'X-Auth-Token' header to a request with value equal to a CMS token.

.. code-block:: sh

   $ export t=`cat auth_token_scoped.pem`
   $ curl -H "X-Auth-Token:$t" \
     -H "Content-Type: application/cdmi-container" \
     -H "Accept: application/cdmi-container" \
     -H "X-CDMI-Specification-Version: 1.0.2" \
     -v -X PUT localhost:8080/storage/new-container   
   $ cat auth_token_scoped.pem 
   -----BEGIN CMS-----
   MIIHwQYJKoZIhvcNAQcCoIIHsjCCB64CAQExCTAHBgUrDgMCGjCCBc4GCSqGSIb3
   DQEHAaCCBb8EggW7eyJhY2Nlc3MiOiB7InNlcnZpY2VDYXRhbG9nIjogW3siZW5k
   cG9pbnRzIjogW3siYWRtaW5VUkwiOiAiaHR0cDovLzEyNy4wLjAuMTo4Nzc2L3Yx
   LzY0YjZmM2ZiY2M1MzQzNWU4YTYwZmNmODliYjY2MTdhIiwgInJlZ2lvbiI6ICJy
   ZWdpb25PbmUiLCAiaW50ZXJuYWxVUkwiOiAiaHR0cDovLzEyNy4wLjAuMTo4Nzc2
   L3YxLzY0YjZmM2ZiY2M1MzQzNWU4YTYwZmNmODliYjY2MTdhIiwgInB1YmxpY1VS
   TCI6ICJodHRwOi8vMTI3LjAuMC4xOjg3NzYvdjEvNjRiNmYzZmJjYzUzNDM1ZThh
   NjBmY2Y4OWJiNjYxN2EifV0sICJlbmRwb2ludHNfbGlua3MiOiBbXSwgInR5cGUi
   OiAidm9sdW1lIiwgIm5hbWUiOiAidm9sdW1lIn0sIHsiZW5kcG9pbnRzIjogW3si
   YWRtaW5VUkwiOiAiaHR0cDovLzEyNy4wLjAuMTo5MjkyL3YxIiwgInJlZ2lvbiI6
   ICJyZWdpb25PbmUiLCAiaW50ZXJuYWxVUkwiOiAiaHR0cDovLzEyNy4wLjAuMTo5
   MjkyL3YxIiwgInB1YmxpY1VSTCI6ICJodHRwOi8vMTI3LjAuMC4xOjkyOTIvdjEi
   fV0sICJlbmRwb2ludHNfbGlua3MiOiBbXSwgInR5cGUiOiAiaW1hZ2UiLCAibmFt
   ZSI6ICJnbGFuY2UifSwgeyJlbmRwb2ludHMiOiBbeyJhZG1pblVSTCI6ICJodHRw
   Oi8vMTI3LjAuMC4xOjg3NzQvdjEuMS82NGI2ZjNmYmNjNTM0MzVlOGE2MGZjZjg5
   YmI2NjE3YSIsICJyZWdpb24iOiAicmVnaW9uT25lIiwgImludGVybmFsVVJMIjog
   Imh0dHA6Ly8xMjcuMC4wLjE6ODc3NC92MS4xLzY0YjZmM2ZiY2M1MzQzNWU4YTYw
   ZmNmODliYjY2MTdhIiwgInB1YmxpY1VSTCI6ICJodHRwOi8vMTI3LjAuMC4xOjg3
   NzQvdjEuMS82NGI2ZjNmYmNjNTM0MzVlOGE2MGZjZjg5YmI2NjE3YSJ9XSwgImVu
   ZHBvaW50c19saW5rcyI6IFtdLCAidHlwZSI6ICJjb21wdXRlIiwgIm5hbWUiOiAi
   bm92YSJ9LCB7ImVuZHBvaW50cyI6IFt7ImFkbWluVVJMIjogImh0dHA6Ly8xMjcu
   MC4wLjE6MzUzNTcvdjIuMCIsICJyZWdpb24iOiAiUmVnaW9uT25lIiwgImludGVy
   bmFsVVJMIjogImh0dHA6Ly8xMjcuMC4wLjE6MzUzNTcvdjIuMCIsICJwdWJsaWNV
   UkwiOiAiaHR0cDovLzEyNy4wLjAuMTo1MDAwL3YyLjAifV0sICJlbmRwb2ludHNf
   bGlua3MiOiBbXSwgInR5cGUiOiAiaWRlbnRpdHkiLCAibmFtZSI6ICJrZXlzdG9u
   ZSJ9XSwidG9rZW4iOiB7ImV4cGlyZXMiOiAiMjAxMi0wNi0wMlQxNDo0NzozNFoi
   LCAiaWQiOiAicGxhY2Vob2xkZXIiLCAidGVuYW50IjogeyJlbmFibGVkIjogdHJ1
   ZSwgImRlc2NyaXB0aW9uIjogbnVsbCwgIm5hbWUiOiAidGVuYW50X25hbWUxIiwg
   ImlkIjogInRlbmFudF9pZDEifX0sICJ1c2VyIjogeyJ1c2VybmFtZSI6ICJ1c2Vy
   X25hbWUxIiwgInJvbGVzX2xpbmtzIjogWyJyb2xlMSIsInJvbGUyIl0sICJpZCI6
   ICJ1c2VyX2lkMSIsICJyb2xlcyI6IFt7Im5hbWUiOiAicm9sZTEifSwgeyJuYW1l
   IjogInJvbGUyIn1dLCAibmFtZSI6ICJ1c2VyX25hbWUxIn19fQ0KMYIByjCCAcYC
   AQEwgaQwgZ4xCjAIBgNVBAUTATUxCzAJBgNVBAYTAlVTMQswCQYDVQQIEwJDQTES
   MBAGA1UEBxMJU3Vubnl2YWxlMRIwEAYDVQQKEwlPcGVuU3RhY2sxETAPBgNVBAsT
   CEtleXN0b25lMSUwIwYJKoZIhvcNAQkBFhZrZXlzdG9uZUBvcGVuc3RhY2sub3Jn
   MRQwEgYDVQQDEwtTZWxmIFNpZ25lZAIBETAHBgUrDgMCGjANBgkqhkiG9w0BAQEF
   AASCAQCAtuVtqTU9h1uaRrYU1eusSnHwD6jizp/xltTrYTyFPfYjhJdglS+bjSeS
   Iau9pN3Tfug98ozUTJ5ByNepAQtxBxPz5bDXhBmAbU6ywaolqRAG+b/s2ShNGQ2a
   tn80NeZmDNbtoqdHVAkD3EZXjsEKr2w+3JTTF2indzczyGe5EeSfNUaT+ZhNEmPR
   Urob62t8atW+zehCSurpaa8pC5m1NcbK8Uu6Y+qO2m08KU9w5kmbOQtWAGCmtpIx
   F2yM1AbSgd90yzen7dv5mNkgZyzQ6SYgRUvkKOKnCyBb97EZK3ZR4qUxQzRYM++8
   g8HdaIfoYVPoPHqODet8Xmhw/Wtp
   -----END CMS-----
   
   