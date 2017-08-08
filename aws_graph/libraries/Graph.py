import datetime

# External libraries
from graphviz import Digraph


def get_default_graph():
    """ Setting graphviz graph global options """
    graph = Digraph('AWS', engine='dot')
    graph.body.append('splines=line')
    graph.body.append('rankdir=LR')
    graph.body.append('outputorder=edgesfirst')
    graph.node_attr.update(shape='rectangle', style='filled', color='black')
    return graph

def fill_graph_from_resources(config, accounts, graph):
    """ This function takes an account node list to
        add the graphviz representation of the nodes
        and their children nodes
    """
    # for each account node
    for account in accounts:
        # not showing empty accounts
        if account.children != []:
            max_depth = int(config.get('max-depth'))
            # Calling the print_graphviz of the account node
            # to fill the string array with the nodes and edges
            account.print_graphviz(subgraph=graph.body, max_depth=max_depth)

def render_graph(graph, services, output_image_format=None):
    """ Render the graph in an output file. """
    # add the shown services to the graph name
    srv = ''
    if services.get('ec2'):
        srv += '-ec2'
    if services.get('rds'):
        srv += '-rds'
    if services.get('iam'):
        srv += '-iam'
    if services.get('s3'):
        srv += '-s3'
    if services.get('cloudtrail'):
        srv += '-ct'
    if output_image_format is None:
        graph.format = 'svg'
    else:
        graph.format = output_image_format
    output_filename = ('aws-graph-output/aws-graph-'
                       + datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
                       + srv + '.gv')
    print "Dumping graphviz output file to " + output_filename
    graph.render(output_filename, view=True)
