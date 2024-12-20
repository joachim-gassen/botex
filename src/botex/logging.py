import logging

def setup_logging():
    logger = logging.getLogger("botex")
    logger.addHandler(logging.NullHandler())
    return logger