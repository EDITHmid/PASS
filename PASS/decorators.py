"""Simple role‑based access decorator.
Usage example:
    @role_required(['admin', 'principal'])
    def view():
        ...
If the logged‑in user does not have one of the allowed roles, a 403 response is returned.
"""

from functools import wraps
from flask import abort
from flask_login import current_user


def role_required(allowed_roles):
    """Return a decorator that restricts a view to users whose ``role``
    attribute is in ``allowed_roles``.
    ``allowed_roles`` can be a list or tuple of role strings.
    """
    if not isinstance(allowed_roles, (list, tuple, set)):
        raise TypeError("allowed_roles must be a list/tuple/set of role strings")

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(403)
            if getattr(current_user, "role", None) not in allowed_roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
