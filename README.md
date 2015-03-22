# eos-db
Database and API server for Cloudhands-EOS system.

# Quickstart for Ubuntu 14.04


 $ apt-get install postgresql libpq-dev

 $ virtualenv ~/eoscloud/py2venv
 $ wget -q -O- https://bootstrap.pypa.io/get-pip.py | ~/eoscloud-venv/py2venv/bin/python

 $ sudo -Hi -u postgres createuser -w $USERNAME -DRS
 $ sudo -Hi -u postgres createdb -w eoscloud -E UTF8 -O $USER

 $ ~/eoscloud-venv/bin/python setup.py develop

 $ ~/eoscloud-venv/bin/pserve development.ini
 
# Notes

This assumes you want to develop the system.  For production, follow a
similar path but do it in a dedicated account and use '... setup.py install'.

The server module requires a Python 2.7 environment, as the *Paste* module has not been ported to Python 3, and we need it for HTTP header handling.
