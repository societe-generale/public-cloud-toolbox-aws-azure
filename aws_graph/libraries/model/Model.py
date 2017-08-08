##############
 ### NODE ###
##############

# Every AWS resources will be instances of the node class

class Node:
    """ The node is the base of the model used in aws-graph.
        All the aws resources are node class instanciated using different nodes
        builders.
    """

    def __init__(self, json, resource_type, id_type, color='white',
                 label=None, father=None, service=None, ancestors=[]):
        self.resource_type = resource_type
        self.id_type = id_type
        self.id = json.get(id_type)
        # Used to stock the all node attributes
        self.json = json
        #self.methods = []
            # the methods atribute may be used to give a fonction to every node
            # on creation, like a delete function
        # Used to check if the node has been visited in a graph traversal
        self._marked = False
        # List of the children node of the node, can be empty
        self.children = []
        # The main anscestor of the node
        self.father = father
        # List of the node anscestors, almost unused for now
        self.ancestors = ancestors
        # Define which to aws service the node belongs, almost unused for now
        self.service = service
        # The graphviz unique identifier for the node
        self.identifier = '"' + self.resource_type + ' ' + self.id + '"'
        # The graphviz label for the node
        if label is None:
            self.label = '"' + self.resource_type + '\n' + self.id + '"'
        else:
            self.label = label
        # The graphviz style for the node
        self.style = '[fillcolor=' + color +', label=' + self.label + ']'

    def get_child_list(self, resource_type):
        """ Return a list from the node children filtered by resource_type """
        return [child for child in self.children
                if child.resource_type == resource_type]

    def print_graphviz(self, subgraph, max_depth=-1):
        """ This function do a traversal of the node and its children
            to build a graphviz graph by filling the subgraph str array
            cf graph traversal
        """
        # The marked attribute shows if the node has been processed yet
        if self._marked or max_depth == 0:
            return
        self._marked = True
        # Adding the node to the graph
        subgraph.append(self.identifier + ' ' + self.style)
        # The max depth attribute can limit be used
        # to limit the depth of the resulting graph
        if self.children != [] and max_depth != 1:
            for child in self.children:
                # Adding each child to the graph
                child.print_graphviz(subgraph, max_depth - 1)
                # And drawing the edges toward them
                subgraph.append(self.identifier + ' -> ' + child.identifier)

    def print_json(self, node_list, max_depth=-1):
        """ This function do a traversal of the node and its children
            to build a graphviz graph by filling the subgraph str array
            cf graph traversal
        """
        # The marked attribute shows if the node has been processed yet
        if self._marked or max_depth == 0:
            return
        self._marked = True
        # Adding the node to the graph
        node_list.append({self.resource_type : self.json})
        # The max depth attribute can limit be used
        # to limit the depth of the resulting graph
        if self.children != [] and max_depth != 1:
            for child in self.children:
                # Adding each child to the graph
                child.print_json(node_list, max_depth - 1)

    #def unmark_nodes ?

###############
### Helpers ###
###############


def get_name_from_tags(tags):
    """ Used in network and ec2 services to get the tag name if it exists """
    name = ''
    if tags is not None:
        for tag in tags:
            if tag.get('Key') == 'Name':
                name = tag.get('Value')
    return name

######################
 ### NODE Builders ###
######################

def create_account_node(json):
    """ Builder for a account node
    :param json: json from aws api
    :return: The account node
    """
    resource_type = 'Account'
    if json.get('Name'):
        label = ('"' + resource_type
                 + '\n' + json.get('Name')
                 + '\n' + json.get('Id') + '"')
    else:
        label = ('"' + resource_type
                 + '\n' + json.get('Id') + '"')
    return Node(json=json, resource_type=resource_type,
                id_type='Id', color='gold', label=label)

def create_region_node(account, region):
    """ Builder for a region node
    :param account: account father node
    :param region: aws region of the node
    :return: The region node
    """
    resource_type = 'Region'
    account_identifier = account.json.get('Name')
    if account_identifier is None:
        account_identifier = 'account ' + account.id
    label = ('"' + resource_type
             + '\n' + account_identifier
             + '\n' + region + '"')
    json = {'CustomId': account.id + '_' + region}
    json['Region'] = region
    return Node(json=json, resource_type=resource_type,
                id_type='CustomId', color='paleturquoise',
                label=label, father=account, service='region')

def create_cloudtrail_node(json, region_node):
    """ Builder for a cloudtrail node
    :param json: json from AWS API
    :param region_node: region father node
    :return: The cloudtrail node
    """
    resource_type = 'Cloudtrail'
    label = ('"' + resource_type + '\n' + json.get('Name') +
             '\nMultiRegion : ' + str(json.get('IsMultiRegionTrail')) + '"')
    return Node(json=json, resource_type=resource_type,
                id_type='TrailARN', color='mediumspringgreen',
                label=label, father=region_node, service='cloudtrail')

def create_bucket_node(json, account):
    """ Builder for a bucket node
    :param json: json from AWS API
    :param account: account father node
    :return: The bucket node
    """
    resource_type = 'Bucket'
    return Node(json=json, resource_type=resource_type, id_type='Name',
                color='coral', father=account, service='s3')

##############
 ### Scan ###
##############

def fill_region(region_list, account):
    """ This function create the region node for an account node
        using the region_list parameter.
    """
    region_node_list = [create_region_node(account, region)
                        for region in region_list]
    account.children.extend(region_node_list)

def fill_cloudtrail(session, region_node):
    """ This function loads the cloudtrail nodes in an account and the
        incomplete s3 bucket nodes they send their logs toward.
    """
    print '  Filling cloudtrail'
    region = region_node.json.get('Region')
    cloudtrail_client = session.client('cloudtrail', region_name=region)
    cloudtrail_json_list = cloudtrail_client.describe_trails().get('trailList')
    cloudtrail_node_list = [
        create_cloudtrail_node(json=trail, region_node=region_node)
        for trail in cloudtrail_json_list
    ]
    # The buckets are not necessarily in the same aws account as the cloudtrail
    # We create incomplete bucket node list as cloudtrail children list to draw
    # the edges toward the buckets nodes
    for trail in cloudtrail_node_list:
        json = {"Name":trail.json.get('S3BucketName')}
        bucket = create_bucket_node(json=json, account=region_node.father)
        trail.children.append(bucket)
    region_node.children.extend(cloudtrail_node_list)

def fill_s3(session, account):
    """ fill_s3 takes an account node and a boto3 session
    and add a s3 bucket node list as child list to the account"""
    print '  Filling s3'
    s3_client = session.client('s3')
    bucket_list = [
        create_bucket_node(json=bucket, account=account)
        for bucket in s3_client.list_buckets().get('Buckets')
    ]
    account.children.extend(bucket_list)
