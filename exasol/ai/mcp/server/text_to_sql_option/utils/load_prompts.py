#################################################################################
## Load the important prompts for translation and rendering from external file ##
##-----------------------------------------------------------------------------##
## You can modify the prompt to your needs with touching the code              ##
#################################################################################

import importlib.resources

def load_translation_prompt(db_schema: str, schema: str) -> str:

    """ Load the Exasol prompt for text to sql transformation."""

    prompt = importlib.resources.read_text("exasol.ai.mcp.server.text_to_sql_option.resources", "sql_translation_prompt.txt")

    return prompt.format(db_schema=db_schema, schema=schema)


def load_render_prompt(db_schema: str) -> str:
    """ Load the Exasol prompt for text to sql transformation."""

    prompt = importlib.resources.read_text("exasol.ai.mcp.server.text_to_sql_option.resources", "result_rendering_prompt.txt")

    return prompt.format(db_schema=db_schema)