from libraries.model import fill_region, fill_iam, fill_ec2, fill_network
from libraries.model import fill_s3, fill_rds, fill_cloudtrail

def scan(account, region_list, services, session):
    """
    scan load an account node children ressources using the session parameter to
    query AWS API on the aws services selected in the services parameter

    Parameters
    ----------
    account : node (object define in Model.py)
        Currently the base element of the model
    region_list : [str]
        list of the aws region that will be scanned
    services : {service_name:bool}
        dictionary that references the services to be scanned
    session
        a boto3 session allowing to query AWS APIs
    """
    # Loads the s3 resources to the account node children
    if services.get('s3'):
        fill_s3(session=session, account=account)
    # Loads the iam resources to the account node children
    if services.get('iam'):
        fill_iam(session=session, account=account)

    # Checking whether the region_node will be necessary
    region_based_services = (services.get('cloudtrail')
                             or services.get('network')
                             or services.get('ec2')
                             or services.get('rds'))

    if region_based_services:
        # Using the parameter region_list to create region nodes
        # to host the resources of the region based services
        fill_region(region_list=region_list, account=account)
        region_node_list = account.get_child_list('Region')
        if services.get('cloudtrail'):
            for region_node in region_node_list:
                fill_cloudtrail(session, region_node)
        if services.get('network'):
            for region_node in region_node_list:
                fill_network(session, region_node)
        if services.get('ec2'):
            for region_node in region_node_list:
                fill_ec2(session, region_node)
        if services.get('rds'):
            for region_node in region_node_list:
                fill_rds(session, region_node)
