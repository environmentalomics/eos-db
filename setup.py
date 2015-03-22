if __name__ == "__main__":

    import os

    from setuptools import setup, find_packages

    here = os.path.abspath(os.path.dirname(__file__))

    with open(os.path.join(here, 'README.md')) as f:
        README = f.read()
    with open(os.path.join(here, 'CHANGES.md')) as f:
        CHANGES = f.read()
    # Could also read version from CHANGES in the Deb style?
    with open(os.path.join(here, 'VERSION')) as f:
        VERSION = f.read().split()[0]

    requires = [
        'pyramid',              # Framework
        'pyramid_debugtoolbar', # Framework debugger
        'pyramid_chameleon',    # Templating framework
        'waitress',             # Server
        'sqlalchemy',           # ORM
        'psycopg2',             # Postgres database interface
        'paste',                # HTTP header handling for security
        'requests',             # Required for tests
        'webtest'               # Required for tests
        ]

    setup(name='eos_db',
          version=VERSION,
          description='eos_db',
          long_description=README + '\n\n' + CHANGES,
          classifiers=[
            "Programming Language :: Python",
            "Framework :: Pyramid",
            "Topic :: Internet :: WWW/HTTP",
            "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
            ],
          author='',
          author_email='',
          url='',
          keywords='web pyramid pylons',
          packages=find_packages(),
          include_package_data=True,
          zip_safe=False,
          install_requires=requires,
          tests_require=requires,
          test_suite="eos_db.test",
          entry_points="""\
          [paste.app_factory]
          main = eos_db:main
          """,
          )
