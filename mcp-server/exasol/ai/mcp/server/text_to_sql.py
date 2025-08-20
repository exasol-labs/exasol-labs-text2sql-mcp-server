
import os
import pandas as pd
import pyexasol
#from mypy.state import state
from pyexasol import ExaError

import sys

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from openai import OpenAI
from pandas import DataFrame
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


from sqlglot import (
    exp,
    parse_one,
)
from sqlglot.errors import ParseError


from exa_prompt.src.exa_prompt.load_prompt import load_prompt
from exasol.ai.mcp.server.server_settings import ExaDbResult





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

    secret_key = os.getenv("MCP_SERVER_EXASOL_SECRET_KEY")
    assert secret_key is not None, "Please set SECRET_KEY environment variable"
    fernet = Fernet(secret_key)
    stored_password = os.getenv("MCP_EXASOL_DATABASE_PASSWORD")
    db_password =  fernet.decrypt(stored_password).decode()

    env = {
            "dsn": os.getenv("MCP_EXASOL_DATABASE_HOST"),
            "db_user": os.getenv("MCP_EXASOL_DATABASE_USER"),
            "db_password": db_password,
            "llm_server_url": os.getenv("MCP_OPENAI_SERVER_URL"),
            "llm_server_api_token": os.getenv("MCP_OPENAI_SERVER_API_KEY"),
            "llm_server_model_check": os.getenv("MCP_OPENAI_SERVER_MODEL_NAME"),
            "llm_server_sql_transform": os.getenv("MCP_OPENAI_SERVER_MODEL_NAME"),
        }

    return env




#######################################################
## Working status of Text2SQL transformation process ##
#######################################################

class GraphState(TypedDict):
    question: str
    db_schema: str
    sql_statement: str
    query_num_rows: int
    query_result: str
    display_result: str
    num_of_attempts: int
    is_allowed: str
    is_relevant: str
    sql_is_valid: str
    sql_error: str
    info: str


############################################################
## Retrieve the metadata for the required database schema ##
#############################################################

def t2s_database_schema(db_schema: str, env: dict) -> str:

    with pyexasol.connect(dsn=env['dsn'], user=env['db_user'], password=env['db_password'], schema='SYS') as c:
        metadata_query = f"""
            SELECT 
                COLUMN_SCHEMA,
                COLUMN_TABLE,
                COLUMN_NAME,
                COLUMN_TYPE,
                COLUMN_COMMENT
            FROM 
                "SYS"."EXA_ALL_COLUMNS"
            WHERE
                COLUMN_SCHEMA = '{db_schema}'
            ORDER BY 
                COLUMN_SCHEMA, COLUMN_TABLE;
        """

        stmt = c.execute(metadata_query)

        schema_metadata = ""
        table, old_table = "", ""

        for row in stmt:
            db_schema = row[0]
            table = row[1]
            if table != old_table:
                schema_metadata += f"\n Table '{db_schema}.{table}': \n Columns: \n"

            if row[4] is None:
                comment = "No comment"
            else:
                comment = row[4]

            schema_metadata += "\t - " + row[2] + ": " + row[3] + '  ::  ' + comment + "\n"
            old_table = table

    print("schema_metadata", file=sys.stderr)

    return schema_metadata

##################################################################
## Check if human question relates to requested database schema ##
##################################################################

class CheckIsRelevant(BaseModel):
    is_relevant: str = Field(
        description="Checks if the question is related to the database schema. 'YES' or 'NO'."
    )

