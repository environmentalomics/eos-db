# eos-db
Database and API server for Cloudhands-EOS system.

# Quickstart for Ubuntu 14.04


 ```$ apt-get install python-dev python-virtualenv postgresql libpq-dev```

 ```$ virtualenv ~/eoscloud-py2-venv```

 ```$ sudo -Hi -u postgres createuser -w $USERNAME -DRS```
 ```$ sudo -Hi -u postgres createdb -w eos_db -E UTF8 -O $USER```

 ```$ ~/eoscloud-py2-venv/bin/python setup.py develop```

 ```$ ~/eoscloud-py2-venv/bin/python bin/eos-init```
 ```$ ~/eoscloud-py2-venv/bin/python bin/eos-admin help```
Use this tool to configure your users and servers, before starting the DB:

 ```$ ~/eoscloud-py2-venv/bin/pserve development.ini```
 
# Notes

This assumes you want to develop the system.  For production, follow a
similar path but do it in a dedicated account and use '... setup.py install'.

The server module requires a Python 2.7 environment, as the *Paste* module has not been ported to Python 3, and we need it for HTTP header handling.
