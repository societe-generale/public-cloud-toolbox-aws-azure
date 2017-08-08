# Standard libraries
import json
import logging

# External libraries
import boto3
from botocore.exceptions import ClientError

# Internal dependencies
from libraries.model import create_account_node

logging.getLogger(__name__).addHandler(logging.NullHandler())

#################
#### CONNECT ####
#################

def get_account_list(config):
    """ This function use the configuration file and optionnaly the json file
        accounts.json to get the list of the account that will be scanned and
        returns an account node list
    """
    if config.get('Accounts') == 'from-organization':
        account_list = get_account_list_from_organization(config)

    elif config.get('Accounts') == 'from-json':
        account_list = get_account_list_from_json()
    else:
        account = get_single_account(config)
        if account is None:
            print "aws-graph failed to connect in single account mode"
            raise ValueError
        return [create_account_node(json=account)]

    # Check if account name is matching with cli parameters filtering
    # and creating the account nodes
    account_list = [create_account_node(json=account)
                    for account in account_list
                    if config.get('match') in account['Name']]
    # Raising an error if there is no account left after matching
    if len(account_list) == 0:
        print "aws-graph expected at least one account to be scanned"
        raise ValueError
    return account_list

def get_account_list_from_organization(config):
    """ use config file parameters to query the account list from organization
    """
    # Getting root session
    if config.get('ProfileName'):
        root_session = boto3.Session(profile_name=config.get('ProfileName'))
    else:
        root_session = boto3.Session()
    # Using the root session to assume the organization scanning role
    if config.get('OrganizationScanningRoleArn'):
        sts_client = root_session.client('sts')

        # The call will throw an exception if you lack the rights
        response = sts_client.assume_role(
            RoleArn=config.get('OrganizationScanningRoleArn'),
            RoleSessionName=config.get('RoleSessionName')
        )

        credentials = response['Credentials']
        # Building a session using the assumed role credentials
        session = boto3.Session(
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken']
        )
    else:
        # Trying with the current session
        session = root_session

    # Using the session to scan organization
    organization_client = session.client('organizations')

    # The call will throw an exception if you lack the rights
    response = organization_client.list_accounts()

    # Building the account json list using the scanned account
    account_list = response['Accounts']
    while response.get('NextToken'):
        response = organization_client.list_accounts(
            NextToken=response.get('NextToken'))
        account_list.extend(response['Accounts'])
    return account_list

def get_account_list_from_json():
    """ Parsing accounts.json to return a json account list """
    with open('accounts.json') as json_file:
        return json.load(json_file)['Accounts']

def get_single_account_session(config):
    """ Try to return a single account session
        using the configuration parameters or boto3 default session
    """
    if config.get('ProfileName'):
        session = boto3.Session(profile_name=config.get('ProfileName'))
    elif (config.get('AwsAccessKeyId')
          and config.get('AwsSecretAccessKey')):
        session = boto3.Session(
            aws_access_key_id=config['AwsAccessKeyId'],
            aws_secret_access_key=config['AwsSecretAccessKey']
        )
    else:
        session = boto3.Session()
    return session

def get_single_account(config):
    """ Try to return a single account using the configuration parameters
        or boto3 default session to find at least one account id to scan
    """
    session = get_single_account_session(config)
    # Using sts API to try to get an account id for the profile used
    account_id = session.client('sts').get_caller_identity().get('Account')
    account = {'Id':account_id}
    try:
        # Using organization API to try to get the account informations
        client = session.client('organizations')
        account = client.describe_account(AccountId=account_id).get('Account')
    except ClientError as client_error:
        logging.getLogger(__name__).warning(client_error)
        # Using the config account name if it exists
        if config.get('AccountName'):
            account['Name'] = config.get('AccountName')
    return account

def get_session(account, config):
    """ Returns a session using the method specified in configuration """
    if     (config.get('Accounts') != 'from-json'
            and config.get('Accounts') != 'from-organization'):
        return get_single_account_session(config)
    # Trying to assume role for iam federated account
    if config.get('ConnectionType') == 'iam-federation':
        try:
            session = assume_role(account, config)
        except ClientError as client_error:
            logging.getLogger(__name__).warning(client_error)
            return None
    else:
        # Trying to use account specified key
        if account.json.get('ProfileName'):
            session = boto3.Session(
                profile_name=account.json.get('ProfileName'))
        elif (account.json.get('AwsAccessKeyId')
              and account.json.get('AwsSecretAccessKey')):

            session = boto3.Session(
                aws_access_key_id=account.json['AwsAccessKeyId'],
                aws_secret_access_key=account.json['AwsSecretAccessKey']
            )
        else:
            session = None
    return session

def assume_role(account, config):
    """ Using the account parameter and the config file parameters
        to request a boto3 session using the aws sts assume role mechanic
    """
    # Building the role arn from the account id and the role name
    if account.json.get('AssumedRoleName'):
        role_arn = 'arn:aws:iam::' + str(account.id)+ ':role/' + config.get('AssumedRoleName')
    elif config.get('AssumedRoleName'):
        role_arn = 'arn:aws:iam::' + str(account.id)+ ':role/' + config.get('AssumedRoleName')
    else:
        return None

    print "Assuming " + config.get('AssumedRoleName') + " in " + account.json.get('Name')

    # Connecting to the Iam Federating account using configurated profile
    if account.json.get('ProfileName'):
        profile_name = account.json.get('ProfileName')
        root_session = boto3.Session(profile_name=profile_name)
    elif config.get('ProfileName'):
        profile_name = config.get('ProfileName')
        root_session = boto3.Session(profile_name=profile_name)
    else:
        root_session = boto3.Session()

    # Using the root session to scan the federing iam account
    if account.json.get('Name') == config.get('AccountName'):
        return root_session

    # Assuming the role in the federed account
    sts_client = root_session.client('sts')
    response = sts_client.assume_role(
        RoleArn=role_arn,
        RoleSessionName=config.get('RoleSessionName')
    )
    credentials = response['Credentials']
    session = boto3.Session(
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken']
    )
    return session
