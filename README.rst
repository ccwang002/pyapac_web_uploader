********************************
PyCon APAC 2015 Web Content Tool
********************************

Command-line tool for managing web content of PyCon APAC 2015.

Installation
============
You may want to install it in a virtual environment.

Clone this repo and run::

    python setup.py install

It requires Python 2.7 or 3.3+ and the following packages:

- six
- requests
- BeautifulSoup4
- click

On Python 2.7 and 3.3 requires pathlib.

pandas and lxml are required to get proposal statistics.


Usage
=====
Command ``pyapac-web`` will be available after install.
Detail help can be found by::

    pyapac-web -h


To automatically log in PyCon APAC 2015 admin, put account info
under ``.web_keychain`` with format::

    Account: 'your account'
    Password: 'your password'

Your account must have the previlege to edit web pages.
Normal speaker account will not work.

Upload web pages
----------------
To update web page at ``tw.pycon.org/2015apac/<lang>/<page>``::

    pyapac-web upload /path/to/<lang>/<page>.html \
        --keychain=../.web_keychain
    pyapac-web upload src.html --target <lang>/<page>

**Commmit the html to** |content-repo|_ **before upload!**

.. |content-repo| replace:: **this repo**
.. _content-repo: https://github.com/pycontw/APAC2015WebContent

Download from site
------------------
Sometimes people change directly on site,
you may want to update that change into repo.
This can be done by::

    pyapac-web download https://.../2015apac/en/venue
    pyapac-web download en/venue
    pyapac-web download en/venue /path/to/out.html

By default, you could get a prettified HTML at ``./<lang>_<page>.html``.
Note that uploaded HTML don't remember original indent space,
you have to re-organize it yourself.

Find more usage through its help page.

Proposal statistics
-------------------
Require pandas and lxml.
Proposals grouped by talk type and language can be shown by::

    pyapac-web stat


Develop
=======
File a pull request or issue.

You could install the package by::

    pip install -r requirements_dev.txt
    python setup.py develop

for development (to reflect change without re-install).

We follow PEP8 coding style, use flake8 at repo root to check::

    flake8

and fix any shown warnings and errors.

Find some experiment codes under ``ipy_playground/``.
