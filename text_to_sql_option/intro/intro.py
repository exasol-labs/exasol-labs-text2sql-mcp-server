

import sys

from exasol.ai.mcp.server.db_connection import DbConnection
from loguru import logger
from typing_extensions import TypedDict

from text_to_sql_option.utilities.helpers import get_environment

env = get_environment()

#######################################################
## Working status of Text2SQL transformation process ##
#######################################################

class GraphState(TypedDict):
    question: str                 # The natural language question
    connection: DbConnection      # The database connection with Impersonation
    db_schema: str                # The database schema to be used
    sql_statement: str            # The generated SQL statement
    query_num_rows: int           # The number of rows returned
    query_result: str             # The result of the generated SQL statement
    display_result: str           # The transformed result into a visual version
    num_of_attempts: int          # The number of attempts to generate a valid SQL statement
    is_allowed: str               # Is the generated SQL statement allowed (READ-ONLY, currently)
    is_relevant: str              # Does the natural language fit to the underlying database schema
    sql_is_valid: str             # SQL statements accepted by the Exasol database
    sql_error: str                # The SQL error returned by the Exasol database, if any
    info: str                     # Additional INFO field


########################
## Set-Up Logging     ##
########################

LOGGING = env['logger']
LOGGING_MODE = env['logger_mode']

logger.add(sys.stdout, colorize=True, format="<green>{time}</green> <level>{message}</level>", filter="my_module", level="INFO")
logger.add(env['logger_destination'])


from typing import Optional


class Filter:
    def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        email_id = user.get("email")

        context_message = {
            "role": "system",
            "content": f"logged_in_user_email_id is {email_id}",
        }
        body.setdefault("messages", []).insert(0, context_message)

        return body