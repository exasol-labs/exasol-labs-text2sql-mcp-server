###############################
## A mix of helper functions ##
###############################

import loguru
import os
import time

from cryptography.fernet import Fernet
from dotenv import load_dotenv


############################################################################
## Get the user password stored encrypted on the desktop file system      ##
##------------------------------------------------------------------------##
## This tools requires special attention. Limit access to this tool for   ##
## yourself only. Execution rights to this tool enables read of password. ##
############################################################################

def get_user_password() -> str:

    load_dotenv()

    secret_key = os.getenv("MCP_SERVER_EXASOL_SECRET_KEY")
    assert secret_key is not None, "Please set SECRET_KEY environment variable"
    fernet = Fernet(secret_key)

    stored_password = os.getenv("MCP_EXASOL_DATABASE_PASSWORD")

    return fernet.decrypt(stored_password).decode()


###############################
## Build env from .env file  ##
###############################


def get_environment() -> dict:

    load_dotenv()

    secret_key = os.getenv("EXA_MCP_SECRET_KEY")
    assert secret_key is not None, "Please set 'MCP_SERVER_EXASOL_SECRET_KEY' environment variable"
    fernet = Fernet(secret_key)
    stored_password = os.getenv("EXA_CRYPTED_PASSWORD")
    db_password =  fernet.decrypt(stored_password).decode()

    env = {
            "dsn": os.getenv("EXA_DSN"),
            "db_user": os.getenv("EXA_USER"),
            "db_password": db_password,
            "llm_server_url": os.getenv("EXA_MCP_LLM_SERVER_URL"),
            "llm_server_api_token": os.getenv("EXA_MCP_LLM_SERVER_API_KEY"),
            "llm_server_model_check": os.getenv("EXA_MCP_LLM_TRANSFORMATION"),
            "llm_server_sql_transform": os.getenv("EXA_MCP_LLM_TRANSFORMATION"),
            "llm_server_result_rendering": os.getenv("EXA_MCP_LLM_RENDERING"),
            "vectordb_persistent_storage": os.getenv("EXA_MCP_VECTORDB_FILE"),
            "vectordb_similarity_distance": os.getenv("EXA_MCP_VECTORDB_SIMILARITY_DISTANCE"),
            "logger": os.getenv("EXA_MCP_LOGGER"),
            "logger_mode": os.getenv("EXA_MCP_LOGGER_MODE").lower(),
            "logger_destination": os.getenv("EXA_MCP_LOGGER_FILE"),
            "temperature_relevance_check": os.getenv("EXA_MCP_LLM_TEMPERATURE_RELEVANCE"),
            "temperature_translation": os.getenv("EXA_MCP_LLM_TEMPERATURE_TRANSLATION"),
            "temperature_query_rewrite": os.getenv("EXA_MCP_LLM_TEMPERATURE_QUERY_REWRITE"),
            "temperature_rendering": os.getenv("EXA_MCP_LLM_TEMPERATURE_RENDERING"),
            "temperature_info": os.getenv("EXA_MCP_LLM_TEMPERATURE_INFO"),






        }

    return env


##############################################
## A tiny helper for printing elapsed times ##
##############################################

def elapsed_time(logging: bool, logger: loguru.logger, start_time, label) -> None:

    if logging:
        et = time.time() - start_time
        logger.info(f"{label}: {et:.2f} seconds")


#################################
## A tiny Helper to set labels ##
#################################

def set_logging_label(logging: bool, logger: loguru.logger, label: str) -> None:

    if logging:
        logger.info(label)
