import hashlib
import hmac
import os
import sqlite3
from contextlib import closing


class UserExistsError(Exception):
    pass


def _hash_password(password, salt):
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)


def parse_seed_users(value):
    users = []
    for entry in value.split(","):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(":", 2)
        if len(parts) != 3 or not all(parts):
            raise ValueError("LOCAL_SEED_USERS entries must look like username:ORG:password")
        users.append(tuple(parts))
    return users


class LocalUserStore:
    def __init__(self, path):
        self.path = path
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS users ("
                "username TEXT PRIMARY KEY COLLATE NOCASE, "
                "user_id TEXT NOT NULL, "
                "org_id TEXT NOT NULL, "
                "password_hash BLOB NOT NULL, "
                "salt BLOB NOT NULL)"
            )

    def _connect(self):
        return sqlite3.connect(self.path)

    def add(self, username, password, org_id):
        salt = os.urandom(16)
        user = {
            "user_id": f"u_{username.lower()}",
            "username": username,
            "org_id": org_id,
        }
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute(
                    "INSERT INTO users (username, user_id, org_id, password_hash, salt) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        username,
                        user["user_id"],
                        org_id,
                        _hash_password(password, salt),
                        salt,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise UserExistsError(username) from error
        return user

    def verify(self, username, password):
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT user_id, username, org_id, password_hash, salt "
                "FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if row is None:
            return None
        user_id, stored_username, org_id, password_hash, salt = row
        if not hmac.compare_digest(password_hash, _hash_password(password, salt)):
            return None
        return {
            "user_id": user_id,
            "username": stored_username,
            "org_id": org_id,
        }

    def seed(self, users):
        for username, org_id, password in users:
            try:
                self.add(username, password, org_id)
            except UserExistsError:
                continue
