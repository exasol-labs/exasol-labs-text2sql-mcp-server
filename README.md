# Exasol MCP Server with Governed SQL option

<p align="center">

<a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/pypi/l/exasol_mcp_server" alt="License">
</a>
<a href="https://pypi.org/project/exasol_mcp_server/">
    <img src="https://img.shields.io/pypi/dm/exasol_mcp_server" alt="Downloads">
</a>
<a href="https://pypi.org/project/exasol_mcp_server/">
    <img src="https://img.shields.io/pypi/pyversions/exasol_mcp_server" alt="Supported Python Versions">
</a>
<a href="https://pypi.org/project/exasol_mcp_server/">
    <img src="https://img.shields.io/pypi/v/exasol_mcp_server" alt="PyPi Package">
</a>
</p>

Provides an LLM access to the Exasol database via MCP tools. Includes tools  
for reading the database metadata and executing data reading queries, and an  
optional tool for (on-premise) translation of natural language into SQL statements  
for the Exasol database.  

__Usually known as Text-to SQL, we call it Governed SQL, as we control every step from  
a natural language question to the database answer.__
  

## Disclaimer

The accuracy of Large Language Models (LLM) depend on the training set used, and on further  
methods like Retrieval Augmented Generation (RAG). Large Language Models can make mistakes and  
may produce faulty or wrong results!  

Check each result produced by the Text-to-SQL (GovernedSQL) option of this experimental MCP-Server!

To mitigate further security related risks this MCP-Server allows Read-Only queries, only.

Nor Exasol as a company, nor the author(s) of the Text-to-SQL option can be held liable for  
damage to any possible kind by using this software. Moreover, the Safe Harbour Statement at the  
end of this README shall remain valid.

__Do NOT use the MCP-Server with the Text-to-SQL option if you do not agree to these conditions!__


