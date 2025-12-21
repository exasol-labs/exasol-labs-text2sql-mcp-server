########################################################################################################################
## Exasol MCP-Server with GovernedSQL (Text-to-SQL) option                                                            ##
##--------------------------------------------------------------------------------------------------------------------##
## This MCP Server is currently in experimental state and being hosted on Exasol-Labs (http://github.com/exasol-labs) ##
## under a pure "Love it or Leave it" rule - No liability that it always produces 100% correct SQL statements         ##
##--------------------------------------------------------------------------------------------------------------------##
## Version 1.2.1                                                                                                      ##
## 2025-12-23 Dirk Beerbohm: - Re-Designed to use the new HookUp functionality of the MCP Server                      ##
##                           - Adapted the environment variables to the official MCP-Server                           ##
##                           - Ability to store a combination of Question/SQL Statement                               ##
##                                                                                                                    ##
## Version 1.0.0                                                                                                      ##
## 2025-10-16 Dirk Beerbohm: - Initial public release; share same code base as the official MCP-Server                ##
########################################################################################################################


##
## Standard Python packages
##

import chromadb
#from dotenv import load_dotenv


##
## The "underlying" Exasol MCP Server
##

from exasol.ai.mcp.server import mcp_server
from exasol.ai.mcp.server.mcp_server import ExasolMCPServer

##
## Thext-to-SQL (GovernedSQL) packages
##

from text_to_sql_option.utilities.helpers import set_logging_label
from text_to_sql_option.sql_audit import text_to_sql_audit
from text_to_sql_option.text_to_sql import t2s_start_process
from text_to_sql_option.learn_sql import learn_sql
from text_to_sql_option.intro.intro import (
    env,
    GraphState,
    logger,
    LOGGING,
    LOGGING_MODE,
)


def text_to_sql(question: str, db_schema: str, state: GraphState):

    #if not self.config.enable_text_to_sql:
    #    raise RuntimeError("Text-to-SQL option is disabled")

    print(question)
    print(db_schema)

    set_logging_label(logging=LOGGING, logger=logger, label="##### Starting Text-to-SQL")
    set_logging_label(logging=LOGGING, logger=logger, label=f"### Database schema: {db_schema}")
    set_logging_label(logging=LOGGING, logger=logger, label=f"### Question: {question}")

    state['question'] = question
    state['db_schema'] = db_schema

    state = t2s_start_process(state)

    return state


def sql_audit(search_text: str, db_schema: str, number_results: int=5):

    if env['logger']:
        set_logging_label(logging=LOGGING, logger=logger, label="##### Retrieving SQL Statements from VectorDB")

    result = text_to_sql_audit(search_text=search_text, db_schema=db_schema, number_results=number_results)

    return result


def teach_sql(question: str, sql_statement: str, db_schema: str):

    if env['logger']:
        set_logging_label(logging=LOGGING, logger=logger, label="##### Teaching VectorDB with Question/SQL Statement")

    learn_sql(question, sql_statement, db_schema)


def _register_text_to_sql(the_mcp_server: ExasolMCPServer) -> None:
    the_mcp_server.tool(
        text_to_sql,
        description=(
            "The tool translates human questions / natural language questions into "
            "SQL statements and executes it against the database. "
            "ALWAYS use this tool for translation of natural language questions into SQL. "
            "The tool always retrieves the metadata of the requested schema on its own. "
            "Do not use other tools!"
        ),
    )

def _register_text_to_sql_audit(the_mcp_server: ExasolMCPServer) -> None:
    the_mcp_server.tool(
        sql_audit,
        description=(
            "The tool returns SQL queries and the corresponding questions for the requested "
            "database schema. You can search with phrases in the SQL history. Results are "
            "returned based semantic search and the distance to the search term. "
        ),
    )

def _register_teach_sql(the_mcp_server: ExasolMCPServer) -> None:
    the_mcp_server.tool(
        teach_sql,
        description=(
            "The tool stores a combination of a natural language question and its corresponding "
            "SQL statement into a VectorDB. It does not execute a query or answer an question."
        ),
    )

def main():


    ##
    ## Startup
    ##

    try:

        vectordb_client = chromadb.PersistentClient(path=env['vectordb_persistent_storage'])
        vectordb_client.get_or_create_collection(name="Questions_SQL_History")

    except Exception as e:
        print(f"VectorDB - Startup - Check: {e}")
        exit()


    ## Initiate the official Exasol MCP Server and register additional tools

    server = mcp_server()

    _register_text_to_sql(server)
    _register_text_to_sql_audit(server)
    _register_teach_sql(server)


   ##  Finally, run the server

    server.run(transport='http', host='localhost', port=9000)


if __name__ == "__main__":

    main()
