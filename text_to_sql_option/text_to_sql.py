##############################################################
## Exasol MCP server with Text-to-SQL query option          ##
## Module: Text to SQL translation                          ##
##----------------------------------------------------------##
## Version 1.0.0 DirkB@Exasol : Initial version             ##
##############################################################

import chromadb
import pyexasol
import re
import time

from datetime import datetime
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from pyexasol import ExaConnection, ExaError
from sql_formatter.core import format_sql

## Project packages

from exasol.ai.mcp.server.server_settings import ExaDbResult
from text_to_sql_option.intro.intro import (
    env,
    GraphState,
    logger,
    LOGGING,
    LOGGING_MODE
)
from text_to_sql_option.utilities.helpers import elapsed_time
from text_to_sql_option.utilities.llm import invoke_llm
from text_to_sql_option.utilities.helpers import set_logging_label
from text_to_sql_option.utilities.database_functions import t2s_database_schema
from text_to_sql_option.utilities.database_functions import get_sql_query_type
from text_to_sql_option.utilities.load_prompts import load_translation_prompt
from text_to_sql_option.utilities.load_prompts import load_render_prompt
from text_to_sql_option.secondary_nodes.info_messages_llm import (
    t2s_info_query_not_relevant,
    t2s_info_unable_query_type,
    t2s_info_unable_create_sql
)
from text_to_sql_option.secondary_nodes.routing import (
    t2s_check_sql_router,
    t2s_relevance_router,
    t2s_sql_valid_router,
    t2s_max_tries_router
)

exa_connection: ExaConnection = None


##################################################################
## Check if human question relates to requested database schema ##
##################################################################

class CheckIsRelevant(BaseModel):
    is_relevant: str = Field(
        description="Checks, if the question is related to the database schema. 'YES' or 'NO'."
    )

def t2s_check_relevance(state: GraphState) -> str:

    set_logging_label(logging=LOGGING, logger=logger, label="----- t2s_check_relevance -----")
    start_time_relevance_test = time.time()

    schema = t2s_database_schema(db_schema=state['db_schema'])

    system_prompt = f"""
    You are an assistant that checks if the given human question: 
    
    {state['question']}
    
    relates to the following database schema
    
    {schema}
    
    Answer with "YES" if question relates to the given schema, otherwise answer with "NO", only!
    """
    start_time_relevance_test = time.time()
    result = invoke_llm(base=env["llm_server_url"],
                                      api=env["llm_server_api_token"],
                                      model=env["llm_server_model_check"],
                                      temperature=env['temperature_relevance_check'],
                                      prompt=system_prompt,
                                      query=state['question'],
                                      output=CheckIsRelevant)
    elapsed_time(logging=LOGGING, logger=logger, start_time=start_time_relevance_test, label="Time needed for Relevance test")

    state['is_relevant'] = result.is_relevant

    if LOGGING == 'True' and LOGGING_MODE == 'debug':
        logger.debug(f"RESULT: {result.is_relevant}")

    return state


#############################################################################
## The core step to transform human language formulated questions into SQL ##
#############################################################################

class TransformIntoSql(BaseModel):
    sql_query: str = Field(
        description="The SQL query corresponding to the user's natural language question."
    )

def t2s_human_language_to_sql(state: GraphState):

    set_logging_label(logging=LOGGING, logger=logger, label="----- t2s_human_language_to_sql -----")

    state['num_of_attempts'] +=  1

    db_schema = state['db_schema']

    schema = t2s_database_schema(db_schema)

    system_prompt = load_translation_prompt(db_schema=db_schema, schema=schema)
    system_prompt_length = len(system_prompt)

    ##
    ## Check VectorDB for a similar question and SQL Statement,
    ## retrieve a threshold for similarity from the .env file
    ##

    try:
        vectordb_client = chromadb.PersistentClient(path=env['vectordb_persistent_storage'])
        sql_collection = vectordb_client.get_or_create_collection(name="SQL_Audit")
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


    start_time_llm = time.time()
    result = invoke_llm(base=env["llm_server_url"],
                        api=env["llm_server_api_token"],
                        model=env["llm_server_model_check"],
                        temperature=env['temperature_translation'],
                        prompt=system_prompt,
                        query=state['question'],
                        output=TransformIntoSql)



    elapsed_time(logging=LOGGING, logger=logger, start_time=start_time_llm, label=f"Time needed for SQL Creation (Prompt-Length: {system_prompt_length})")

    state["sql_statement"] = result.sql_query

    if LOGGING == 'True' and LOGGING_MODE == 'debug':
        sql_for_logger = format_sql(result.sql_query)
        logger.debug(f"SQL created: \n \n {sql_for_logger} \n\n")



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
            sql_collection = vectordb_client.get_or_create_collection(name="SQL_Audit")

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


##################################################
## Post-Processing of the SQL execution process ##
##################################################

class DisplayResult(BaseModel):
    display_result: str = Field(
        description="The result set converted into a nice and shiny table in MARKDOWN syntax."
    )

def t2s_show_answer(state: GraphState):

    set_logging_label(logging=LOGGING, logger=logger, label="----- t2s_show_answer -----")


    result = re.search(r"(\[.*\])", state['query_result'])
    result_set = result.group(0)

    system_prompt = load_render_prompt(db_schema=state['db_schema'])
    system_prompt_length = len(system_prompt)

    question = f"""Transform the dataset below into a table in markdown syntax. For a result
    with one value only, build a table with one column:
    
    {result_set}
    """

    if LOGGING == 'True' and LOGGING_MODE == 'debug':
        logger.debug(f"System-Prompt: \n \n {system_prompt} \n\n")
        logger.debug(f"Question:: \n \n {question} \n\n")

    start_time_render = time.time()
    result = invoke_llm(base=env["llm_server_url"],
                        api=env["llm_server_api_token"],
                        model=env["llm_server_model_check"],
                        temperature=env['temperature_rendering'],
                        prompt=system_prompt,
                        query=state['question'],
                        output=DisplayResult)

    state["display_result"] = str(result.display_result)

    elapsed_time(logging=LOGGING, logger=logger, start_time=start_time_render, label=f"Time needed for rendering answer (Prompt-Length: {system_prompt_length})")

    return state


#########################################################
## Rewriting the question to try a new SQL translation ##
#########################################################

class NewVariantOfQuestion(BaseModel):
    new_question: str = Field(
        description="Reformulated Question to gain a valid SQL transformation."
    )
def t2s_correct_query(state: GraphState):

    set_logging_label(logging=LOGGING, logger=logger, label="----- t2s_correct_query -----")

    ## Reformulate the question to initiate a new SQL translation

    system_prompt = "You are a correcting assistant and re-write the question, but keep the semantics."
    info_message = f"Rewrite the following question: {state['question']} "

    start_time_rewrite = time.time()
    result = invoke_llm(base=env["llm_server_url"],
                        api=env["llm_server_api_token"],
                        model=env["llm_server_model_check"],
                        temperature=env['temperature_query_rewrite'],
                        prompt=system_prompt,
                        query=info_message,
                        output=NewVariantOfQuestion)
    elapsed_time(logging=LOGGING, logger=logger, start_time=start_time_rewrite, label="Time needed for rewriting question")
    state["question"] = result.new_question

    return state





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


