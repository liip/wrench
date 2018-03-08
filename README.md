wrench: a CLI tool for Passbolt
===============================

Installation
------------

wrench only works with Python 3, so if your system only has Python 2 you should
first install Python3. You can then use pip to install wrench:

```
pip install passbolt-wrench
```

Then go to your Passbolt instance, export your private key and run `wrench
import_key /path/to/your/key.asc` (you'll be prompted to enter some
configuration values the first time you run wrench).

Usage
-----

Search for a resource:

```
$ wrench search cisco
name        : Cisco router
id          : 5943ba07-2880-4814-a5da-1dd3c0a87a74
uri         : https://10.0.2.70
username    : cisco
secret      : 1234
description : Please keep this password secret
```

Add a resource:

```
$ wrench add
Name: Bank account
URI: http://example.com
Description: My private bank account
Username: john.doe
Secret: 

Entry 'Bank account' successfully saved.

If you would like to share it, enter e-mail addresses below, separated by commas. Auto completion through Tab key is supported.
Recipients: 
```

To see the list of all wrench commands, run `wrench` without any argument.

Contributing
------------

To work on wrench locally it is advised that you create a virtual environment.
There are several ways to do it
([virtualenvwrapper](https://pypi.python.org/pypi/virtualenvwrapper),
[direnv](https://github.com/direnv/direnv), plain virtual env, etc), but here's
one (this will create a `venv` directory in your current directory, make sure
you don't accidentally commit it):

```
python3 -m venv venv
. venv/bin/activate
```

Then use the following command to symlink wrench in your virtualenv. That way when you run `wrench` you'll be running the code from your working copy:

```
./setup.py develop
```

To run the tests, use the following command:

```
./setup.py test
```
