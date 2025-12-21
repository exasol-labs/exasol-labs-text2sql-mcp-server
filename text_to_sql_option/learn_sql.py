

import chromadb
import time

from datetime import datetime

from text_to_sql_option.utilities.helpers import get_environment

from text_to_sql_option.intro.intro import (
    env,
    logger,
    LOGGING,
    LOGGING_MODE
)

from text_to_sql_option.utilities.helpers import elapsed_time


def learn_sql(question: str, sql_statement: str, db_schema: str) -> list:

    #env = get_environment()

    if LOGGING == 'True' and LOGGING_MODE == 'debug':
        logger.debug("STEP: Storing pre-define combination of Question and SQL into VectorDB.")

    vectordb_client = chromadb.PersistentClient(path=env['vectordb_persistent_storage'])
    sql_collection = vectordb_client.get_or_create_collection(name="Questions_SQL_History")

    ## Check, if query exists in VectorDB

    start_time_chroma = time.time()

    new_idx = sql_collection.count() + 1
    sql_collection.add(
        documents=[ question ],
        metadatas=[{"sql": sql_statement,
                    "execution_date": str(datetime.now()),
                    "db_schema": db_schema,
                    "user": 'system',
                    "origin": "learn_sql"}],
        ids=[f"{new_idx}"]
    )
    if LOGGING == 'True' and LOGGING_MODE == 'debug':
        logger.debug("STEP: Vector-DB-SQL[Learn SQL] with Question/SQL written")


    elapsed_time(logging=LOGGING, logger=logger, start_time=start_time_chroma, label="Elapsed Time on VectorDB")

    return [ "Question / SQ Statement combination stored!" ]

