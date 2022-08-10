from azure.data.tables import TableServiceClient, TableClient
import json
from typing import Any, Dict, List, Optional
import sys


DEFAULT_PARTITION_KEY = "pkey"
DEFAULT_TABLE_NAME = "ncyd_configuration_info"


def parse_file(path):
    '''
    Parse a key-value pair text file into a python dictionary ready to be uploaded to the database

    Parameters:
    - path (required): the path to the text file containing key value pairs

    Return:
    a dictionary with the specified key-value pairs by the text file
    '''
    
    out = {}

    with open(path, 'r') as file:
        for line in file:
            # Get rid of newline characters
            line = line.replace("\n", "")

            # Split into two parts
            key_value = line.split("=")

            # Strip leading and trailing whitespace
            key_value[0] = key_value[0].strip()
            key_value[1] = key_value[1].strip()

            # Strip the extra quotations
            if(key_value[0][0] == '"' and key_value[0][-1] == '"'):
                key_value[0] = key_value[0][1:-1]
            if(key_value[1][0] == '"' and key_value[1][-1] == '"'):
                key_value[1] = key_value[1][1:-1]

            out[key_value[0]] = key_value[1]
    
    # Add a partition key if not specified
    if("PartitionKey" not in out.keys()):
        out["PartitionKey"] = DEFAULT_PARTITION_KEY
    
    # Add a row key (required and must be unique)
    if("RowKey" not in out.keys()):
        try:
            # Keep the old key in case querying for that
            out["RowKey"] = out["prefix"]
        except:
            try:
                out["RowKey"] = out["id"]
            except:
                raise Exception("Please provide a key named \"prefix\" or \"id\" with a unique value")
    
    return out


def connect_to_db(conn_str:str):
    '''
    Get a TableServiceClient to do operations on a Cosmos Table API database

    Parameters:
    - conn_str: the connection string to access a Cosmos Table API database

    Return:
    a TableServiceClient which points to the database specified in the connection string
    '''

    return TableServiceClient.from_connection_string(conn_str)


def connect_to_table(db:TableServiceClient, table_name:str):
    '''
    Get a TableClient to do operations on a Cosmos Table API table

    Parameters:
    - db (required): a TableClientService which points to the database in which the table is located
    - table_name (required): the name of the table to access

    Return:
    a TableClient which points to the table specified by table_name
    '''

    return db.create_table_if_not_exists(table_name)


def upsert_entry(table:TableClient, entry:Dict[str, Any]):
    '''
    Upload an entry to the database

    Parameters:
    - table (required): a TableClient which points to the table to be queried
    - entry (required): a dictionary with string keys. Nested objects not supported

    Return: None
    '''

    table.upsert_entity(entry)


def delete_entry(table:TableClient, id:str, partition_key:Optional[str] = None):
    '''
    Delete an entry from the database

    Parameters:
    - table (required): a TableClient which points to the table to be queried
    - id (required): the id of the entry to get
    - partition_key: the partition the entry is in

    Return: None
    '''

    if(partition_key is None):
        table.delete_entity(partition_key=DEFAULT_PARTITION_KEY, row_key=id)
        return
    table.delete_entity(partition_key, id)


def get_entry(table:TableClient, id:str, partition_key:Optional[str] = None):
    '''
    Get a specific entry from the database

    Parameters:
    - table (required): a TableClient which points to the table to be queried
    - id (required): the id of the entry to get
    - partition_key: the partition the entry is in

    Return:
    a dictionary representation of the entry
    '''

    try:
        if(partition_key is None):
            return table.get_entity(partition_key=DEFAULT_PARTITION_KEY, row_key=id)
        return table.get_entity(partition_key=partition_key, row_key=id)
    except:
        return None


def query(table:TableClient, query:Optional[str]=None, fields:Optional[List[str]]=None):
    '''
    Query the database

    Parameters:
    - table (required): a TableClient which points to the table to be queried
    - query: a string to specify the query. None returns all entries in the table
    - fields: a list of which fields should be returned. None returns all fields

    Return:
    an iterable containing dictionary representations of the entries which meet the query requirements

    Formatting a query string:\n
    Only specify required conditions, in the format <field> <operator> <value>\n
    *Note: the value must be within single quotes (ie 'value') if it is a string\n
    Many conditions can be applied in the same query by using <condition1> and/or <condition2>

    Supported operators:
    - equals (=): eq
    - greater than (>): gt
    - greater than or equal to (>=): ge
    - less than (<): lt
    - less than or equal to (<=): le
    - not equals (<>): ne

    Example:
    mystring eq 'welcome' and mynumber gt 10
    '''

    return table.query_entities(query_filter=query, select=fields)


# For internal use
def help():
    help_text = '''
    -----NCYD deployment information automation tool-----

    Use case: python table_api.py <command>

    Available commands:
        - publish <connection string> <table name> <path to text file>
            publish an entry to the database by specifying key-value pairs with a unique "id" key in a text file

        - delete <connection string> <table name> [OPTIONS]
            delete an entry from the database by specifying a unique "id"
            OPTIONS (one is required):
                -i <id> delete the entry with specified id
                -f <path to text file> for more advanced searching, specify the partition key and row key of the entry to be deleted

        - query <connection string> [OPTIONS]...
            query the database using a query string and filters the results for only relevant fields
            OPTIONS:
                -q <query string> if not provided, returns all entries (see API documentation for formatting)
                -f <fields> ... if not provided, returns all available fields
            *ex: query <connection string> <table name>
            *ex: query <connection string> <table name> -q query_string -f field1 field2 field3)

        - get <connection string> <table name> [OPTIONS]
            returns a specific entry within the database by specifying a unique "id"
            OPTIONS (one is required):
                -i <id> get the entry with specified id
                -f <path to text file> for more advanced searching, specify the partition key and row key of the entry to get
    '''
    return help_text


