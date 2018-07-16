Changelog
=========

dev
---

**Improvements**

- Split terms in ``search`` command and match them separately
- Add groups support when sharing a resource
- Allow setting default recipients in the configuration file
- Add support for tags

0.1.0 (2018-03-29)
------------------

**Improvements**

- Add ``add`` command to add new resources
- Add ``--version`` flag
- Add Debian packaging scripts
- Make resource search case insensitive
- Recommend the usage of pipsi to install wrench

**Bugfixes**

- Accept HTTPS URL in configuration wizard (`PR #7 <https://github.com/liip/wrench/pull/7>`_)
- Make sure configuration directory exists before creating config file

**Dependencies**

- Use requests-gpgauthlib>0.1.0 (`PR #6 <https://github.com/liip/wrench/pull/6>`_)


0.0.1 (2018-02-28)
------------------

Initial release.
