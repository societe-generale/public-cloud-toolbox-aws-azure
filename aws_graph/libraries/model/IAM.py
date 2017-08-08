# Standard libraries
import logging
import threading
# External libraries
from botocore.exceptions import ClientError
# Internal dependencies
from Model import Node

################
#### LOGGER ####
################

logging.getLogger(__name__).addHandler(logging.NullHandler())

##########################
#### IAM Node Builder ####
##########################

def create_iam_node(account):
    """ Builder for a iam node
    :param account: account father node
    :return: The bucket node
    """
    resource_type = 'IAM'
    account_identifier = account.json.get('Name')
    if account_identifier is None:
        account_identifier = 'account ' + account.id
    label = '"' + account_identifier + ' ' + resource_type + '"'
    json = {'CustomId': account.id + '_IAM'}
    return Node(json=json, resource_type=resource_type, id_type='CustomId',
                color='goldenrod', label=label, father=account, service='iam')

def create_group_node(json, iam):
    """ Builder for a group node
    :param json: json from AWS API
    :param iam: iam father node
    :return: the created group node
    """
    resource_type = 'Group'
    label = '"' + resource_type + ' : ' + json.get('GroupName') + '"'
    return Node(json=json, resource_type=resource_type, id_type='Arn',
                color='tomato', label=label, father=iam, service='iam')

def create_role_node(json, iam):
    """ Builder for a role node
    :param json: json from AWS API
    :param iam: iam father node
    :return: the created role node
    """
    resource_type = 'Role'
    label = '"' + resource_type + ' : ' + json.get('RoleName') + '"'
    return Node(json=json, resource_type=resource_type, id_type='Arn',
                color='plum', label=label, father=iam, service='iam')

def create_user_node(json, iam):
    """ Builder for a user node
    :param json: json from AWS API
    :param iam: iam father node
    :return: the created user node
    """
    resource_type = 'User'
    label = '"' + resource_type + ' : ' + json.get('UserName') + '"'
    return Node(json=json, resource_type=resource_type, id_type='Arn',
                color='turquoise', label=label, father=iam, service='iam')

def create_policy_node(json, iam):
    """ Builder for a policy node
    :param json: json from AWS API
    :param iam: iam father node
    :return: the created user node
    """
    resource_type = 'Policy'
    label = '"' + resource_type + ' : ' + json.get('PolicyName') + '"'
    json['CustomId'] = json.get('Arn') + iam.father.id
    return Node(json=json, resource_type=resource_type, id_type='CustomId',
                color='limegreen', label=label, father=iam, service='iam')

def create_inline_policy_node(json, resource_type, father):
    """ Builder for an inline policy node
    :param json: json from AWS API
    :param resource_type : type of inline policy
    :param father: father node
    :return: the created user node
    """
    if resource_type == 'GroupPolicy':
        color = 'tomato'
    if resource_type == 'RolePolicy':
        color = 'plum'
    if resource_type == 'UserPolicy':
        color = 'turquoise'
    json['CustomId'] = father.id + ' ' + resource_type + ' ' + json.get('PolicyName')
    label = '"' + resource_type + ' : ' + json.get('PolicyName') + '"'
    return Node(json=json, resource_type=resource_type, id_type='CustomId',
                color=color, label=label, father=father, service='iam')

def create_login_profile_node(json, user):
    """ Builder for a login profile node
    :param json: json from AWS API
    :param user: user father node
    :return: the created login profile node
    """
    resource_type = 'LoginProfile'
    json['CustomId'] = resource_type + ' ' + json.get('UserName') + ' ' + user.id
    create_date = json.get('CreateDate').strftime("%Y-%m-%d %H:%M:%S")
    label = ('"LoginProfile\nCreate Date : ' + create_date
             + '\nPasswordResetRequired : ' + str(json.get('PasswordResetRequired')) + '"')
    return Node(json=json, resource_type=resource_type, id_type='CustomId',
                color='turquoise', label=label, father=user, service='iam')

def create_mfa_device_node(json, user):
    """ Builder for a mfa device node
    :param json: json from AWS API
    :param user: user father node
    :return: the created mfa device node
    """
    resource_type = 'MFADevice'
    enable_date = json.get('EnableDate').strftime("%Y-%m-%d %H:%M:%S")
    label = ('"MFA Device\nUser : ' + json.get('UserName')
             + '\nEnable Date : ' + enable_date + '"')
    return Node(json=json, resource_type=resource_type, id_type='SerialNumber',
                color='turquoise', label=label, father=user, service='iam')

