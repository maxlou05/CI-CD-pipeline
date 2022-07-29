# REQUIREMENTS
# For table: pip install azure-data-tables

from typing import Any, Dict, List, Optional
from azure.data.tables import TableServiceClient, TableClient
import sys
from azure.identity import DefaultAzureCredential
import os
from dotenv import load_dotenv


def parse_file(path):
    out = {}

    with open(path, 'r') as file:
        for line in file:
            # Split into two parts
            key_value = line.split(" = ")

            # Get rid of newline characters
            key_value[0] = key_value[0].replace("\n", "")
            key_value[1] = key_value[1].replace("\n", "")
            
            # Strip the extra quatations
            if(key_value[0][0] == '"' and key_value[0][-1] == '"'):
                out[key_value[0]] = key_value[1][1:-1]
            if(key_value[1][0] == '"' and key_value[1][-1] == '"'):
                out[key_value[0]] = key_value[1][1:-1]
    
    out["PartitionKey"] = "pkey"
    try:
        out["RowKey"] = out["prefix"]
    except:
        raise Exception("Please provide a key named \"prefix\" with a unique value")
    
    return out


def connect_to_db(conn_str:str):
    return TableServiceClient.from_connection_string(conn_str)


def connect_to_table(client:TableServiceClient, table_name:str):
    return client.create_table_if_not_exists(table_name)


def upsert_entry(table:TableClient, entry:Dict[str, Any]):
    table.upsert_entity(entry)


def delete_entry(table:TableClient, id:str):
    table.delete_entity("pkey", id)


def get_entry(table:TableClient, id:str):
    return table.get_entity("pkey", id)


def query(table:TableClient, query:Optional[str]=None, fields:Optional[List[str]]=None):
    # query_filter = None means return all items
    # select = None means return all columns
    # fields is a list of strings, which are the requested fields
    return table.query_entities(query_filter=query, select=fields)


def publish(text_path:str, connection_string:str, table_name:str):
    entry = parse_file(text_path)
    database = connect_to_db(connection_string)
    table = connect_to_table(database, table_name)
    upsert_entry(table, entry)


def run():
    try:
        text_path = sys.argv[1]
        connection_string = sys.argv[2]
        table_name = sys.argv[3]
    except:
        try:
            load_dotenv()
            text_path = os.environ["FILE_PATH"]
            connection_string = os.environ["CONNECTION_STRING"]
            table_name = os.environ["TABLE_NAME"]
        except:
            pass
        raise Exception("Use case: python table_api.py <path to text file> <connection string> <table name>, or provide environment variables or .env file with FILE_PATH, CONNECTION_STRING, and TABLE_NAME")
    
    publish(text_path, connection_string, table_name)



# MAIN
if(__name__ == "__main__"):
    run()
