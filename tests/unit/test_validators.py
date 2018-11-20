import pytest
import wrench.validators
from wrench.exceptions import ValidationError


def test_validate_non_empty_raises_error_for_empty_value():
    with pytest.raises(ValidationError):
        wrench.validators.validate_non_empty('')


def test_validate_non_empty_does_not_raise_error_for_non_empty_value():
    wrench.validators.validate_non_empty('value')


def test_validate_http_url_raises_error_for_non_http_url():
    with pytest.raises(ValidationError):
        wrench.validators.validate_http_url('ftp://localhost')


def test_validate_http_url_raises_error_for_non_url():
    with pytest.raises(ValidationError):
        wrench.validators.validate_http_url('localhost')


def test_validate_http_url_does_not_raise_error_for_http_url():
    wrench.validators.validate_http_url('http://localhost')


def test_validate_http_url_does_not_raise_error_for_https_url():
    wrench.validators.validate_http_url('https://localhost')


def test_validate_recipients_raises_error_for_invalid_choices():
    with pytest.raises(ValidationError):
        wrench.validators.validate_recipients('jane.doe@example.com', {'john.doe@example.com': 'John'})


def test_validate_recipients_raises_error_if_one_invalid_choice():
    with pytest.raises(ValidationError):
        wrench.validators.validate_recipients(
            'jane.doe@example.com, john.doe@example.com', {'john.doe@example.com': 'John'}
        )


def test_validate_recipients():
    wrench.validators.validate_recipients(
        'jane.doe@example.com, john.doe@example.com', {'john.doe@example.com': 'John', 'jane.doe@example.com': 'Jane'}
    )


def test_validate_recipients_with_empty_value_returns_empty_list():
    assert wrench.validators.validate_recipients(
        '   ', {'john.doe@example.com': 'John', 'jane.doe@example.com': 'Jane'}
    ) == []


def test_validate_recipients_returns_selected_recipients():
    assert wrench.validators.validate_recipients(
        'jane.doe@example.com', {'john.doe@example.com': 'John', 'jane.doe@example.com': 'Jane'}
    ) == ['Jane']
