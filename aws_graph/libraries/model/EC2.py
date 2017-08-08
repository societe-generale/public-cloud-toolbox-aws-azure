import logging

# Internal dependencies
from Model import Node, get_name_from_tags
from Network import fill_network

logging.getLogger(__name__).addHandler(logging.NullHandler())

###########################
#### EC2 Node Builders ####
###########################

def create_instance_node(json, subnet):
    """ aws ec2 instance node builder """
    resource_type = 'Instance'
    name = get_name_from_tags(json.get('Tags'))
    label = ('"' + resource_type
             + '\n' + name
             + '\n' + json.get('InstanceId') + '"')
    return Node(json=json, resource_type=resource_type,
                id_type=resource_type + 'Id', color='yellowgreen',
                label=label, father=subnet, service='ec2')

def create_volume_node(json, instance=None):
    """ aws ebs volume node builder """
    resource_type = 'Volume'
    name = get_name_from_tags(json.get('Tags'))
    label = ('"' + resource_type
             + '\nName : ' + name
             + '\nId : ' + json.get(resource_type + 'Id')
             + '\n State : ' + json.get('State')
             + '\n Type : ' + json.get('VolumeType') + '"')
    return Node(json=json, resource_type=resource_type,
                id_type=resource_type + 'Id', color='silver',
                label=label, father=instance, service='ec2')

##############
#### SCAN ####
##############

def fill_ec2(session, region_node):
    """ this function load all the ec2 service nodes
        for a region using a region and a boto3 session
    """
    # Verifying that network is filled
    vpc_list = region_node.get_child_list('Vpc')
    if vpc_list == []:
        fill_network(session, region_node)
        vpc_list = region_node.get_child_list('Vpc')

    print '  Filling ec2'
    region = region_node.json.get('Region')
    ec2_client = session.client('ec2', region_name=region)
    # Recuperating actives ec2 instances using boto3 client api
    instance_json_list = get_active_instance_list(ec2_client=ec2_client)
    if instance_json_list != []:
        # Using list comprehension to get the list of all th subnet
        # in the region for the current account
        subnet_list = [child
                       for vpc in vpc_list
                       for child in vpc.children
                       if child.resource_type == "Subnet"]
        # Using the subnet list to instanciate the ec2 instance nodes
        # and adding them to the subnets child lists
        instance_node_list = add_instances_to_subnets(subnet_list,
                                                      instance_json_list)

        volume_list = get_volume_list(ec2_client)
        # Creating two list for volume separated by attachment
        attached_volume_list = [v for v in volume_list if is_volume_attached(v)]
        detached_volume_list = [create_volume_node(v)
                                for v in volume_list
                                if not is_volume_attached(v)]

        for volume in attached_volume_list:
            # Getting attached instance ids
            attached_instance_id = [attachment.get('InstanceId')
                                    for attachment in volume['Attachments']]
            if len(attached_instance_id) != 1:
                logging.getLogger(__name__).warning(
                    volume.id + "is attached to an incorrect number of instances"
                )
            else:
                # Adding the volume to the instances
                for instance_id in attached_instance_id:
                    instance = next(instance for instance in instance_node_list
                                    if instance.id == instance_id)
                    instance.children.append(create_volume_node(json=volume,
                                                                instance=instance))
        # Detached instances are rattached to the region node
        # (instead of the non represented Availibility Zones)
        region_node.children.extend(detached_volume_list)

def get_active_instance_list(ec2_client):
    """ This function returns the json list of ec2 non terminated instances """
    # terminated instances are not childrens of a subnet
    response = ec2_client.describe_instances(
        Filters=[
            {'Name': 'instance-state-name',
             'Values':['running', 'stopping', 'stopped']}
        ]
    )
    # Getting the instances from the json
    instance_list = [
        instance
        for reservation in response.get('Reservations')
        for instance in reservation.get('Instances')
    ]
    # If there is too many instances, calling the api with the "next token" will
    # provide the remaining instances
    while response.get('NextToken'):
        response = ec2_client.describe_instances(
            NextToken=response.get('NextToken'),
            Filters=[{'Name': 'instance-state-name',
                      'Values':['running', 'stopping', 'stopped']}])
        instance_list.extend(
            [instance
             for reservation in response.get('Reservations')
             for instance in reservation.get('Instances')]
        )
    return instance_list

def get_volume_list(ec2_client):
    """ This function returns the json list of volumes """
    response = ec2_client.describe_volumes()
    volume_list = response.get('Volumes')
    # If there is too many volumes, calling the api with the "next token" will
    # provide the remaining volumes
    while response.get('NextToken'):
        response = ec2_client.describe_volumes()
        volume_list.extend(response.get('Volumes'))
    return volume_list

def add_instances_to_subnets(subnet_list, instance_list):
    """ Using the subnet nodes as father to build the instance nodes
        and adding them to the subnet nodes children
    """
    if len(subnet_list) < 1:
        return []

    # Sorting the instance list to avoid the search
    # when several instances are in the same subnet
    instance_list = sorted(
        instance_list,
        key=lambda instance: instance.get('SubnetId')
    )

    # Initializing loop variable
    subnet = subnet_list[0]
    for index, instance in enumerate(instance_list):
        if subnet.id != instance['SubnetId']:
            # Getting the subnet of the current instance
            # that may be shared by the next instances in the list
            subnet = next((subnet for subnet in subnet_list
                           if subnet.id == instance['SubnetId']),
                          None)
            # TODO Attach instances with no subnet to their vpc
        instance = create_instance_node(json=instance, subnet=subnet)
        # Remplacing the json by the node at the current index of the list
        instance_list[index] = instance
        if subnet is not None:
            subnet.children.append(instance)

    return instance_list

def is_volume_attached(volume):
    """ This function checks if a volume is attached
        and returns the answer to taht question as a boolean
    """
    if not volume.get('Attachments'):
        return False
    attached_states = {'attached', 'attaching'}
    for attachment in volume['Attachments']:
        if attachment.get('State') in attached_states:
            return True
    # The volume is not attached since the above return
    # did not exit the function
    return False
