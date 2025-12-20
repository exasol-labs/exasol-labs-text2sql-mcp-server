########################################################################################################################
## Exasol MCP-Server with GovernedSQL (Text-to-SQL) option                                                            ##
##--------------------------------------------------------------------------------------------------------------------##
## This MCP Server is currently in experimental state and being hosted on Exasol-Labs (http://github.com/exasol-labs) ##
## under a pure "Love it or Leave it" rule - No liability that it always produces 100% correct SQL statements         ##
##--------------------------------------------------------------------------------------------------------------------##
## Version 1.2.1                                                                                                      ##
## 2025-12-23 Dirk Beerbohm: Re-Designed to use the new HookUp functionality of the MCP Server                        ##
##                                                                                                                    ##
## Version 1.0.0                                                                                                      ##
## 2025-10-16 Dirk Beerbohm: Initial public release; share same code base as the official MCP-Server                  ##
########################################################################################################################


##
## Standard Python packages
##

import chromadb
from dotenv import load_dotenv
from pydantic import Field
from typing import (
    Annotated,
)

##
## The "underlying" Exasol MCP Server
#######

from exasol.ai.mcp.server import mcp_server
from exasol.ai.mcp.server.mcp_server import ExasolMCPServer

##
## Thext-to-SQL (GovernedSQL) packages
##

from text_to_sql_option.utilities.helpers import set_logging_label
from text_to_sql_option.sql_history import text_to_sql_history
from text_to_sql_option.text_to_sql import t2s_start_process
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

#def t2s_to_sql_history(self,
#                        search_text: Annotated[str, Field(description="Search Text in question metadata field'", default="*")],
#                        db_schema: Annotated[str, Field(description="Name of Database Schema", default="*")],
#                        number_results: Annotated[int, Field(description="Number of records returned", default=5)],
#                        ):

def sql_audit(search_text: str, db_schema: str, number_results: int=5):

    print(search_text)
    print(db_schema)
    print(number_results)


    result = text_to_sql_history(search_text=search_text, db_schema=db_schema, number_results=number_results)

    return result


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

def _register_text_to_sql_history(the_mcp_server: ExasolMCPServer) -> None:
    the_mcp_server.tool(
        sql_audit,
        description=(
            "The tool returns SQL queries and the corresponding questions for the requested "
            "database schema. You can search with phrases in the SQL history. Results are "
            "returned based semantic search and the distance to the search term. "
        ),
    )

def main():
    set_logging_label(logging=LOGGING, logger=logger, label="##### Starting Text-to-SQL (Main)")

    ## Load the environment

    load_dotenv()

    ##
    ## Very first start, ensure that VectorDB exists
    ##

    vectordb_client = chromadb.PersistentClient(path=env['vectordb_persistent_storage'])
    sql_collection = vectordb_client.get_or_create_collection(name="Questions_SQL_History")



    ## Initiate the official Exasol MCP Server

    server = mcp_server()

    _register_text_to_sql(server)
    _register_text_to_sql_history(server)


   ##  Finally, run the server

    server.run(transport='http', host='localhost', port=9000)


if __name__ == "__main__":

    main()
