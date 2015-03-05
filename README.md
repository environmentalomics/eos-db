# eos-db
Database and API server for Cloudhands-EOS system.

# Quickstart for Ubuntu 14.04


 $ apt-get install python3.4-dev postgresql

 # A hack to bootstrap the venv properly
 $ pyvenv-3.4 --without-pip ~/eoscloud-venv
 $ wget -q -O- https://bootstrap.pypa.io/get-pip.py | ~/eoscloud-venv/bin/python

 $ sudo -Hi -u postgres createuser -w $USERNAME -DRS
 $ sudo -Hi -u postgres createdb -w eoscloud -E UTF8 -O $USER

 $ ~/eoscloud-venv/bin/python setup.py develop

 $ ~/eoscloud-venv/bin/pserve test.ini

At this point I get an error about the lack of the SQLAlchemy module.
So, need to work out how to configure the database.
Does it still need a hard-coded password?  If so, we can fix that!!


# Notes

This assumes you want to test/develop the system.  For production, follow a
similar path but do it in a dedicated account and use '... setup.py install'.

You should use the same venv for eos-agents and eos-portal, so if you already
have the venv skip straigh to the setup.py bit.
