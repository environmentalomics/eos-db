"""This is an example settings file. If no settings file is found a connection
as the current user will be attempted without a password to the eos_db database.
If the username is empty the host and password will be ignored but the specified
database will be used."""

class DBDetails():
    database = 'eoscloud'
    username = 'databasedude'
    #These are ignored if username is blank
    password = 'god'
    host     = 'localhost'
