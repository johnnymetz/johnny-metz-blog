from contextlib import contextmanager

from django.db import transaction

from gevent.local import local


class TransactionState(local):
    depth = 0
    initialized = False

    def __init__(self):
        if self.initialized:
            raise SystemError("__init__ called too many times")
        self.initialized = True


_allow_transaction_state = TransactionState()


@contextmanager
def allow_transaction():
    """
    Context manager/decorator that allows transactions, even if it contains
    the no_transaction contextmanager.
    """
    _allow_transaction_state.depth += 1
    try:
        yield
    finally:
        _allow_transaction_state.depth -= 1


@contextmanager
def no_transaction(msg="Process needs to run outside a DB transaction"):
    """
    Context manager/decorator that raises an Exception if run inside a transaction.
    """
    if (
        _allow_transaction_state.depth == 0
        and transaction.get_connection().in_atomic_block
    ):
        raise transaction.TransactionManagementError(msg)

    yield
