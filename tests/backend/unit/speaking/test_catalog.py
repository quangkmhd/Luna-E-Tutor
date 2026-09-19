from luna_tutor.speaking.catalog import load_topics


def test_catalog_has_six_open_scenarios_with_at_most_eight_words():
    topics = load_topics()
    assert {item.id for item in topics} == {
        'animals', 'food', 'school', 'hobbies', 'family-friends', 'places-travel'
    }
    assert all(item.scenario and 1 <= len(item.words) <= 8 for item in topics)
