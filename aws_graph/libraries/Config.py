import sys

def set_default_options(config):
    """
        Setting options default if they are not set in the config file
        theses options should be set in the config file but will not make
        the script crash if missing
    """
    if not config.get('region'):
        config['region'] = 'us-east-1'
    if not config.get('Accounts'):
        config['Accounts'] = 'single'
    if not config.get('threading'):
        config['threading'] = False
    if not config.get('env'):
        config['env'] = 'all'
    if not config.get('match'):
        config['match'] = ''
    if not config.get('max-depth'):
        config['max-depth'] = -1
    if not config.get('OutputType'):
        config['OutputType'] = 'graphviz'

def set_options_from_cli(config):
    """ Setting config options from command line parameters """
    for arg in sys.argv:
        if arg.startswith('--region='):
            config['region'] = arg.split('=')[1]

        if arg.startswith('--accounts='):
            config['Accounts'] = arg.split('=')[1]

        if arg.startswith('--max-depth='):
            try:
                config['max-depth'] = int(arg.split('=')[1])
            except ValueError:
                pass

        if arg.startswith('--env='):
            config['env'] = arg.split('=')[1]

        if arg.startswith('--match='):
            config['match'] = arg.split('=')[1]

        if arg.startswith('--threading'):
            config['threading'] = True

        if arg.startswith('--json'):
            config['OutputType'] = 'json'

def set_services_from_cli(default_services_selection):
    """ Setting services selection from command line parameters """
    services = {}
    # If services are selected using cli interface
    # the default service selelction will not be used
    default_services = True
    for arg in sys.argv:
        if arg == '--iam':
            services['iam'] = True
            default_services = False

        if arg == '--network':
            services['network'] = True
            default_services = False

        if arg == '--ec2':
            services['ec2'] = True
            default_services = False

        if arg == '--rds':
            services['rds'] = True
            default_services = False

        if arg == '--cloudtrail':
            services['cloudtrail'] = True
            default_services = False

        if arg == '--s3':
            services['s3'] = True
            default_services = False

    # Setting using default services selection when they are not set
    # from the command line arguments
    if default_services:
        services = default_services_selection
        # Fallback services selection in case default services are not set
        # in the config file
        if services is None:
            services = {}
        if services == {}:
            services['s3'] = True
            services['iam'] = True
            services['rds'] = True
            services['ec2'] = True
            services['network'] = True
            services['cloudtrail'] = True
    return services
