# Standard libraries
import os
import json
import logging
import datetime
import threading

# Internal dependencies
from libraries import get_session, get_account_list
from libraries import scan
from libraries import get_default_graph, fill_graph_from_resources, render_graph
from libraries import set_default_options, set_options_from_cli
from libraries import set_services_from_cli
from libraries import print_json


def set_up_log(config):
    """ Setting up the logger for aws-graph using config.json """
    # Setting log directory and log level to config file value
    log_dir = config.get('LOG_DIR')
    log_level = config.get('LOG_LEVEL')

    # Using default values if they are not set
    if log_dir is None:
        log_dir = ".aws_graph_logs"
    if log_level is None:
        log_level = "WARNING"

    # Append script file absolute path if the logfile is a relative path
    if log_dir.startswith('.'):
        script_path = os.path.dirname(os.path.abspath(__file__)) + os.sep
        log_dir = script_path + log_dir.split('.')[1]

    # Creating the logs directory if it is missing
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Setting logfile name using current timestamp
    log_file = (log_dir + os.sep + 'aws_graph '
                + datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
                + '.log')

    # Setting up logs FileHandler
    handler = logging.FileHandler(log_file)
    formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)

    # Adding FileHandler to the connect logger
    connection_logger = logging.getLogger('libraries.Connect')
    connection_logger.addHandler(handler)
    connection_logger.setLevel(log_level)

    # Adding FileHandler to the iam logger
    iam_logger = logging.getLogger('libraries.model.IAM')
    iam_logger.addHandler(handler)
    iam_logger.setLevel(log_level)

    # Adding FileHandler to the ec2 logger
    ec2_logger = logging.getLogger('libraries.model.EC2')
    ec2_logger.addHandler(handler)
    ec2_logger.setLevel(log_level)

def get_resources(accounts, config, services):
    """ This function loads an aws account node children """

    # Preparing a list to store the threads if the multi-threading is enabled
    # for the accounts scans
    if config.get('threading'):
        threads = []

    for account in accounts:
        # Getting a boto3 session using the connection option
        # set in the configuration
        session = get_session(account, config)
        if session is None:
            if account.json.get('Name'):
                print ("  Connection to account "
                       + account.json['Name'] + " failed")
            else:
                print "Connection to account " + account.id + " failed"
            continue
        # Using aws api to get latest region list if all the region are scanned
        if config.get('region') == 'all':
            ec2_client = session.client('ec2', region_name='eu-west-1')
            region_list = [
                region.get('RegionName')
                for region in ec2_client.describe_regions().get('Regions')
            ]
        else:
            region_list = [config.get('region')]

        if config.get('threading'):
            # Launching the scan function in a daemon thread
            # to parallelize the aws api calls
            thread = threading.Thread(
                target=scan,
                args=(account, region_list, services, session))
            thread.setDaemon(True)
            threads.append(thread)
            thread.start()
        else:
            scan(account=account, region_list=region_list,
                 services=services, session=session)

    if config.get('threading'):
        for thread in threads:
            # waithing for the threads to end before building the graphviz graph
            while thread.isAlive():
                thread.join()

##############
#### MAIN ####
##############

def main():
    """ The main of the script """

    # Trying to open the config file to get the script configuration and
    # the default options and services.
    try:
        with open('config.json') as config_file:
            config = json.load(config_file)
    except (OSError, IOError):
        print "Configuration file config.json not found, using default parameters"
        # Initialiasing an empty configuration and the command line options
        # or default fallback will be used
        config = {'Config':{}}

    default_services_selection = config.get('DefaultServicesSelection')

    # Removing default services from config
    config = config.get('Config')

    # setting the default configuration options needed for the script
    set_default_options(config)

    # Adding a file handler to the loggers
    set_up_log(config)

    # Setting proxy from configuration
    if config.get('HTTPS_PROXY'):
        os.environ['https_proxy'] = config.get('HTTPS_PROXY')

    # Using the command line parameters to set options and select services
    set_options_from_cli(config)
    services = set_services_from_cli(default_services_selection)

    # Creating a Digraph object from graphviz library and adding default options
    graph = get_default_graph()

    # Using the connection function set in the configuration
    # to create an account node list
    account_list = get_account_list(config)

    # Using configuration to open an AWS session by account
    # and query the account's resources using boto3 client API
    # to loads the account resources nodes
    get_resources(account_list, config, services)

    if config['OutputType'] == 'json':
        # Dumping node's json to output file if it is the desired format
        print_json(account_list)
    else:
        # Fill the graph by printing the resources nodes aws graphiz representation
        fill_graph_from_resources(config, account_list, graph)

        # Rendering the graph as an image
        output_image_format = config.get('OutputImageFormat')
        render_graph(graph, services, output_image_format)

# Only run the main function if the file is python entry point
if __name__ == "__main__":
    main()
