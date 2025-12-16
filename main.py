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
## The "underlying" Exasol MCP Server
##

from exasol.ai.mcp.server import  mcp_server





def main():
    print("Hello from exasol-mcp-server-governed-sql!")

    server = mcp_server()


if __name__ == "__main__":


    main()
