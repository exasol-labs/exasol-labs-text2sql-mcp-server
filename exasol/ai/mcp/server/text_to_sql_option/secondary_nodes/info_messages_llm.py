


from pydantic import BaseModel, Field

from exasol.ai.mcp.server.text_to_sql_option.intro.intro import env, GraphState,logger, LOGGING, LOGGING_MODE
from exasol.ai.mcp.server.text_to_sql_option.utilities.helpers import set_logging_label
from exasol.ai.mcp.server.text_to_sql_option.utilities.llm import invoke_llm

###############################################################################################
## Inform user that query seems to be not relevant / does not fit to desired database schema ##
###############################################################################################

class BadRelevanceAnswer(BaseModel):
    info_about_relevance: str = Field(
        description="Informing the user about question and database schema mismatch"
    )

def t2s_info_query_not_relevant(state: GraphState):

    set_logging_label(logging=LOGGING, logger=logger, label="----- t2s_info_query_not_relevant -----")

    system_prompt = "You are a educative assistant who responds in a strict manner!"
    info_message = "The human question and the database schema do not fit together!"

    result = invoke_llm(base=env["llm_server_url"],
                        api=env["llm_server_api_token"],
                        model=env["llm_server_model_check"],
                        temperature=env['temperature_info'],
                        prompt=system_prompt,
                        query=info_message,
                        output=BadRelevanceAnswer)

    state["info"] = result.info_about_relevance

    return state


##############################################################################
## Inform user that (currently) on 'SELECT' (READ-ONLY) queries are allowed ##
##############################################################################

class SQLTypeNotAllowed(BaseModel):
    info_about_bad_sql_type: str = Field(
        description="Informing the user that the type of the SQL statement is not allowed."
    )

def t2s_info_unable_query_type(state: GraphState):

    set_logging_label(logging=LOGGING, logger=logger, label="----- t2s_info_unable_query_type -----")

    system_prompt = "You are a educative assistant who responds in a strict manner"
    info_message = "Explain: The SQL query type is not allowed."

    result = invoke_llm(base=env["llm_server_url"],
                        api=env["llm_server_api_token"],
                        model=env["llm_server_model_check"],
                        temperature=env['temperature_info'],
                        prompt=system_prompt,
                        query=info_message,
                        output=SQLTypeNotAllowed)

    state["info"] = result.info_about_bad_sql_type

    return state

##############################################################################################
## Inform user that the text-to-sql tool cannot create a valid SQL statement in 3 attempts. ##
##############################################################################################

class UnableCreateSQL(BaseModel):
    info_unable_create_sql: str = Field(
        description="Informing the user that the text-to-sql tool cannot create a valid SQL statement"
    )

def t2s_info_unable_create_sql(state: GraphState):

    set_logging_label(logging=LOGGING, logger=logger, label="----- t2s_info_unable_create_sql -----")

    system_prompt = "You are a educative assistant who responds in a strict manner."
    info_message = "Text-to-SQL tool cannot create a valid SQL statement, explain the SQL dialect does not work."

    result = invoke_llm(base=env["llm_server_url"],
                        api=env["llm_server_api_token"],
                        model=env["llm_server_model_check"],
                        temperature=env['temperature_info'],
                        prompt=system_prompt,
                        query=info_message,
                        output=UnableCreateSQL)

    state["info"] = result.info_unable_create_sql

    return state
