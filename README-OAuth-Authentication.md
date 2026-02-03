# OAuth Documentation for Exasol MCP Server with KeyCloak and OpenLDAP

This documentation outlines how to establish QAuth authenctication for the 
Exasol _ExasolMCP Server_ with or without the GovernedSQL option.   
Derive your individual requirements from this template. 

## Why Oauth Authentification?

MCP Servers basically offers two deployment options, a local deployment and a centralized deployment.  
With a local deployment the user tool communicates with the MCP Server via the _stdio_ protocol, requiring  
a locally installed MCP Server. 

For an Enterprise deployment this approach is not feasible. Therefore a centralized MCP Server neeeds to be  
deployed and accordingly secured. The MCP Server requires an authentication against an OAuth identity provider  
to ensure validated access to itsself. 

Detailed information can bee retrieved from the following website:  

    https://modelcontextprotocol.io/docs/tutorials/security/authorization


Be aware that the steps below are the absolute minimum for an OAuth authentication.   
No themes customization or specialities for LDAP or Active Directory are included.   
As we work a one Open-WebUI Server, acting as a client for the MCP-Server, we do not cover  
_Dynamic CLient Registration_.
  

## Requirements

### Software components used

    1. OpenLDAP Server with PHPLDAPAdmin installed, we are using it in a Docker environment
    2. Keycloak as OAuth Identiy provider, we are using it in a Docker environment
    3. Open-WebUI as end user interface
    4. Exasol MCP-Server, here with the GovernedSQL option.


### Organizational

A database role (in Exasol) with all users allowed to use the MCP Server and a  
technical database user, with the following grants (only):  

        CREATE SESSION
        IMPERSONATE TO <database role> ON <technical user>   

The technical user will only connect to the database and switch to the desired user
by impersonation.  
This user shall have no further grants for securtiy reasons!  


## Pre-Requisites

The OpenLDAP User / Active Directory User __must__ be the same as the database username.
As of now, there is no mapping from a   
LDAP  / Active Directory username  to a database username.
If this requirements fails, the MCP Server will fail with authentication errors,   
as the so-called impersonation will fail!


## Notes

This tutorial strictly aligns with Keycloak, OpenLDAP and Open-WebUI for a working
environment. The overall principle should be the same   
for other selected tools, but  Exasol has not tested any other tools than the mentioned ones. 

Certain object names, for example role names or identifiers, have been selected for a
working demo environment. Change this object names   
carefully to your needs. Mixing up
object names may lead to a non-working environment.


## Setting up Installation environment

### Network ports

We are using the following network ports for our installation:  

    8080: Open-WebUI
    9080: Keycloak
    9100: MCP-Server

### OpenLDAP

We use OpenLDAP for the user management. When using Microsoft Active Directory, certain object names
are different with same functionality.  
Consult the AD documentation.

We use the Docker envrionment for OpenLDAP, plus PHPLDAPAdmin for the administration of OpenLDAP.
Follow the installation guidelines for both,   
including a persistance storage for OpenLDAP in case you   deploy OpenLDAP ina containerized environment.

Configure your domain, and an administrator account. For this tutorial we use:  

    dc=exasol,dc=local
    cn=admin,dc=exasol,dc=local. 

Create a group for the desired users:  

    cn=openwebui,dc=exasol,dc=local

Create one or more users inside the "openwebui" group:  

    cn=user1,cn=openwebui,dc=exasol,dc=local
    cn=user2,cn=openwebui,dc=exasol,dc=local

Remember: the "user1", "user2" have to be created in the Exasol database and assigned to a role for impersonation
of the technical user.


### Keycloak

#### Realm

Create your own _Realm_ and activate it. All settings from now on will be stored under the new Realm. 

#### User Federation

Keycloak uses  OpenLDAP to check the validity of a user (authentication) and offers the login procedure when
users want to login into their client,  
here: "Open-WebUI". In Keycloak the _User Federation_ needs to be configured against
an OpenLDAP or Microsoft Active Directory server. Refer to   
the documention for the following fields, as they can vary
depending on your deployment:

    Username LDAP attribute
    RDN LDAP attribute
    UUID LDAP attribute
    User object class
    User LDAP filter

To check the user federation goto "Users" and search for a user from your OpenLDAP/Active Directory. You may see a
red sign when retrieving one or more users,  
it is most likely due to an unverfied email address. Go into the users
profile and check the _Email verified_ switch.


