from importlinter.application.user_options import UserOptions


def test_user_options_returns_false_on_unsupported_type_for_equality():
    options = UserOptions(session_options={}, contracts_options=[])
    result = options == 1
    assert result is False
