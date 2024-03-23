from utils import *

def pytest_configure(config):
    """
    Delete any stale databases before running tests.
    """
    delete_botex_db()
    delete_otree_db()
