

from text_to_sql_option.intro.intro import logger, GraphState, LOGGING, LOGGING_MODE
from text_to_sql_option.utilities.database_functions import get_sql_query_type


def t2s_check_sql_router(state: GraphState):

    if get_sql_query_type(state["sql_statement"]):
        state['is_allowed'] = "YES"
    else:
        state['is_allowed'] = "NO"

    if LOGGING == 'True' and LOGGING_MODE == 'debug':
        logger.debug(f"SQL-ALLOWED: {state['is_allowed']}")

    return state['is_allowed']

########################################################################
## Route workflow to the right path depending on determined relevance ##
########################################################################

def t2s_relevance_router(state: GraphState) -> str:

    if state['is_relevant'].upper() == "YES":
        return "YES"
    else:
        return "NO"

def t2s_sql_valid_router(state: GraphState) -> str:

    if state['sql_is_valid'].upper() == "YES":
        return "YES"
    else:
        return "NO"


def t2s_max_tries_router(state: GraphState) -> str:

    if state['num_of_attempts'] >= 3:
        return "YES"
    else:
        return "NO"