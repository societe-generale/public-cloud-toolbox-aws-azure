# Internal dependencies
from Model import Node
from Network import fill_network

##########################
#### RDS Node Builder ####
##########################

def create_db_instance_node(json, vpc):
    """ Builder for a db instance node
    :param json: json from AWS API
    :param vpc: vpc father node
    :return: The db instance node
    """
    resource_type = 'DBInstance'
    name = ''
    if json.get('DBName'):
        name = json.get('DBName')
    label = ('"' + resource_type + '\n' + name
             + '\n Status' + json.get('DBInstanceStatus')
             + '\n Engine' + json.get('Engine') + '"')
    return Node(json=json, resource_type=resource_type,
                id_type='DBInstanceIdentifier', color='aquamarine',
                label=label, father=vpc, service='rds')

##############
#### SCAN ####
##############

def fill_rds(session, region_node):
    """ fill_rds take a boto3 session, a region node
        and add rds instances nodes to the vpcs nodes
    """
    # Verifying that network is filled
    vpc_list = region_node.get_child_list('Vpc')
    if vpc_list == []:
        fill_network(session, region_node)
        vpc_list = region_node.get_child_list('Vpc')

    print '  Filling rds'

    region = region_node.json.get('Region')
    db_instance_list = get_db_instance_lists(session=session, region=region)

    if db_instance_list != []:
        add_db_instances_to_vpcs(vpc_list, db_instance_list)

def get_db_instance_lists(session, region):
    """ Call boto3 api using the session to get the database instance list """
    db_instance_list = []
    rds_client = session.client('rds', region_name=region)
    response = rds_client.describe_db_instances()
    db_instance_list.extend(response.get('DBInstances'))
    while response.get('Marker'):
        response = rds_client.describe_db_instances(Marker=response.get('Marker'))
        db_instance_list.extend(response.get('DBInstances'))
    return db_instance_list

def add_db_instances_to_vpcs(vpc_list, db_instance_list):
    """ The function takes the region vpc node list and the database instance
        json list to create the db instance nodes and add them to the vpc nodes
    """
    for db_instance in db_instance_list:
        # Getting the VpcId from the VpcGroup or the Subnet Group
        if db_instance.get('DBVpcGroup'):
            db_instance['VpcId'] = db_instance.get('DBVpcGroup').get('VpcId')
        else:
            db_instance['VpcId'] = db_instance.get('DBSubnetGroup').get('VpcId')

    # Sorting the instance list to avoid the search
    # when several instances are in the same vpc
    db_instance_list = sorted(
        db_instance_list,
        key=lambda db_instance: db_instance.get('VpcId')
    )

    # Initializing loop variable
    vpc = vpc_list[0]
    for db_instance in db_instance_list:
        if vpc.id != db_instance.get('VpcId'):
            # Getting the vpc of the current instance
            # that may be shared by the next instances in the list
            vpc = next((vpc for vpc in vpc_list
                        if vpc.id == db_instance['VpcId']),
                       None)

        db_instance = create_db_instance_node(json=db_instance, vpc=vpc)
        if vpc is not None:
            vpc.children.append(db_instance)