This MCP Server is based on the official Exasol MCP Server (https://github.com/exasol/mcp-server) and  
extends its functionality by an on-premise Text-to-SQL process. This server does not change the code  
of the official server, but hooks into it. The full functionality of the original MCP Server is supported.  
Do not install both server, or activate both servers as this will lead into problems.

## Version history

__-Version 1.3.0.3__:

- Updated README.md file

__Version 1.3.0.2__:

- Corrected a bug which prevented "uv tool install" to install successfully.

__Version 1.3.0__: 
- This MCP server does now fully rely on the official Exasol MCP Server by creating an  
  MCP Server object and registering additional tools.
- New tool: teach the MCP Server with a question and the corresponding SQL statement.
- Now using the Connection Factory of the official MCP Server
- Tested for Authentication via OAuth with Keycloak and OpenLDAP.  
  See README-OAuth-Authentication.md for details.
- Recommend Streamable HTTP as standard installation (for Enterprises)
- __IMPORTANT__: This MCP Server offers the very same functionality as the official  
  Exasol MCP Server. Do __not__ install both servers simultaneously or ensure that one
  MCP Server is disabled. Otherwise, you may encounter problems.

__Version 1.2.1__: 
- Architecture Change to use the Hook-Up functionality of the official Exasol MCP-Server  
- Ability to store a predefined question/SQL Statement combination in the underlying  
  VectorDB to better adapt to specific user requirements.
- Environment variable naming changed to adapt better the naming convention of the official MCP-Server

__Version 1.0.0__: 
- Initial Version.
  

## Introduction

Governed SQL (Text-to-SQL) is nothing unknown or rarely technology anymore. However, most of the  
solutions rely on  publicly served Large Langauge Models (LLM) by companies like OpenAI, or Anthropic.  
This contradicts the principle of *Data  Sovereignty* where your keep full control of your data or metadata. Moving  
the transformation of natural language into SQL is not enough, as widely used AI Desktops, e.g.  
Anthropic Claude utilize a public served LLM to render the results. To fully protect your data you  
have to use an AI Desktop application which allows to use a self-hosted Large Language model.

The MCP sever with the text-to-sql option can be used with commercially AI Desktops like Claude or  
open source AI applications like Open-WebUI like Jan.ai.

__This README will cover a centralized deployment via streamable http, only!__

Refer to the official Exasol MCP Server documentation for other installation options.


## Features

- Checks the relevance of a natural language question for a requested database schema
- Checks the VectorDB for similar questions and give hints if feasible
- Transforms the question into an SQL statement
- Checks if the SQL statement is allowed; currently, we only allow read-only statements.
- Executes the SQL statement
- Checks if SQL statement is valid
  - If a result set is returned, the question, the SQL statement, and some metadata is stored in a VectorDB
- If required, rewrites the question
- Generates a result
  

### Workflow of the Governed SQL Agent

This is the workflow of the Governed SQL agent, coded with the langgraph library.

<img src="exasol_mcp_server_governed_sql/images/langgraph_workflow.png" width="640"  alt=""/>


## Prerequisites

- [Python](https://www.python.org/) >= 3.12.
- MCP Client application, e.g. [Claude Desktop](https://claude.ai/download), or [Open-WebUI](https://github.com/open-webui/open-webui)

* A dedicated Large Language Model (LLM) server with a LLM of your choice loaded, e.g.:  
  
  * LM-Studio (https://lmstudio.ai) or  
  * Ollama (https://ollama.com).  
  
Preferable with GPU support. For accessing the servers the OpenAI API is used. You can use  
any other LLM server application which supports the OpenAI API. 
  

## Installation

### Remark

Do not configure the Exasol supported MCP server and this MCP server at the same time within the  
AI tool of your choice. This MCP server will use the same version numbers as the officially  
supported Exasol MCP-Server, plus a four digit to show different patches or add-ons.  
Equal version numbers indicate the same functionality, plus the Governed-SQL option.

Ensure the `uv` package is installed. If uncertain call
```bash
uv --version
```
To install `uv`, please follow [the instructions](https://docs.astral.sh/uv/getting-started/installation/)
in the `uv` official documentation.
  
To install the MCP-Server execute the following command:

    uv tool install exasol-mcp-server-governed-sql@latest

You can start the server like:

    exasol-mcp-server-goverfned-sql-http -- host="0.0.0.0" --port=<desired port number>


Optionally, you can specify a dedicated IP address of your server the MCP-Server should listen on.  
Before starting, create a ".env" file (if not existing already) and add the environment variables  
as shon below. This will start the MCP-Server without authentication. For authentication, please  
refer to the README-OAuth-Authentication.md file.

### Open-WebUI as end user client

Open-WebUI can be deployed in various options. Please refer to the documentation and install  
with you preferred deployment type. 
Refer to README-OAuth-Authentication for detailed configuration   
steps of Open-WebUI for an OAuth Authentication deployment.

## Configuration settings

The configuration is split in two parts, one for the Exasol supported MCP-Server, and one  
for the text-to-sql option.  
  

### Original Settings for the Exasol MCP Server

Most importantly, the server configuration specifies if reading the data using SQL  
queries is enabled. Note that reading is disabled by default. To enable the data  
reading, the `enable_read_query` property must be set to true (see the
configuration settings json below).  

The server configuration settings can also be used to enable/disable or filter the  
listing of a particular type of database objects. Similar settings are defined for  
the following object types:
```
schemas,
tables,
views,
functions,
scripts
```
The settings include the following properties:
- `enable`: a boolean flag that enables or disables the listing.
- `like_pattern`: filters the output by applying the specified SQL LIKE condition to
the object name.
- `regexp_pattern`: filters the output by matching the object name with the specified
regular expression.

The settings can be specified using another environment variable - `EXA_MCP_SETTINGS`.  
They should be written in the json format. The json text can be set directly as a  
value of the environment variable, for example  
```json
{"EXA_MCP_SETTINGS": "{\"schemas\": {\"like_pattern\": \"my_schemas\"}"}
```
Note that double quotes in the json text must be escaped, otherwise the environment  
variable value will be interpreted, not as a text, but as a part of the outer json.  

Alternatively, the settings can be written in a json file. In this case, the  
`EXA_MCP_SETTINGS` should contain the path to this file, e.g.
```json
{"EXA_MCP_SETTINGS": "path_to_settings.json"}
```

The following json shows the default configuration settings.
```json
{
  "schemas": {
    "enable": true,
    "like_pattern": "",
    "regexp_pattern": ""
  },
  "tables": {
    "enable": true,
    "like_pattern": "",
    "regexp_pattern": ""
  },
  "views": {
    "enable": false,
    "like_pattern": "",
    "regexp_pattern": ""
  },
  "functions": {
    "enable": true,
    "like_pattern": "",
    "regexp_pattern": ""
  },
  "scripts": {
    "enable": true,
    "like_pattern": "",
    "regexp_pattern": ""
  },
  "enable_read_query": false
}
```

### Settings for the Governed SQL option

The specific settings for the Text-to-SQL option are to be set in a ".env" file in your  
home directory file as follows:  

```
EXA_DSN=<exasol-database-dsn>
EXA_USER=<technical-db-user>
EXA_PASSWORD=<db-password>>
EXA_MCP_SETTINGS=<path-to-mcp-server-settings>
EXA_MCP_LLM_SERVER_URL=<URL for LLM server>
EXA_MCP_LLM_SERVER_API_KEY=not-needed
EXA_MCP_LLM_TRANSFORMATION=<LLM to be used>
EXA_MCP_LLM_RENDERING=<LLM to be used>
EXA_MCP_LLM_TEMPERATURE_RELEVANCE=0.0
EXA_MCP_LLM_TEMPERATURE_TRANSLATION=0.0
EXA_MCP_LLM_TEMPERATURE_QUERY_REWRITE=0.4
EXA_MCP_LLM_TEMPERATURE_RENDERING=0.0
EXA_MCP_LLM_TEMPERATURE_INFO=0.7
EXA_MCP_VECTORDB_FILE=<path-to-vector-database-location>>
EXA_MCP_VECTORDB_SIMILARITY_DISTANCE=0.3
EXA_MCP_LOGGER=True
EXA_MCP_LOGGER_MODE=(INFO|DEBUG)
EXA_MCP_LOGGER_FILE=<path-to-log-file>>
```
The meaning of these settings should be self-explanatory. Changing the so-called temperatures for the  
relevance check, translation and rendering should be changed if you know what the consequences are.  
The temperatures for the info messages and the query rewrite can be lowered or increased to your likings,  
however, be cautious with the setting for the query rewrite.  Refer to the Exasol MCP-Server for the settings  
EXA_MCP_SETTINGS environment variable.

In general, the temperature defines, how strict the LLM will generate answers. The higher the temperature,   
the more variation you will see.

__These settings allow the MCP Server to start without authentication requirements. Refer to the file  
README-OAuth-Authentication.md for the required steps to enable authentication.__

  
  
### Large Language Models to consider

For the transformation process, you can select any LLM which is known to code (specifically for SQL)  
with good quality. We have made some good experience with the

- qwen/qwn-coder-30b, quantized down to 4-bit, approx. 18GB of size.

Large Language Model for both transforming into SQL statements and rendering result sets.  
In case you decide to use an AI Desktop where you can configure the LLM to be utilized,  
you need to check, if the LLM is trained for tool usage. The more parameters the LLM features  
the higher is the performance requirement for a timely answer. An LLM with too many parameters might  
consume quite some time. Having a dedicated LLM server (on premise) is definitely a plus.

Also, your LLM of choice needs to be trained for tool usage.
  


  
### Please consider!

Large Language Models do not act like a human brain, basically they predict the next possible  
word or token, based on a set of parameters (do not mix it with connections between neurons of the neural   
network, a.k.a. parameters), e.g. temperature. You have to instruct them precisely about  
the task they have to solve. For many AI Desktop applications this is even valid for displaying  
the result set the Text-to-SQL option has created. 

For example, with __Claude Desktop__ or __Open-WebUI__ the following text helped to receive pure  
results without any commentary, or other additional information. Consider it purely optional:  

```
Use only answer from tool to display result. Do not comment!
```

## Examples

Here are a few examples how Text-to-SQL transformed a natural language question into an SQL Statement.  
You need to instruct the LLM precisely with your question and the desired outcome. You have to include  
the name of the database schema you want to use. As of now, Text-to-SQL does not search for an adequate  
database schema when it is missing in the question, or misspelled.

### Simple count

- Show me the number of rows in the SALES_POSITIONS table of the RETAIL database schema, do not comment.


```
SELECT 
   COUNT(*) AS RECORD_COUNT 
FROM 
   RETAIL.SALES_POSITIONS
```
### Date Extractions
- Top three products with regard to revenue for the area of 'Hessen' for the 22nd week of day 2023 in the
  RETAIL database schema, include units sold?

```
SELECT 
   a.DESCRIPTION AS PRODUCT_DESCRIPTION, 
   SUM(sp.AMOUNT) AS UNITS_SOLD, 
   SUM(sp.PRICE) AS REVENUE 
FROM 
   RETAIL.SALES s JOIN RETAIL.SALES_POSITIONS sp ON s.SALES_ID = sp.SALES_ID 
                  JOIN RETAIL.ARTICLE a ON sp.ARTICLE_ID = a.ARTICLE_ID 
                  JOIN RETAIL.MARKETS m ON s.MARKET_ID = m.MARKET_ID 
WHERE 
   m.AREA = 'Hessen' AND 
   YEAR(s.SALES_DATE) = 2023 AND 
   to_char(s.SALES_DATE, 'uW') = '22' 
GROUP BY 
   a.DESCRIPTION 
ORDER BY 
   REVENUE DESC 
LIMIT 3
```

### Higher degree of GROUP BY attributes

- Show the top 5 routes with the most delayed flights between departure city and destination city,  
  include accrued minutes of delay in the list; use the FLIGHTS database schema

```
SELECT 
   F.ORIGIN_CITY_NAME AS ORIGIN_CITY_NAME, 
   F.DEST_CITY_NAME AS DEST_CITY_NAME, 
   COUNT(F.DEP_DELAY) AS DELAY_COUNT, 
   SUM(F.DEP_DELAY) AS TOTAL_DELAY_MINUTES 
FROM 
   FLIGHTS.FLIGHTS F 
WHERE 
   F.DEP_DELAY > 0 
GROUP BY 
   F.ORIGIN_CITY_NAME, F.DEST_CITY_NAME 
ORDER BY 
   DELAY_COUNT DESC LIMIT 5
```

The first query just returns the number of rows. The second and third example return  
a table in Markdown syntax, which is rendered in the client accordingly. As the visual  
result differs between different AI Desktops they are not shown here. In order to retrieve  
consistent visual results you need to set the so-called temperature to '0.0'. For all  
process steps within Text-to-SQL where an LLM is involved the temperature is '0.0'. However,  
when using AI Desktops with publicly used LLMs the final rendering may look differently  
with every single run - this is an indication of a temperature greater than '0.0'.


## Auditing

Auditing can happen in two ways. Search in the log file specified in the ".env" file or by querying  
the internal Vector database from the AI Desktop application with the "SQL History" tool of the MCP-Server.

As an example, the following request:  

```Show me SQL statements about busy routes in Texas include the question and date```

shows the following SQL statement

![img.png](exasol_mcp_server_governed_sql/images/sql_history.png)

Please beware, the quality of the search results depend on the selected LLM. If you are using a different 
LLM you might have a different experience.


## License

This project is licensed under the MIT License - see the LICENSE file for details.

### Safe Harbor Statement: Exasol MCP Server & AI Solutions

Exasol’s AI solutions (including MCP Server) are designed to enable intelligent,
autonomous, and highly performant access to data through AI and LLM-powered agents.
While these technologies unlock powerful new capabilities, they also introduce
potentially significant risks.

By granting AI agents access to your database, you acknowledge that the behavior of
large language models (LLMs) and autonomous agents cannot be fully predicted or
controlled. These systems may exhibit unintended or unsafe behavior—including but not
limited to hallucinations, susceptibility to adversarial prompts, and the execution of
unforeseen actions. Such behavior may result in data leakage, unauthorized data
generation, or even data modification or deletion.

Exasol provides the tools to build AI-native workflows; however, you, as the implementer
and system owner, assume full responsibility for managing these solutions within your
environment. This includes establishing appropriate governance, authorization controls,
sandboxing mechanisms, and operational guardrails to mitigate risks to your organization,
your customers, and their data.