def create_access_key_node(json, user):
    """ Builder for an access key node
    :param json: json from AWS API
    :param user: user father node
    :return: the created access key node
    """
    resource_type = 'AccessKey'
    label = ('"Access Key\nUser : ' + json.get('UserName')
             + '\nStatus : ' + json.get('Status') + '"')
    return Node(json=json, resource_type=resource_type,
                id_type=resource_type + 'Id', color='turquoise',
                label=label, father=user, service='iam')

# TODO def create_virtual_mfa_node

##############
#### SCAN ####
##############

def fill_iam(session, account):
    """ fill_iam take a boto3 session, an account node
        and add iam resources nodes as children nodes
    """
    print '  Filling iam'
    # Creating the iam node to host iam resources
    iam = create_iam_node(account)
    account.children.append(iam)
    iam_client = session.client('iam')
    # Using the aws api "get_account_authorization_details" to get json
    # for most iam resources at once
    try:
        response = iam_client.get_account_authorization_details()
        group_details = response.get('GroupDetailList')
        role_details = response.get('RoleDetailList')
        user_details = response.get('UserDetailList')
        policy_details = response.get('Policies')
        while response.get('Marker'):
            response = iam_client.get_account_authorization_details(
                Marker=response.get('Marker'))
            group_details.extend(response.get('GroupDetailList'))
            role_details.extend(response.get('RoleDetailList'))
            user_details.extend(response.get('UserDetailList'))
            policy_details.extend(response.get('Policies'))
    except ClientError as client_error:
        # Getting the logger that is not shared in the multithreaded context
        # but is supposed to be thread safe
        logging.getLogger(__name__).warning(client_error)
        return

    # Creating policies node list
    attached_policy_list = []
    unattached_policy_list = []

    for policy_detail in policy_details:
        if policy_detail.get('AttachmentCount') == '0':
            policy = create_policy_node(json=policy_detail, iam=iam)
            unattached_policy_list.append(policy)
        else:
            policy = create_policy_node(json=policy_detail, iam=iam)
            attached_policy_list.append(policy)

    # Using the json detail list and attached policy list
    # to create the iam children nodes and their policy nodes

    group_list = fill_group_list(iam=iam, group_details=group_details,
                                 iam_attached_policy_list=attached_policy_list)
    fill_role_list(iam=iam, role_details=role_details,
                   iam_attached_policy_list=attached_policy_list)

    # this function use the session to query the user login details
    # (mfa device, login profile and access keys)
    fill_user_list(session=session, user_details=user_details,
                   iam_attached_policy_list=attached_policy_list,
                   group_list=group_list, iam=iam)

#####################################
## IAM Resources filling fonctions ##
#####################################

def fill_group_list(group_details, iam_attached_policy_list, iam):
    """ This function takes an iam node, a group json list
        and a list of attached policies """
    # Creating group node from json
    group_list = [create_group_node(json=group_detail, iam=iam)
                  for group_detail in group_details]
    for group in group_list:
        # Attaching managed policies
        attach_managed_policies(group.json.get('AttachedManagedPolicies'),
                                iam_attached_policy_list, group)
        # Creating group policy node for the inline policies
        build_inline_policies(group)
    iam.children.extend(group_list)
    return group_list

def fill_role_list(role_details, iam_attached_policy_list, iam):
    """ This function takes an iam node, a role json list
        and a list of attached policies
    """
    # Creating role node from json
    role_list = [create_role_node(json=role_detail, iam=iam)
                 for role_detail in role_details]

    for role in role_list:
        # Attaching managed policies
        attach_managed_policies(role.json.get('AttachedManagedPolicies'),
                                iam_attached_policy_list, role)
        # Creating role policy nodes for the inline policies
        build_inline_policies(role)
    iam.children.extend(role_list)

