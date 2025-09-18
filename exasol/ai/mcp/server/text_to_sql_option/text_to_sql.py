############################################################
## Exasol MCP server with Text-to-SQL query option        ##
##--------------------------------------------------------##
## Version 0.1 DirkB@Exasol : Initial version             ##
############################################################

#######################
## Required Packages ##
#######################

import chromadb
from datetime import datetime
import time
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from loguru import logger
from pydantic import BaseModel, Field
import pyexasol
from pyexasol.exceptions import ExaConnectionError, ExaAuthError
from pyexasol import ExaConnection, ExaError
import re
from sql_formatter.core import format_sql
import sys
from typing_extensions import TypedDict

## Project packages

from exasol.ai.mcp.server.server_settings import ExaDbResult
from exasol.ai.mcp.server.text_to_sql_option.utils.helpers import get_environment
from exasol.ai.mcp.server.text_to_sql_option.utils.helpers import elapsed_time
from exasol.ai.mcp.server.text_to_sql_option.utils.helpers import set_logging_label
from exasol.ai.mcp.server.text_to_sql_option.utils.database_functions import t2s_database_schema
from exasol.ai.mcp.server.text_to_sql_option.utils.database_functions import get_sql_query_type
from exasol.ai.mcp.server.text_to_sql_option.utils.load_prompts import load_translation_prompt
from exasol.ai.mcp.server.text_to_sql_option.utils.load_prompts import load_render_prompt


#########################
## Get the environment ##
#########################

env = get_environment()


########################
## Set-Up Logging     ##
########################

LOGGING = env['logger']
LOGGING_MODE = env['logger_mode']

logger.add(sys.stdout, colorize=True, format="<green>{time}</green> <level>{message}</level>", filter="my_module", level="INFO")
logger.add(env['logger_destination'])

exa_connection: ExaConnection = None

#######################################################
## Working status of Text2SQL transformation process ##
#######################################################

class GraphState(TypedDict):
    question: str                 # The natural language question
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


##################################################################
## Check if human question relates to requested database schema ##
##################################################################

class CheckIsRelevant(BaseModel):
    is_relevant: str = Field(
        description="Checks, if the question is related to the database schema. 'YES' or 'NO'."
    )

def t2s_check_relevance(state: GraphState) -> str:

    set_logging_label(logging=LOGGING, logger=logger, label="----- t2s_check_relevance -----")
    start_time = time.time()

    system_prompt = f"""
    You are an assistant that checks if the given human question: 
    
    {state['question']}
    
    relates to the following database schema
    
    {state['db_schema']}
    
    Answer with "YES" if question relates to the given schema, otherwise answer with "NO", only!
    """

    llm = ChatOpenAI(model_name=env["llm_server_model_check"],
                     temperature=0.0,
                     openai_api_base=env["llm_server_url"],
                     openai_api_key=env["llm_server_api_token"])

    question = state['question']

    t2s_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", "Question: {question}"),
        ]
    )
    structured_llm = llm.with_structured_output(CheckIsRelevant)
    is_relevant_checker = t2s_prompt | structured_llm
    result = is_relevant_checker.invoke({"question": question})

    state['is_relevant'] = result.is_relevant

    if LOGGING == 'True' and LOGGING_MODE == 'debug':
        logger.debug(f"RESULT: {result.is_relevant}")

    elapsed_time(logging=LOGGING, logger=logger, start_time=start_time, label="Time needed for Relevance test" )

    return state


########################################################################
## Route workflow to the right path depending on determined relevance ##
########################################################################

def t2s_relevance_router(state: GraphState) -> str:

    if state['is_relevant'].upper() == "YES":
        return "YES"
    else:
        return "NO"


#############################################################################
## The core step to transform human language formulated questions into SQL ##
#############################################################################

class TransformIntoSql(BaseModel):
    sql_query: str = Field(
        description="The SQL query corresponding to the user's natural language question."
    )

