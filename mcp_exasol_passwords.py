###########################################################
## Create encrypted password for database authentication ##
##-------------------------------------------------------##
## DB - 2025-04-26: V0.1 - Initial version               ##
###########################################################

import os
import re
import sys

from cryptography.fernet import Fernet
from dotenv import load_dotenv


##################
## Get the user ##
##################

home_dir = os.path.expanduser("~")

####################################################
## Insert or Update SECRET KEY in '.env' variable ##
####################################################

def update_env_variable(file_path: str, key: str, value: str) -> None:

    updated = False
    lines = []

    # Read existing lines if the file exists

    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            for line in f:
                if line.strip().startswith(f"{key}="):
                    lines.append(f"{key}={value}\n")
                    updated = True
                else:
                    lines.append(line)

    # If the variable wasn't found, add it at the end

    if not updated:
        lines.append(f"{key}={value}\n")

    # Write the updated lines back to the file

    with open(file_path, 'w') as f:
        f.writelines(lines)

    # This file is critical, allow access only for user

    os.chmod(path=file_path, mode=0o600)

    print(f"{'Updated' if updated else 'Added'} {key}={value} to {file_path}")


#############################
## Creating the secret key ##
#############################

def create_secret_key() -> str:

    try:
        secret_key = Fernet.generate_key()
        secret_key = re.search("b'(.*)'", secret_key).group(1)
        update_env_variable(file_path=f"{home_dir}/.env", key='EXA_MCP_SECRET_KEY', value=secret_key)
    except Exception as e:
        return "ERROR: Could not write secret_key!"
    else:
        print("Success: New secret key written")


###########################################
## Retrieving the SECRET KEY if existing ##
###########################################

load_dotenv()
SECRET_KEY = os.getenv("EXA_MCP_SECRET_KEY")
assert SECRET_KEY
FERNET = Fernet(SECRET_KEY)


##########################
## Password maintenance ##
##########################

if  len(sys.argv) > 1 and sys.argv[1] == "--decrypt":

    ## Decrypt the password -  potentially unsafe!

    try:
        stored_user_password = os.getenv("EXA_CRYPTED_PASSWORD")
        decrypted_user_password = FERNET.decrypt(stored_user_password).decode()

    except Exception as e:
        print("Error: Cannot decrypt password, maybe secret key wrong!")
        exit()
    else:
        print(f"Success: Decrypted Database Password is '{decrypted_user_password}'")
elif len(sys.argv) > 1 and sys.argv[1] == "--db_password":

    ## Create a new password. MUST match the password for the Exasol database!
    ## This password will ALWAYS overwrite an existing password. The file only
    ## stores one individual password for one Exasol instance.

    new_password = input("Password on Exasol Database: ")
    new_enc_password = FERNET.encrypt(new_password.encode()).decode()

    try:
        update_env_variable(file_path=f"{home_dir}/.env", key='EXA_CRYPTED_PASSWORD', value=new_enc_password)

    except Exception as e:
        print("Error: Could not write encrypted database password!")
        exit()
    else:
        print(f"Encrypted Database Password stored")

elif len(sys.argv) > 1 and sys.argv[1] == "--secret_key":

    create_secret_key()

    print("New Secret Key created, you MUST specify your passwords again!")
else:
    print("Usage:")
    print("""
        python3 mcp_exasol_passwords.py --db_password     Specify the user's database password.
                                        --secret_key      Set a new secret for the encryption algorithm.
                                        --decrypt         Decrypt and show the passwords.
        """)