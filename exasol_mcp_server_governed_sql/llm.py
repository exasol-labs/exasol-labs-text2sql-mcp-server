####################################
## Infer the large Language Model ##
####################################

## DO NOT SEND TELEMETRY TO POSTHOG !!! ##

import os
os.environ["LANGCHAIN_TELEMETRY"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

def invoke_llm(base: str, api: str, model: str, temperature: float, prompt: str, query: str, output: BaseModel):

    llm = ChatOpenAI(model_name=model,
                         temperature=temperature,
                         openai_api_base=base,
                         openai_api_key=api)

    question = query

    t2s_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", prompt),
            ("user", "Question: {question}"),
        ]
    )
    structured_llm = llm.with_structured_output(output)
    process = t2s_prompt | structured_llm

    result = process.invoke({"question": question})

    return result