def t2s_human_language_to_sql(state: GraphState):

    set_logging_label(logging=LOGGING, logger=logger, label="----- t2s_human_language_to_sql -----")

    start_time = time.time()

    state['num_of_attempts'] +=  1

    db_schema = state['db_schema']
    schema = t2s_database_schema(db_schema)

    system_prompt = load_translation_prompt(db_schema=db_schema, schema=schema)

    ##
    ## Check VectorDB for a similar question and SQL Statement,
    ## retrieve a threshold for similarity from the .env file
    ##

    try:
        vectordb_client = chromadb.PersistentClient(path=env['vectordb_persistent_storage'])
        sql_collection = vectordb_client.get_or_create_collection(name="Questions_SQL_History")
        tmp = sql_collection.query(query_texts=state['question'], n_results=1, include=["distances", "documents", "metadatas"])

        if float(tmp["distances"][0][0]) <= float(env['vectordb_similarity_distance']):
            system_prompt += f"""
                                For a similar natural language question you have created the following SQL statement:
                                
                                {tmp['metadatas'][0][0]['sql']}
                                
                            """
    except Exception as e:
        logger.error(f"ChromaDB - Error: {e}")

    if LOGGING == 'True' and LOGGING_MODE == 'debug':
        logger.debug(f"System-Prompt for translation: {system_prompt}")


    llm = ChatOpenAI(model_name=env["llm_server_sql_transform"],
                     temperature = 0.0,
                     openai_api_base=env["llm_server_url"],
                     openai_api_key=env["llm_server_api_token"]).with_structured_output(TransformIntoSql)

    question = state['question']

    t2s_prompt = ChatPromptTemplate.from_messages(
        [
            ( "system", system_prompt),
            ( "user", "Question: {question}" ),
        ]
    )

    sql_process = t2s_prompt | llm
    result = sql_process.invoke({"question": question})
    state["sql_statement"] = result.sql_query

    if LOGGING == 'True' and LOGGING_MODE == 'debug':
        sql_for_logger = format_sql(result.sql_query)
        logger.debug(f"SQL created: \n \n {sql_for_logger} \n\n")

    elapsed_time(logging=LOGGING, logger=logger, start_time=start_time, label="Time needed for SQL Creation")

    return  state


########################################################
## Check, if we allow the SQL statement for execution ##
########################################################

def t2s_check_sql_is_allowed(state: GraphState):

    set_logging_label(logging=LOGGING, logger=logger, label="----- t2s_check_sql_is_allowed -----")

    if get_sql_query_type(state["sql_statement"]):
        state['is_allowed'] = "YES"
    else:
        state['is_allowed'] = "NO"

    return state


def t2s_check_sql_router(state: GraphState):

    if get_sql_query_type(state["sql_statement"]):
        state['is_allowed'] = "YES"
    else:
        state['is_allowed'] = "NO"

    if LOGGING == 'True' and LOGGING_MODE == 'debug':
        logger.debug(f"SQL-ALLOWED: {state['is_allowed']}")

    return state['is_allowed']

#######################
## Execute the query ##
#######################

def t2s_execute_query(state: GraphState):

    set_logging_label(logging=LOGGING, logger=logger, label="----- t2s_execute_query -----")

    try:
        start_time_exa_conn = time.time()
        with pyexasol.connect(dsn=env['dsn'], user=env['db_user'], password=env['db_password'], schema=state['db_schema']) as C:
            elapsed_time(logging=LOGGING, logger=logger, start_time=start_time_exa_conn, label="Elapsed Time on Exasol-DB - Create Connection")

            start_time_exa_query = time.time()

            rows = C.execute(state['sql_statement']).fetchall()
            cols = C.meta.sql_columns(state['sql_statement'])

            elapsed_time(logging=LOGGING, logger=logger, start_time=start_time_exa_query, label="Elapsed Time on Exasol-DB - Execute Query")

            col_names = tuple(cols.keys())
            rows.insert(0, col_names)

            state['query_result'] = str(ExaDbResult(rows))
            state['query_num_rows'] = C.last_statement().rowcount()

    except ExaError as e:
        state['sql_is_valid'] = "NO"
        state['sql_error'] = str(e)
        logger.error(f"SQL Execution Error: {e}")
    else:
        state['sql_is_valid'] = "YES"
        state['sql_error'] = "None"

        ## Store the generated SQL statement and the natural language question into a VectorDB
        ## We will use it for similarity search and may add this query to the prompt for future
        ## natural language questions

        if rows is not None:
            if LOGGING == 'True' and LOGGING_MODE == 'debug':
                logger.debug("STEP: Storing or updating SQL statement in Vector-DB.")

            vectordb_client = chromadb.PersistentClient(path=env['vectordb_persistent_storage'])
            sql_collection = vectordb_client.get_or_create_collection(name="Questions_SQL_History")

            ## Check, if query exists in VectorDB

            start_time_chroma = time.time()

            tmp = sql_collection.query(query_texts=state['question'], n_results=1,
                                       include=["distances", "documents", "metadatas"],
                                       where={"$and": [{'user': env['db_user'].lower()},
                                                       {'db_schema': state['db_schema']},
                                                       ]
                                              },
                                       )

            ## VectorDB is empty, no distances stored:

            if not tmp["distances"][0]:
                new_idx = sql_collection.count() + 1
                sql_collection.add(
                    documents=[state['question']],
                    metadatas=[{"sql": state['sql_statement'],
                                "execution_date": str(datetime.now()),
                                "db_schema": state['db_schema'],
                                "user": env['db_user'].lower(),
                                "origin": "text-to-sql"}],
                    ids=[f"{new_idx}"]
                )
                if LOGGING == 'True' and LOGGING_MODE == 'debug':
                    logger.debug("STEP: Vector-DB-SQL initially written")

            if not tmp["distances"] or not tmp["distances"][0]:
                pass
            elif float(tmp["distances"][0][0]) > 0.0001:

                    new_idx = sql_collection.count() + 1
                    sql_collection.add(
                        documents=[state['question']],
                        metadatas=[{"sql": state['sql_statement'],
                                    "execution_date": str(datetime.now()),
                                    "db_schema": state['db_schema'],
                                    "user": env['db_user'].lower(),
                                    "origin": "text-to-sql"}],
                        ids=[f"{new_idx}"]
                    )
                    if LOGGING == 'True' and LOGGING_MODE == 'debug':
                        logger.debug("STEP: Vector-DB-SQL written")
            else:
                sql_collection.update(
                    ids=[ tmp['ids'][0][0] ],
                    metadatas=[ {"execution_date": str(datetime.now())} ]
                )
                if LOGGING == 'True' and LOGGING_MODE == 'debug':
                    logger.debug("STEP: Vector-DB-SQL initially updated")

            elapsed_time(logging=LOGGING, logger=logger, start_time=start_time_chroma, label="Elapsed Time on VectorDB")

    return state


