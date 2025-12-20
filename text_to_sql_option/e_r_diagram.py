##############################################################
## Exasol MCP server with Text-to-SQL query option          ##
## Module: E-R-Diagram / Schema Description                 ##
##----------------------------------------------------------##
## Version 1.0.0 DirkB@Exasol : Initial version             ##
##############################################################


import time

from pydantic import BaseModel, Field
from typing import Annotated

from text_to_sql_option.intro.intro import (
    env,
    logger,
    LOGGING
)
from text_to_sql_option.utilities.helpers import elapsed_time
from text_to_sql_option.utilities import t2s_database_schema
from text_to_sql_option.utilities import invoke_llm


class ERGraph(BaseModel):
    e_r_graph_in_mermaid: str = Field(
        description="The database schewma as a Mermaid graph."
    )

def generate_e_r_diagram(db_schema: Annotated[str, Field(description="Name of Database Schema")]) -> str:

    schema = t2s_database_schema(db_schema=db_schema)

    system_prompt = """
                        You are a helpful assistant with knowledge for graphs base don the Mermaid Syntax.
                        - Specify the secondary_nodes only with table name, omit schema name.
                        - In a node only show column name and data type, but no scake or precision.
                    
                     """
    system_prompt_length = len(system_prompt)
    question = f"""
    
    For the following schema create a Entity-Relationship diagram in Mermaid syntax and display the graph:
    
    {schema}
    """

    start_time_render = time.time()
    result = invoke_llm(base=env["llm_server_url"],
                        api=env["llm_server_api_token"],
                        model=env["llm_server_model_check"],
                        temperature=0.1,
                        prompt=system_prompt,
                        query=question,
                        output=ERGraph)

    result = str(result.e_r_graph_in_mermaid)

    elapsed_time(logging=LOGGING, logger=logger, start_time=start_time_render,
                 label=f"Time needed for rendering answer (Prompt-Length: {system_prompt_length})")

    return result