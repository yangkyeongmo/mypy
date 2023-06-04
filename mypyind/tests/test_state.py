from mypyind.src.state import MypyindState


def test_initialize_with_seed():
    state = MypyindState('seed')
    assert state.is_in_found('seed')


def test_increase_level():
    state = MypyindState('seed')
    prev_level = state.level
    state.increase_level()
    assert state.level == prev_level + 1


def test_add_found():
    state = MypyindState('seed')
    state.add_found('foo', 'bar')
    assert state.list_all_found() == ['seed', 'foo', 'bar']


def test_add_found_to_existing():
    state = MypyindState('seed')
    state.add_found('foo', 'bar')
    state.add_found('foo', 'baz')
    assert state.list_all_found() == ['seed', 'foo', 'bar', 'baz']
