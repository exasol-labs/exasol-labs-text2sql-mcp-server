##############################################################
## Exasol MCP server with Text-to-SQL query option          ##
## Module: SQL AUDIT / SEARCH                               ##
##----------------------------------------------------------##
## Version 1.0.0 DirkB@Exasol : Initial version             ##
##############################################################

import chromadb
import datetime
import sys
import time

from pydantic import BaseModel, Field

from text_to_sql_option.utilities.helpers import get_environment


##
## Add-On: Retrieve the past SQL Statements stored by the user for reference.
##

class SqlHistory(BaseModel):
    sql_history: str = Field(
        description="The SQL history set converted into a nice and shiny table in MARKDOWN syntax."
    )


def text_to_sql_audit(search_text: str, db_schema: str, number_results: int) -> list:

    env = get_environment()
    print(env['vectordb_persistent_storage'])
    result = []
    try:

        search_text = "*" # f"*{search_text}*"
        vectordb_client = chromadb.PersistentClient(path=env['vectordb_persistent_storage'])
        collection = vectordb_client.get_collection(name='SQL_Audit')
        result = collection.query(query_texts=[search_text],
                               n_results=number_results,
                               where= {'db_schema': db_schema },

                               include=["documents", "metadatas"])

    except Exception as e:
        print(f"ChromaDB - Error: {e}", file=sys.stderr)

    ## ChromaDB cannot sort like 'ORDER BY'

    print(result)

    combined = list(zip(
        result['ids'][0],
        result['documents'][0],
        result['metadatas'][0],
    ))
    sorted_combined = sorted(combined, key=lambda x: datetime.datetime.fromisoformat(x[2]['execution_date']), reverse=True)

    result['ids'][0], result['documents'][0], result['metadatas'][0] = map(list, zip(*sorted_combined))

    return sorted_combined