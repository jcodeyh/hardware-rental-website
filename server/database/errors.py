class DuplicateUserError(Exception):
    """Raised when attempting to insert a new user that already exists to the database."""
    pass