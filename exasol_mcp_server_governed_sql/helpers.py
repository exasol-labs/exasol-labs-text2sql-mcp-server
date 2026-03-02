###############################
## A mix of helper functions ##
###############################

import loguru
import os
import time


from dotenv import load_dotenv, find_dotenv


###############################
## Build env from .env file  ##
###############################


def get_environment() -> dict:

    load_dotenv(find_dotenv())

    env = {
            "dsn": os.getenv("EXA_DSN"),
            "db_user": os.getenv("EXA_USER"),
            "db_password": os.getenv("EXA_PASSWORD"),
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

    print(env)

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
