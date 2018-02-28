from wrench.resources import resource_matches

from ..factories import ResourceFactory


def test_search_ignores_case():
    assert resource_matches(ResourceFactory(name='LIIP'), 'liip')