##########################################################################
## Check, if the SQL statement execution was correct or raised an error ##
##########################################################################

def t2s_check_sql_valid(state: GraphState):

    if state['sql_error'] == "None":
        state['sql_is_valid'] = "YES"
    else:
        state['sql_is_valid'] = "NO"

    return state

def t2s_sql_valid_router(state: GraphState) -> str:

    if state['sql_is_valid'].upper() == "YES":
        return "YES"
    else:
        return "NO"


##################################################
## Post-Processing of the SQL execution process ##
##################################################

class DisplayResult(BaseModel):
    display_result: str = Field(
        description="The result set converted into a nice and shiny table in MARKDOWN syntax."
    )


def t2s_show_answer(state: GraphState):

    set_logging_label(logging=LOGGING, logger=logger, label="----- t2s_show_answer -----")
    start_time = time.time()

    result = re.search(r"(\[.*\])", state['query_result'])
    result_set = result.group(0)

    schema = t2s_database_schema(state['db_schema'])
    system_prompt = load_render_prompt(db_schema=state['db_schema'], schema=schema)

    question = f"""Transform the dataset below into a table in markdown syntax. For a result
    with one value only, build a table with one column:
    
    {result_set}
    """

    if LOGGING == 'True' and LOGGING_MODE == 'debug':
        logger.debug(f"System-Prompt: \n \n {system_prompt} \n\n")
        logger.debug(f"Question:: \n \n {question} \n\n")

    llm = ChatOpenAI(model_name=env["llm_server_result_rendering"],
                     temperature=0.0,
                     openai_api_base=env["llm_server_url"],
                     openai_api_key=env["llm_server_api_token"]).with_structured_output(DisplayResult)

    t2s_prompt = ChatPromptTemplate.from_messages(
        [
            ( "system", system_prompt),
            ( "user", "Question: {question}" ),
        ]
    )

    render_process = t2s_prompt | llm
    result = render_process.invoke({"question": question})
    state["display_result"] = str(result.display_result)

    elapsed_time(logging=LOGGING, logger=logger, start_time=start_time, label="Time needed for rendering answer")

    return state


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

    llm = ChatOpenAI(model_name=env["llm_server_sql_transform"],
                     temperature=0.5,
                     openai_api_base=env["llm_server_url"],
                     openai_api_key=env["llm_server_api_token"]).with_structured_output(BadRelevanceAnswer)

    t2s_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", "Question: {{info_message}}"),
        ]
    )

    info_generator = t2s_prompt | llm
    result = info_generator.invoke({"question": info_message})
    state["info"] = result.info_about_relevance

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

    env = get_environment()

    llm = ChatOpenAI(model_name=env["llm_server_sql_transform"],
                     temperature=0.7,
                     openai_api_base=env["llm_server_url"],
                     openai_api_key=env["llm_server_api_token"]).with_structured_output(UnableCreateSQL)

    t2s_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", "Question: {{info_message}}"),
        ]
    )

    info_generator = t2s_prompt | llm
    result = info_generator.invoke({"question": info_message})
    state["info"] = result.info_unable_create_sql

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

    llm = ChatOpenAI(model_name=env["llm_server_sql_transform"],
                     temperature=0.7,
                     openai_api_base=env["llm_server_url"],
                     openai_api_key=env["llm_server_api_token"]).with_structured_output(SQLTypeNotAllowed)

    t2s_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", "Question: {{info_message}}"),
        ]
    )

    info_generator = t2s_prompt | llm
    result = info_generator.invoke({"question": info_message})
    state["info"] = result.info_about_bad_sql_type

    return state