#### Client Scopes

Create a _Client Scope_ and name it _mcp-tools_. You can change the name but must use this name in other locations accordingly, otherwise your
deployment will fail.  
Set the Type do _Default_. In the _Mapper_ tab create entries for the following mappers:  

    - "User Attribute" and map the field _username_ to the "Token Claim Name" of "preferred_username"

    - "Audience" with the name "audience-config" and set the "Included Client Audience" to the URI of the  
      MCP-Server


#### Clients

Create a new client with a unique id, e.g. __openwebui_id__, as we are using Open-WebUI in this tutorial. Add the following URLs on the
first page as follows:

    Valid redirect URIs: http(s)://<Open-WebUI server>:<Port>/oauth/oidc/callback
    Web origins: http(s)://<Open-WebUI server>:<Port>

For the _Capability Config_ check:

    Client Authentication
    Standard Flow
    Direct Access Grants
    Service Account Roles

In the tab _Credentials_ note or re-create the _Client Secret_. You need this information for the configuration of Open-WebUI.


### Open-WebUI

Open-Webui needs to be configured for OAuth based authentication, so it can pass ther neccessary information to the MCP-Server.
It can use defined local  
users, or authenticate against an LDAP, or Active Directory server; you can keep all of them. 
Open-WebUI will still offer these authentication options. However,  
trying to involve the MCP Server will lead to an
error. It is highly advisable to have an administrative user with one of the optional authentication methods.

Initial OAuth configuration will be performed via environment variables:

Make the following environment variables availabe to the Open-WebUI server, depending on your deplyment, e.g.
defining them in the shell before executing  
Open-WebUI or passing them into Docker, in case you are using a dockerized deployment:

    WEBUI_URL=http://<Open-WebUI server>:8080
    ENABLE_OAUTH_PERSISTENT_CONFIG=false
    OPENID_PROVIDER_URL=http://<Keycloak server>:<PORT of Keycloak>/realms/<your realm>/.well-known/openid-configuration
    OPENID_REDIRECT_URI=http://<Open-WebUI server>:<PORT OF Open-WebUI>/oauth/oidc/callback
    OAUTH_PROVIDER_NAME=keycloak
    OAUTH_CLIENT_ID=<client_id>>
    OAUTH_CLIENT_SECRET=<client secret>
    OAUTH_SCOPES=openid
    OAUTH_MERGE_ACCOUNTS_BY_EMAIL=true
    ENABLE_OAUTH_SIGNUP=true
    GLOBAL_LOG_LEVEL=DEBUG

If you have not configured an extern tool - the MCP-Server - in Open-WebUI, do so now. Go to the
__Administration__, __Settings__ and finally to __External Tools__.  
Here select the type __MCP Streamble HHTP__.
Enter the URL of the MCP Server like "http://<your MCP Server>:<PORT>/mcp. For Authentication, select __OAuth__,
__not__ OAuth 2.1, and provide  
a unique ID and Name.

### MCP-Server

We are opting to deploy the MCP-Server as a web service. Without further configuration as outlined in the user 
documentation, the server will start without authentication.  
Every user can use the MCP-Server; this is a security hole. Add the following environment variables in the ".env" file to deploly the MCP-Server with OAuth authentication:

    FASTMCP_SERVER_AUTH=exa.fastmcp.server.auth.auth.RemoteAuthProvider
    EXA_USERNAME_CLAIM=preferred_username
    EXA_AUTH_AUTHORIZATION_SERVERS=http://<keycloak-server-name>:9080/realms/<your realm>
    EXA_AUTH_BASE_URL=http://<mcp-server-name>:9100
    EXA_AUTH_JWKS_URI=http://<keycloak-server-name>:9080/realms/<your realm>protocol/openid-connect/certs


## How to use

1.) Call the Open-WebUI server  
2.) In the login form, press __Continue with Keycloak__ (or similar)  
3.) A new Login-Form appears, login with:

    - Username (as defined in OpenLDAP or Microsoft Active Directory), or
    - Email address

   Enter your password you are using when authenticating against OpewnLDAP or Active Directory.

4.) Select a workspace and ensure that the MCP server is enabled. (Refer to Open-WebUI documentation).
    You can pre-define workspaces. 
    with enabled  
    MCP Server Tool and additional instructions for the LLM.

5.) Enter your question and wait for response from MCP Server.

Happy Exasoling!