def fill_user_list(session, user_details, group_list, iam_attached_policy_list,
                   iam):
    """ Creating the user nodes from json adding them to the iam
        and adding the login details to the users
    """
    # Creating user nodes from json
    user_list = [create_user_node(json=user_detail, iam=iam)
                 for user_detail in user_details]
    threads = []
    for user in user_list:
        if user.json.get('GroupList') == []:
            # The ungrouped user are children of the iam node instead of the groups
            iam.children.append(user)
        else:
            add_user_to_groups(user, group_list)

        attach_managed_policies(user.json.get('AttachedManagedPolicies'),
                                iam_attached_policy_list, user)

        # Creating user policy nodes for the inline policies
        build_inline_policies(user)

        # Using multithread to parallelize AWS API calls
        thread = threading.Thread(target=add_login_detail_to_user,
                                  args=(session, user))
        thread.setDaemon(True)
        threads.append(thread)
        thread.start()

    for thread in threads:
        # waithing for the threads before returning
        while thread.isAlive():
            thread.join()

########################
# Iam helper fonctions #
########################

def attach_managed_policies(resource_policy_list, iam_policy_list, resource):
    """ This function takes an iam resource, a json list (from authorization
    details api call) of its attached policies and the iam attached policy node
    list to add the policy nodes to the resources childrens """
    if resource_policy_list == []:
        return
    # Extracting the arn as an unique identifier from the json policy list
    # to build a set
    resource_policy_arns = {
        attached_policy['PolicyArn']
        for attached_policy in resource_policy_list
    }
    # Filtering the iam policy node list by arn using the set
    resource_attached_policy_nodes = [
        policy_node for policy_node in iam_policy_list
        if policy_node.json['Arn'] in resource_policy_arns
    ]
    # Adding the policies to the resource child list
    resource.children.extend(resource_attached_policy_nodes)

def build_inline_policies(resource):
    """ Creating inline policy nodes for the iam resource """
    res_type = resource.resource_type
    inline_policy_json_list = resource.json.get(res_type + 'PolicyList')
    if inline_policy_json_list:
        # Creating inline policy node from their json
        inline_policy_list = [
            create_inline_policy_node(json=inline_policy, father=resource,
                                      resource_type=res_type + 'Policy')
            for inline_policy in inline_policy_json_list
        ]
        resource.children.extend(inline_policy_list)

def add_user_to_groups(user, group_list):
    """ This function takes a user node and the iam group node list
        and add the user nodes to the groups
    """
    # Build a set of group names
    group_names = {group_name for group_name in user.json['GroupList']}
    # Use the set to user to group nodes from the list
    for group in group_list:
        if group.json['GroupName'] in group_names:
            group.children.append(user)

def add_login_detail_to_user(session, user):
    """ Adding the user login detail missing from
    the iam client get_account_authorization_details API call"""
    iam_client = session.client('iam')
    add_login_profile_to_user(iam_client, user)
    add_access_keys_to_user(iam_client, user)
    add_mfa_devices_to_user(iam_client, user)

def add_login_profile_to_user(iam_client, user):
    """ Create the login profile node and adding it to the user node """
    try:
        # AWS API will throw a NoSuchEntity exception
        # if there is no login profile
        response = iam_client.get_login_profile(UserName=user.json.get('UserName'))
        login_profile = create_login_profile_node(json=response.get('LoginProfile'), user=user)
        user.children.append(login_profile)
    except ClientError as client_error:
        # Getting the logger that is not shared in the multithreaded context
        # but is supposed to be thread safe
        logging.getLogger(__name__).warning(client_error)

def add_mfa_devices_to_user(iam_client, user):
    """ Adding mfa devices to user nodes """
    response = iam_client.list_mfa_devices(UserName=user.json.get('UserName'))
    mfa_device_list = response.get('MFADevices')
    while response.get('IsTruncated'):
        response = iam_client.list_mfa_devices(Marker=response.get('Marker'))
        mfa_device_list.extend(response.get('MFADevices'))
    # Using list comprehension to transform the json list in a node list
    mfa_device_list = [
        create_mfa_device_node(json=mfa, user=user)
        for mfa in mfa_device_list
    ]
    user.children.extend(mfa_device_list)

def add_access_keys_to_user(iam_client, user):
    """ Adding access keys to user nodes """
    response = iam_client.list_access_keys(UserName=user.json.get('UserName'))
    access_key_list = response.get('AccessKeyMetadata')
    while response.get('IsTruncated'):
        response = iam_client.list_access_keys(Marker=response.get('Marker'))
        access_key_list.extend(response.get('AccessKeyMetadata'))
    # Using list comprehension to transform the json list in a node list
    access_key_list = [
        create_access_key_node(json=key, user=user)
        for key in access_key_list
    ]
    user.children.extend(access_key_list)
