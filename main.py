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
from functools import partial

from exasol.ai.mcp.server.db_connection import DbConnection
from exasol.ai.mcp.server.server_settings import McpServerSettings
from fastmcp.server.middleware.logging import LoggingMiddleware

VERSION = '1.2.1'

##
## Standard Python packages
##

import chromadb
import click
import logging
#from dotenv import load_dotenv


##
## The "underlying" Exasol MCP Server
##

from exasol.ai.mcp.server import mcp_server
from exasol.ai.mcp.server.mcp_server import ExasolMCPServer

from exasol.ai.mcp.server.connection_factory import get_oidc_user

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


##############################
## Entry-Point to the tools ##
##############################


class Text2SQL:

    def __init__(self, connection: DbConnection) -> None:
        self.connection = connection
        self.state: GraphState = GraphState()

    def text_to_sql(self ,question: str, db_schema: str):

        #if not self.config.enable_text_to_sql:
        #    raise RuntimeError("Text-to-SQL option is disabled")

  #      print("TK:"+str(self.connection.execute_query("SELECT 1").fetchall()))

        set_logging_label(logging=LOGGING, logger=logger, label="##### Starting Text-to-SQL")
        set_logging_label(logging=LOGGING, logger=logger, label=f"### Database schema: {db_schema}")
        set_logging_label(logging=LOGGING, logger=logger, label=f"### Question: {question}")

        self.state['question'] = question
        self.state['db_schema'] = db_schema
        self.state['connection'] = self.connection

        state = t2s_start_process(self.state)

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


#####################################################################
## Register tool sof this module in addition to the original tools ##
#####################################################################

def _register_text_to_sql(the_mcp_server: ExasolMCPServer) -> None:
    text_to_sql_with_con = Text2SQL(the_mcp_server.connection).text_to_sql
    the_mcp_server.tool(
        text_to_sql_with_con,
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


########################################################
## Test for VectorDB, if not exists, create a new one ##
########################################################

def check_vectordb():

    try:

        vectordb_client = chromadb.PersistentClient(path=env['vectordb_persistent_storage'])
        vectordb_client.get_or_create_collection(name="SQL_Audit")

    except Exception as e:
        print(f"VectorDB - Startup - Check: {e}")
        exit()
    else:
        print("VectorDB - Startup - Check: OK")


##################################################
## main_http(): Standalone MCP Server over HTTP ##
##################################################

@click.command()
@click.version_option(VERSION, message="Version: %(version)s")
@click.option("--transport", default="http", help="MCP Transport (default: http)")
@click.option("--host", default="0.0.0.0", help="Host address (default: 0.0.0.0)")
@click.option("--port", default=8000, type=click.IntRange(min=1), help="Port number (default: 8000)")

def main_http(transport, host, port) -> None:
    """
       Main entry point that creates and runs the MCP server centralized.
    """

    check_vectordb()

    ## Initiate the official Exasol MCP Server and register additional tools

    server = mcp_server()
    #print(server.connection)

#    server.add_middleware(LoggingMiddleware(logger=logging.getLogger()))
    _register_text_to_sql(server)
    _register_text_to_sql_audit(server)
    _register_teach_sql(server)


   ##  Finally, run the server
#    logging.basicConfig(level=logging.DEBUG)
    server.run(transport=transport, host=host, port=port)



####################################
## main():  MCP Server over STDIO ##
####################################

def main():
    """
    Main entry point that creates and runs the MCP server locally.
    """

    check_vectordb()

    server = mcp_server()

    _register_text_to_sql(server)
    _register_text_to_sql_audit(server)
    _register_teach_sql(server)

    server.run()



if __name__ == "__main__":

    main_http()
