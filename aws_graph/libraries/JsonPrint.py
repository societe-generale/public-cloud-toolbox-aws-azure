import io
import json
from datetime import datetime

def json_serial(obj):
    """ JSON serializer for objects not serializable by default json code:
        allows to avoid datetime non-serialisable exceptions in json dumps
    """

    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError("Type not serializable")

def print_json(account_list):
    """ This function takes the account node list and print a json dump
        of all the nodes in the list.
    """
    json_node_list = []
    # Adding the json of every node for each account in the list
    for account_node in account_list:
        account_node.print_json(json_node_list)

    output_file_name = ('aws-graph-output/output-'
                        + datetime.now().strftime("%Y-%m-%d %H-%M-%S")
                        + '.json')
    # Writing the json to the output file
    with io.open(output_file_name, 'w', encoding='utf-8') as output_file:
        # Converting the list of dict to write
        output_file.write(
            json.dumps(json_node_list, default=json_serial, ensure_ascii=False)
        )
    print "Dumping json output to " + output_file_name
