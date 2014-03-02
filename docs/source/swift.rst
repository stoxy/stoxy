OpenStack Swift backend
=======================

Introduction
------------

Stoxy can serve as a CDMI interface to a remote OpenStack Swift service. The top level flow is as follows:

#. A new container is created.
#. Container's metadata field is set with the ``swift`` backend and the base url values:

   - stoxy_backend: **swift**
   - stoxy_backend_base_protocol: **https://swift.example.org:port/v1/AUTH_df37f5b1ebc94604964c2854b9c0551f**

#. For the data objects value modifications operations inside the container, the commands will be
   propagated to the OpenStack Swift storage (saving, loading, deleting).
  
**NB!** Usage of the ``swift`` backend assumes that OpenStack authentication token is passed in the
*X-Auth-Token* header of the request.