def t2s_check_relevance(state: GraphState) -> str:

    env = get_environment()

    system_prompt = f"""
    You are an assistant that checks if the given human question: 
    
    {state['question']}
    
    relates to the following database schema
    
    {state['db_schema']}
    
    Answer with "YES" if question relates to the given schema, otherwise answer with "NO", only!
    """

    llm = ChatOpenAI(model_name=env["llm_server_sql_transform"],
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

    state['num_of_attempts'] +=  1

    env = get_environment()

    db_schema = state['db_schema']
    schema = t2s_database_schema(db_schema, env)

    system_prompt = load_prompt(db_schema=db_schema, schema=schema)

    print(f"Prompt: {system_prompt}", file=sys.stderr)


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

    print(f"SQL-Statement: {state['sql_statement']}", file=sys.stderr)

    return  state


#######################################################
## Is the execution of the SQL statement permissible ##
##---------------------------------------------------##
## Currently, only 'SELECT' statements are permitted ##
#######################################################

def t2s_get_sql_query_type(query: str) -> bool:
    """
    Verifies that the query is a valid SELECT query.
    Declines any other types of statements including the SELECT INTO.
    """
    try:
        ast = parse_one(query, read="exasol")
        if isinstance(ast, exp.Select):
            return "into" not in ast.args
        return False
    except ParseError:
        return False


def t2s_check_sql_is_allowed(state: GraphState):

    if t2s_get_sql_query_type(state["sql_statement"]):
        state['is_allowed'] = "YES"
    else:
        state['is_allowed'] = "NO"

    return state


def t2s_check_sql_router(state: GraphState):

    print("##### CHECK QUERY TYPE", file=sys.stderr)

    if t2s_get_sql_query_type(state["sql_statement"]):
        state['is_allowed'] = "YES"
        print(f"##### END of CHECK QUERY TYPE ::: {state['is_allowed']}", file=sys.stderr)
        return "YES"
    else:
        state['is_allowed'] = "NO"
        print(f"##### END of CHECK QUERY TYPE ::: {state['is_allowed']}", file=sys.stderr)
        return "NO"


    #return state


#######################
## Execute the query ##
#######################

def t2s_execute_query(state: GraphState):

    print(f"#### Beginning of SQL Execution ::: state['sql_statement']", file=sys.stderr)

    env = get_environment()
    try:
        with pyexasol.connect(dsn=env['dsn'], user=env['db_user'], password=env['db_password'], schema=state['db_schema']) as c:
            rows = c.execute(state['sql_statement']).fetchall()
            #rows = c.export_to_pandas(state['sql_statement'])

            state['query_result'] = str(ExaDbResult(rows))

    except ExaError as e:
        state['sql_is_valid'] = "NO"
        print(f"##### ERROR-EXECUTION: {e}")
    else:
        state['sql_is_valid'] = "YES"
        state['sql_error'] = "None"

    print("#### End of SQL Execution", file=sys.stderr)

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

    env = get_environment()

    state['display_result'] = state['query_result']

    print(f" ", file=sys.stderr)
    print(f"Show-Answer :: {state['query_result']}", file=sys.stderr)
    print(f"Show-Answer-2 :: {state['display_result']}", file=sys.stderr)
    print(f" ", file=sys.stderr)

    return state


###############################################################################################
## Inform user that query seems to be not relevant / does not fit to desired database schema ##
###############################################################################################

class BadRelevanceAnswer(BaseModel):
    info_about_relevance: str = Field(
        description="Informing the user about question and database schema mismatch"
    )

def t2s_info_query_not_relevant(state: GraphState):

    system_prompt = "You are a educative assistant who responds in a strict manner!"
    info_message = "The human question and the database schema do not fit together!"

    env = get_environment()

    llm = ChatOpenAI(model_name=env["llm_server_sql_transform"],
                     temperature=0.0,
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
    system_prompt = "You are a educative assistant who responds in a strict manner"
    info_message = "Explain: The SQL query type is not allowed."

    env = get_environment()

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

def t2s_correct_query(state: GraphState):
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

async def start_t2s_process(state: GraphState):

    state['is_allowed'] = "NO"
    state['sql_is_valid'] = "NO"
    state['num_of_attempts'] = 0
    state['display_result'] = ""

    workflow = StateGraph(GraphState)

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

    workflow.add_edge(START, "check_relevance")

    workflow.add_conditional_edges(
        "check_relevance",
        t2s_relevance_router,
        {
            "YES": "transform_into_sql",
            "NO": "info_query_not_relevant",
        },
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


    workflow.add_conditional_edges(
        "check_max_tries",
        t2s_max_tries_router,
        {
            "NO": "correct_query",
            "YES": "info_unable_create_sql"
        }

    )

    workflow.add_conditional_edges(
        "check_sql_is_allowed",
        t2s_check_sql_router,
        {
            "YES": "execute_query",
            "NO": "info_unable_query_type",
        }
    )

    workflow.add_edge("transform_into_sql", "check_sql_is_allowed")
    #workflow.add_edge("transform_into_sql", "execute_query")
    workflow.add_edge("correct_query", "transform_into_sql")
    workflow.add_edge("info_query_not_relevant", END)
    workflow.add_edge("info_unable_create_sql", END)

    ## to be changed
    # workflow.add_edge("execute_query", "show_answer")
    workflow.add_edge("show_answer", END)

    t2s_process = workflow.compile()

    state = await t2s_process.ainvoke(state)

    return state