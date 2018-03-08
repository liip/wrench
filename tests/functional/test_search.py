from unittest.mock import patch


@patch('wrench.services.passbolt_api.get_resources')
@patch('wrench.commands.GPGAuthSession')
def test_search_doesnt_include_non_matching_resources(GPGAuthSession, get_resources, cli, gpg):
    get_resources.return_value = [
        {
            'id': '43',
            'name': 'other account',
            'username': 'jane.doe',
            'uri': 'example.com',
            'description': 'my bank account',
            'secrets': [{'data': gpg.encrypt('secret', 'john.doe')}]
        },
    ]

    result = cli('search', ['production'])

    assert 'other account' not in result.output


@patch('wrench.services.passbolt_api.get_resources')
@patch('wrench.commands.GPGAuthSession')
def test_search_includes_matching_resources(GPGAuthSession, get_resources, cli, gpg):
    get_resources.return_value = [
        {
            'id': '42',
            'name': 'bank account',
            'username': 'jane.doe',
            'uri': 'example.com',
            'description': 'my bank account',
            'secrets': [{'data': gpg.encrypt('secret', 'john.doe')}]
        },
    ]

    result = cli('search', ['bank'])

    assert 'bank account' in result.output
