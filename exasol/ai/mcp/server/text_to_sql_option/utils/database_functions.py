
import pyexasol
import sys

from exasol.ai.mcp.server.text_to_sql_option.utils.helpers import get_environment

############################################################
## Retrieve the metadata for the required database schema ##
#############################################################

def t2s_database_schema(db_schema: str) -> str:

    env = get_environment()

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