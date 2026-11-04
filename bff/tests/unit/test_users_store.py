import pytest

from app.modules.users.store import LocalUserStore, UserExistsError, parse_seed_users


def test_add_and_verify(tmp_path):
    store = LocalUserStore(str(tmp_path / "users.sqlite3"))
    user = store.add("Maria", "correct-horse", "AUS")
    assert user["user_id"] == "u_maria"
    assert store.verify("maria", "correct-horse")["org_id"] == "AUS"
    assert store.verify("maria", "wrong") is None
    assert store.verify("nobody", "correct-horse") is None


def test_duplicate_username_is_case_insensitive(tmp_path):
    store = LocalUserStore(str(tmp_path / "users.sqlite3"))
    store.add("maria", "correct-horse", "AUS")
    with pytest.raises(UserExistsError):
        store.add("MARIA", "other-password", "DAL")


def test_seed_is_repeatable(tmp_path):
    store = LocalUserStore(str(tmp_path / "users.sqlite3"))
    users = parse_seed_users("demo:AUS:pass:with:colons, second:DAL:password2")
    store.seed(users)
    store.seed(users)
    assert store.verify("demo", "pass:with:colons")["org_id"] == "AUS"
    assert store.verify("second", "password2")["org_id"] == "DAL"


def test_invalid_seed_entry_is_rejected():
    with pytest.raises(ValueError):
        parse_seed_users("missing-fields")
