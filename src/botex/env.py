import os
import logging
logger = logging.getLogger("botex")

from dotenv import load_dotenv

def load_botex_env(env_file = "botex.env") -> bool:
    """
    Load botex environment variables from a file.

    Args:
        env_file (str, optional): The path to the .env file containing
            the botex configuration. Defaults to "botex.env".

    Returns:
        Bool: True if at least one botex environment variable was set.
    """
    if not os.path.exists(env_file):
        logger.warning(
            f"Could not read any botex environment variables from '{env_file}' "
            "as the file does not exist. "
            "Please make sure that the file is in the right location and that "
            "it sets the botex environment variables that you need."
        )
        return False
    success = load_dotenv(env_file)
    if success:
        logger.info(f"Loaded botex environment variables from '{env_file}'")
    else:
        logger.info(
            f"botex environment variables parsed from '{env_file}'. "
            "No new environment variables were set."
        )
    return success


