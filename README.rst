wrench: a CLI tool for Passbolt
===============================

Installation
------------

Before installing wrench, make sure your system has the following software installed:

- `Python <https://www.python.org/downloads/>`_ (version >= 3.5)
- `pipx <https://github.com/pipxproject/pipx>`_
- `GnuPG <https://gnupg.org/>`_ (version >= 2.1)

If you already have pipx installed, you can skip the next section and jump
straight to `Installing wrench`_.

Installing pipx
~~~~~~~~~~~~~~~

Open a terminal and run the following commands::

  python3 -m pip install --user pipx
  python3 -m pipx ensurepath

Try running ``pipx --version`` to make sure it's installed correctly.

.. note::

   If you previously installed wrench using pipsi, uninstall it first by running ``pipsi uninstall wrench``.

Installing wrench
~~~~~~~~~~~~~~~~~

You can now install wrench by running the following command::

  pipx install passbolt-wrench

If you want to have passwords copied automatically to the clipboard, install ``pyperclip``::

  pipx inject passbolt-wrench pyperclip

Then go to your Passbolt instance, export your private key and run ``wrench
import-key /path/to/your/key.asc`` (you'll be prompted to enter some
configuration values the first time you run wrench).

Usage
-----

Search for a resource::

  $ wrench search cisco
  name        : Cisco router
  id          : 5943ba07-2880-4814-a5da-1dd3c0a87a74
  uri         : https://10.0.2.70
  username    : cisco
  secret      : 1234
  description : Please keep this password secret

Add a resource::

  $ wrench add
  Name: Bank account
  URI: http://example.com
  Description: My private bank account
  Username: john.doe
  Secret:

  Entry 'Bank account' successfully saved.

  If you would like to share it, enter e-mail addresses below, separated by commas. Auto completion through Tab key is supported.
  Recipients:

Dump all resources::

  $ wrench dump > dump.json


To see the list of all wrench commands, run `wrench` without any argument.

Common issues
-------------

**I'm getting a GPGAuthStage1Exception**

First, take a deep breath, don't panic. Once you've stopped shaking, make sure
the GnuPG version you're running is at least 2.1 (you can find out by running
``gpg --version``). If that's not the case, install a newer version.

If it still doesn't work, try to run the following::

  GPG_TTY=$(tty) wrench

If it works, you can make this persistent by adding the following to your
.bashrc/.zshrc/.whateverrc file (located in your home directory)::

  export GPG_TTY=$(tty)

Contributing
------------

To work on wrench locally it is advised that you create a virtual environment.
There are several ways to do it
(`virtualenvwrapper <https://pypi.python.org/pypi/virtualenvwrapper>`_,
`direnv <https://github.com/direnv/direnv>`_, plain virtual env, etc), but here's
one (this will create a `venv` directory in your current directory, make sure
you don't accidentally commit it)::

  python3 -m venv venv
  . venv/bin/activate

Then use the following command to symlink wrench in your virtualenv. That way
when you run ``wrench`` you'll be running the code from your working copy::

  ./setup.py develop

To run the tests, use the following command::

  ./setup.py test
