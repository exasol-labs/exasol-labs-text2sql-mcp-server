#######################################
## Database / SQL specific functions ##
#######################################

import pyexasol
import time

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError

from exasol.ai.mcp.server.text_to_sql_option.intro.intro import (
    env,
    logger,
    LOGGING,
)
from exasol.ai.mcp.server.text_to_sql_option.utilities.helpers import elapsed_time


############################################################
## Retrieve the metadata for the required database schema ##
#############################################################

def t2s_database_schema(db_schema: str) -> str:
    start_time_exa_conn = time.time()
    with pyexasol.connect(dsn=env['dsn'], user=env['db_user'], password=env['db_password'], schema='SYS') as c:
        elapsed_time(logging=LOGGING, logger=logger, start_time=start_time_exa_conn, label="Elapsed Time on Exasol-DB - Create Connection")
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

        start_time_exa_query = time.time()
        stmt = c.execute(metadata_query)
        elapsed_time(logging=LOGGING, logger=logger, start_time=start_time_exa_query, label="Elapsed Time on Exasol-DB - Retrieve Database Schema")

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

    return schema_metadata

#######################################################
## Is the execution of the SQL statement permissible ##
##---------------------------------------------------##
## Currently, only 'SELECT' statements are permitted ##
#######################################################

def get_sql_query_type(query: str) -> bool:
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