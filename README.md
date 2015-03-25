# eos-db
Database and API server for Cloudhands-EOS system.

# Quickstart for Ubuntu 14.04


 ```$ apt-get install python3.4-dev postgresql libpq-dev libffi-dev```

 ```# A hack to bootstrap the venv properly```

 ```$ pyvenv-3.4 --without-pip ~/eoscloud-venv```

 ```$ wget -q -O- https://bootstrap.pypa.io/get-pip.py | ~/eoscloud-venv/bin/python```


 ```$ sudo -Hi -u postgres createuser -w $USERNAME -DRS```

 ```$ sudo -Hi -u postgres createdb -w eos_db -E UTF8 -O $USER```

 ```$ ~/eoscloud-venv/bin/python setup.py develop```

 ```$ ~/eoscloud-venv/bin/python bin/eos-init```

 ```$ ~/eoscloud-venv/bin/python bin/eos-admin help```

Use this tool to configure your users and servers, before starting the DB:

 ```$ ~/eoscloud-venv/bin/pserve development.ini```

# Notes

This assumes you want to develop the system.  For production, follow a
similar path but do it in a dedicated account and use '... setup.py install'.

The server module requires a Python 2.7 environment, as the *Paste* module has not been ported to Python 3, and we need it for HTTP header handling.