#########################################################
## Rewriting the question to try a new SQL translation ##
#########################################################

class NewVersionOfQuestion(BaseModel):
    new_question: str = Field(
        description="Reformulated Question to gain a valid SQL transformation."
    )
def t2s_correct_query(state: GraphState):

    set_logging_label(logging=LOGGING, logger=logger, label="----- t2s_correct_query -----")

    ## Reformulate the question to initiate a new SQL translation

    system_prompt = "You are a correcting assistant and re-write the question, but keep the semantics."
    info_message = f"Rewrite the following question: {state['question']} "

    llm = ChatOpenAI(model_name=env["llm_server_sql_transform"],
                     temperature=0.7,
                     openai_api_base=env["llm_server_url"],
                     openai_api_key=env["llm_server_api_token"]).with_structured_output(NewVersionOfQuestion)

    t2s_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", "Question: {{info_message}}"),
        ]
    )

    info_generator = t2s_prompt | llm
    result = info_generator.invoke({"question": info_message})
    state["question"] = result.new_question

    return state


def t2s_max_tries_router(state: GraphState) -> str:

    if state['num_of_attempts'] >= 3:
        return "YES"
    else:
        return "NO"


def t2s_check_max_tries(state: GraphState) -> str:
    return state

def t2s_sql_execution_router(state: GraphState):
    return state

############################################################################
## The Process Flow to create transformation of natural language into SQL ##
############################################################################

async def t2s_start_process(state: GraphState):

    ## Create a connection to the Exasol database ##

    total_start_time = time.time()

    set_logging_label(logging=LOGGING, logger=logger, label="########## Begin of Translation Process ##########")

    state['is_allowed'] = "NO"
    state['sql_is_valid'] = "NO"
    state['num_of_attempts'] = 0
    state['display_result'] = ""

    workflow = StateGraph(GraphState)

    workflow.add_edge(START, "check_relevance")
    workflow.add_node("check_relevance", t2s_check_relevance)
    workflow.add_node("transform_into_sql", t2s_human_language_to_sql)
    workflow.add_node("info_unable_query_type", t2s_info_unable_query_type)
    workflow.add_node("check_sql_is_allowed", t2s_check_sql_is_allowed)
    workflow.add_node("execute_query", t2s_execute_query)
    workflow.add_node("show_answer", t2s_show_answer)
    workflow.add_node("info_query_not_relevant", t2s_info_query_not_relevant)
    workflow.add_node("correct_query", t2s_correct_query)
    workflow.add_node("check_max_tries", t2s_check_max_tries)
    workflow.add_node("info_unable_create_sql", t2s_info_unable_create_sql)
    workflow.add_node("check_sql_valid", t2s_check_sql_valid)

    workflow.add_conditional_edges(
        "check_relevance",
        t2s_relevance_router,
        {
            "YES": "transform_into_sql",
            "NO": "info_query_not_relevant",
        },
    )

    workflow.add_conditional_edges(
        "check_max_tries",
        t2s_max_tries_router,
        {
            "NO": "correct_query",
            "YES": "info_unable_create_sql"
        }

    )

    workflow.add_edge("transform_into_sql", "check_sql_is_allowed")

    workflow.add_conditional_edges(
        "check_sql_is_allowed",
        t2s_check_sql_router,
        {
            "YES": "execute_query",
            "NO": "info_unable_query_type",
        }
    )

    workflow.add_edge("execute_query", "check_sql_valid")

    workflow.add_conditional_edges(
        "check_sql_valid",
        t2s_sql_valid_router,
        {
            "YES": "show_answer",
            "NO": "check_max_tries"
        }
    )

    workflow.add_edge("show_answer", END)
    workflow.add_edge("correct_query", "transform_into_sql")
    workflow.add_edge("info_query_not_relevant", END)
    workflow.add_edge("info_unable_create_sql", END)

    t2s_process = workflow.compile()

    state = await t2s_process.ainvoke(state)

    set_logging_label(logging=LOGGING, logger=logger, label="\n")
    elapsed_time(logging=LOGGING, logger=logger, start_time=total_start_time, label="Total Time")
    set_logging_label(logging=LOGGING, logger=logger, label="########## End of Translation Process #########\n\n\n")

    return state


