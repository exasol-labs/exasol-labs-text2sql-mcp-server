import importlib.resources

def load_prompt(db_schema: str, schema: str) -> str:

    """ Load the Exasol prompt for text to sql transformation."""

    prompt = importlib.resources.read_text("exa_prompt", "prompt.txt")

    return prompt.format(db_schema=db_schema, schema=schema)