def cli_publish(connection_string:str, text_path:str):
    entry = parse_file(text_path)
    database = connect_to_db(connection_string)
    table = connect_to_table(database, DEFAULT_TABLE_NAME)
    upsert_entry(table, entry)
    print("Successfully published entry with PartitionKey '{}' and RowKey '{}' to database".format(entry["PartitionKey"], entry["RowKey"]))


def cli_delete(connection_string:str, text_path:Optional[str]=None, id:Optional[str]=None):
    database = connect_to_db(connection_string)
    table = connect_to_table(database, DEFAULT_TABLE_NAME)
    if(text_path is not None):
        keys = parse_file(text_path)
        delete_entry(table, keys["RowKey"], keys["PartitionKey"])
        print("Successfully deleted entry with PartitionKey '{}' and RowKey '{}'".format(keys["PartitionKey"], keys["RowKey"]))
    else:
        delete_entry(table, id)
        print("Successfully deleted entry with PartitionKey '{}' and RowKey '{}'".format(DEFAULT_PARTITION_KEY, id))


def cli_query(connection_string:str, query_str:Optional[str]=None, fields:Optional[List[str]]=None):
    database = connect_to_db(connection_string)
    table = connect_to_table(database, DEFAULT_TABLE_NAME)
    if(fields is not None):
        if(len(fields) == 0):
            fields = None
    return list(query(table, query_str, fields))


def cli_get(connection_string:str, text_path:Optional[str]=None, id:Optional[str]=None):
    database = connect_to_db(connection_string)
    table = connect_to_table(database, DEFAULT_TABLE_NAME)
    if(text_path is not None):
        keys = parse_file(text_path)
        return get_entry(table, keys["RowKey"], keys["PartitionKey"])
    else:
        return get_entry(table, id)


def run():
    try:
        command = sys.argv[1]
    except:
        print(help())
        sys.exit()

    if(command == "help" or command == "--help" or command == "-h"):
        print(help())

    elif(command == "publish"):
        try:
            connection_string = sys.argv[2]
            text_path = sys.argv[3]
        except:
            print("Invalid format")
            print("Use case for publish: python table_api.py publish <connection string> <path to text file>")
            sys.exit("See 'python table_api.py help' for more help documentation")
    
        cli_publish(connection_string, text_path)

    elif(command == "delete"):
        try:
            connection_string = sys.argv[2]
            mode = sys.argv[3]
            value = sys.argv[4]
            if(mode != "-f" and mode != "-i"):
                raise
        except:
            print("Invalid format")
            print("Use case for delete: python table_api.py delete <connection string> [OPTIONS]")
            sys.exit("See 'python table_api.py' help for more help documentation")
        
        if(mode == "-f"):
            cli_delete(connection_string, text_path=value)
        elif(mode == "-i"):
            cli_delete(connection_string, id=value)
    
    elif(command == "query"):
        try:
            connection_string = sys.argv[2]
            query_str = None
            fields = []
            if(len(sys.argv) > 3):
                if(sys.argv[3] == "-q"):
                    try:
                        query_str = sys.argv[4]
                        if(query_str == "-f"):
                            raise
                    except:
                        print("-q requires one argument")
                        raise
                    if(len(sys.argv) > 6):
                        if(sys.argv[5] == "-f"):
                            fields=[]
                            for i in range(6, len(sys.argv)):
                                fields.append(sys.argv[i])
                elif(sys.argv[3] == "-f"):
                    if(sys.argv[-2] == "-q"):
                        stop = len(sys.argv) - 2
                        query_str = sys.argv[-1]
                    else:
                        stop = len(sys.argv)
                    for i in range(4, stop):
                        fields.append(sys.argv[i])
        except:
            print("Invalid format")
            print("Use case for query: python table_api.py query <connection string> <table name> [OPTIONS]...")
            sys.exit("See 'python table_api.py help' for more help documentation")
        
        results = cli_query(connection_string, query_str, fields)
        print(json.dumps(results, indent=2))

    elif(command == "get"):
        try:
            connection_string = sys.argv[2]
            mode = sys.argv[3]
            value = sys.argv[4]
            if(mode != "-f" and mode != "-i"):
                raise
        except:
            print("Invalid format")
            print("Use case for delete: python table_api.py get <connection string> [OPTIONS]")
            sys.exit("See 'python table_api.py help' for more help documentation")
        
        if(mode == "-f"):
            results = cli_get(connection_string, text_path=value)
        elif(mode == "-i"):
            results = cli_get(connection_string, id=value)

        print(json.dumps(results, indent=2))

    else:
        print(f"'{command}' is not a recognized command, see help:")
        print(help())
        sys.exit("Command not found")



# MAIN
if(__name__ == "__main__"):
    run()
