from wrench.resources import resource_matches

from ..factories import ResourceFactory


def test_search_ignores_case():
    assert resource_matches(ResourceFactory(name='LIIP'), 'liip')


def test_resource_without_all_words_does_not_match():
    assert not resource_matches(ResourceFactory(name='liip web dev'), 'liip mobile dev')


def test_resource_with_all_words_unordered_matches():
    assert resource_matches(ResourceFactory(name='liip web dev'), 'web dev')


def test_resource_with_words_in_different_fields_matches():
    assert resource_matches(ResourceFactory(name='liip web', username='admin'), 'admin liip')
