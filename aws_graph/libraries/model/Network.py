# Internal dependencies
from Model import Node, get_name_from_tags

###############################
#### Network Node Builders ####
###############################

def create_vpc_node(json, region_node):
    """ Builder for a vpc node
    :param json: json from AWS API
    :param region_node: region father node
    :return: The vpc node
    """
    resource_type = 'Vpc'
    name = get_name_from_tags(json.get('Tags'))
    # Using json fields to build graphviz label
    label = ('"' + resource_type +
             '\n' + name +
             '\n' + json.get('VpcId') + '"')
    return Node(json=json, resource_type=resource_type,
                id_type='VpcId', color='orange', label=label,
                father=region_node, service='network')

def create_subnet_node(json, vpc):
    """ Builder for a subnet node
    :param json: json from AWS API
    :param vpc: vpc father node
    :return: The subnet node
    """
    resource_type = 'Subnet'
    name = get_name_from_tags(json.get('Tags'))
    # Using json fields to build graphviz label
    label = ('"' + resource_type
             + '\n' + name
             + '\n' + json.get('SubnetId')
             + '\nAZ :' + json.get('AvailabilityZone') + '"')
    return Node(json=json, resource_type=resource_type,
                id_type='SubnetId', color='lightblue',
                label=label, father=vpc, service='network')

def create_vpc_peering_node(json, vpc_list):
    """ aws eb2 vpc peering connection node builder """
    resource_type = 'VpcPeeringConnection'
    # Using json fields to build graphviz label
    label = '"' + resource_type + '\n' + json.get(resource_type + 'Id')
    if json.get('State'):
        label += '\n State : ' + json.get('State')
    if json.get('ExpirationTime'):
        label += '\n ExpirationTime : ' + str(json.get('ExpirationTime'))
    label += '"'
    # Getting requester and/or accepter vpc node if they are in the same account
    # and region
    requester_vpc_id = json['RequesterVpcInfo']['VpcId']
    accepter_vpc_id = json['AccepterVpcInfo']['VpcId']
    requester_vpc = None
    accepter_vpc = None
    for vpc in vpc_list:
        if vpc.id == requester_vpc_id:
            requester_vpc = vpc
        elif vpc.id == accepter_vpc_id:
            accepter_vpc = vpc
        if requester_vpc is not None and accepter_vpc is not None:
            break
    # Setting father and ancestors depending on the vpcs
    # present in the current account and region
    father = None
    ancestors = None
    if requester_vpc is not None and accepter_vpc is not None:
        father = requester_vpc
        ancestors = [accepter_vpc]
    elif requester_vpc is not None:
        father = requester_vpc
    elif accepter_vpc is not None:
        father = accepter_vpc
    # Creating the vpc peering node using the parameters
    return Node(json=json, resource_type=resource_type,
                id_type=resource_type + 'Id', color='orange', label=label,
                father=father, service='ec2', ancestors=ancestors)

##############
#### SCAN ####
##############

def fill_network(session, region_node):
    """
        This function loads the children network nodes
        in the given region nodes using the session to query AWS APIs
    """
    print '  Filling network'
    region = region_node.json.get('Region')
    ec2_client = session.client('ec2', region_name=region)
    # Getting json list from api
    vpc_json_list = ec2_client.describe_vpcs().get('Vpcs')
    # Creating vpc nodes from json using list comprehension
    vpc_node_list = [create_vpc_node(json=vpc, region_node=region_node)
                     for vpc in vpc_json_list]
    region_node.children.extend(vpc_node_list)
    # Loads vpc children nodes
    if vpc_node_list != []:
        fill_subnets(ec2_client, vpc_node_list)
        # Vpc peering make the graphviz output messy
        #fill_vpc_peering(ec2_client, vpc_node_list)

def fill_subnets(ec2_client, vpc_list):
    """ this function loads the vpc peering in the  given vpc nodes list """
    response = ec2_client.describe_subnets()
    # Getting json list from api sorter by vpc id
    subnet_list = sorted(response.get('Subnets'),
                         key=lambda subnet: subnet['VpcId'])
    # Initializing vpc variable
    vpc = vpc_list[0]
    for subnet in subnet_list:
        # Getting subnet's vpc if it is different from last subnet
        if vpc.id != subnet['VpcId']:
            vpc = next(vpc for vpc in vpc_list if vpc.id == subnet['VpcId'])
        # Using the vpc to create the subnet node
        subnet_node = create_subnet_node(json=subnet, vpc=vpc)
        # and adding it the vpc's subnets child_list
        vpc.children.append(subnet_node)

def fill_vpc_peering(ec2_client, vpc_list):
    """ this function loads the vpc peering in the  given vpc nodes list

        if the accepter and requester vpc are not in the same region or account
        there will be two vpc peering node with the same id that will be merged
        in a graphiz print
    """
    response = ec2_client.describe_vpc_peering_connections()
    # Getting json list from api
    vpc_peering_json_list = response['VpcPeeringConnections']
    # Creating vpc peering nodes from json using list comprehension
    vpc_peering_node_list = [create_vpc_peering_node(peering, vpc_list)
                             for peering in vpc_peering_json_list]
    # Adding the vpc peering in the child lists of the accepter vpc
    # and the requester vpc
    for peering in vpc_peering_node_list:
        peering.father.children.append(peering)
        if peering.ancestors:
            peering.ancestors[0].children.append(peering)
