# Contributing to Member Audit

Member Audit welcomes every contribution to Member Audit!
If you are unsure whether your idea is a good fit, please do not hesitate to open an issue or ask one of the maintainers on Discord.

To make sure your merge request can pass our CI and gets accepted we kindly ask you to follow the instructions below:

## Code Formatting

This project uses [pre-commit](https://github.com/pre-commit/pre-commit) to
verify compliance with formatting rules. To use:

1. Pip install `pre-commit`
2. From inside the memberaudit root directory, run `pre-commit install`.
3. You're all done! Code will be checked automatically using git hooks.

## Tests

Please include proper unit tests for all new functionality.

We are using [Python unittest](https://docs.python.org/3/library/unittest.html) with the Django `TestCase` classes for all tests. In addition we are using following 3rd party test tools:

- django-webtest / [WebTest](https://docs.pylonsproject.org/projects/webtest/en/latest/) - testing the web UI
- [request-mock](https://requests-mock.readthedocs.io/en/latest/) - testing requests with the requests library
- [tox](https://tox.wiki/en/latest/) - Running the test suite
- [coverage](https://coverage.readthedocs.io/en/6.4.1/) - Measuring the test coverage

## Running tox tests locally

Our test suite is run through tox, which is automatically executed on GitLab. To run the test suite locally you provide access to a running MySQL (or MariaDB) instance:

- MySQL user that can create the test database: `test_tox_allianceauth` (this will only be created temporarily while the test is running)
- Username and password of that MySQL user must be set as environment variables: `MYSQL_USER`, `MYSQL_PASSWORD`.
- Optionally you can also set `MYSQL_HOST` and `MYSQL_PORT`

Example:

```bash
export MYSQL_USER="runner"
```
