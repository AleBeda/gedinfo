"""Exception taxonomy for gedinfo.

``UserError`` marks errors whose message is meant for end users: the CLI
prints it tersely (no traceback, exit code 1). It subclasses ``ValueError``
so existing ``except ValueError`` / ``pytest.raises(ValueError)`` call sites
keep working. Genuine programming errors must NOT use it — they should
surface as tracebacks.
"""

from __future__ import annotations


class UserError(ValueError):
    """An error whose message should be shown to the user without a traceback."""
