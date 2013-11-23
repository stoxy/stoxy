cdmiclient usage
================

`cdmiclient` is a command-line tool to manipulate STOXY CDMI objects, like creating containers and objects,
uploading object data from files, updating data, downloading and deleting objects.


.. code-block:: sh

    usage: cdmiclient.py [-h] [-f FILENAME] [-m MIMETYPE] [-u AUTH]
                         [-o {json,yaml,raw}]

                         {create_container,create_object,delete,head,get,update_container,update_object}
                         url

    positional arguments:
      {create_container,create_object,delete,head,get,update_container,update_object}
                            Action to perform on the URL
      url                   URL of the object to apply action to

    optional arguments:
      -h, --help            show this help message and exit
      -f FILENAME, --filename FILENAME
                            Input file path (required, when calling create* and
                            update*)
      -m MIMETYPE, --mimetype MIMETYPE
                            Input file MIME-type
      -u AUTH, --auth AUTH  Authentication credentials (user:password)
      -o {json,yaml,raw}, --output {json,yaml,raw}
                            Pretty-print in a format specified (YAML, JSON or raw
                            dict)

NOTE: `--filename` option is required for `create_object` action.
