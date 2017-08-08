# AWS Graph README

The goal of this script is to provide a graph output for the AWS resources of an infrastructure in AWS.

This script can be used for audits, in order to visualize the relationship between the resources.

This project is under the Apache 2 license.

## Set Up

Set up your [aws credentials](http://boto3.readthedocs.io/en/latest/guide/configuration.html) for boto3

If there is no profiles specified in the configuration files, aws-graph will try to use the default credentials

Set up your [aws credentials](http://boto3.readthedocs.io/en/latest/guide/configuration.html) for boto3

If there are no profiles specified in the configuration files, aws-graph will try to use the default credentials.

Install [python 2.7](http://python-guide-pt-br.readthedocs.io/en/latest/starting/installation/)
and [Graphviz 2.38](http://www.graphviz.org/Download..php) (the only version tested)

For windows:

 * Add "Python27" and "Graphviz2.38\bin" directories to Path

Clone the project.

Use pip install in the project directory to install external dependancies and add aws-graph in python modules:

    python pip install .

Fill the config.json file to suit your needs (see configuration).

Run with console and command line arguments.

For windows:

    python.exe .\aws_graph.py
    or
    Python27\Scripts\aws-graph.exe

## Usage

### Command Line Arguments

	'-h' / '--help' (not implemented yet) : show help

Account Targeting:

	'--match=<string>' : only accounts whose names contains the given string will be scanned

Resources Targeting:

	'--region=us-east-1' : set the region that will be scanned, the option 'all' is used to scan every region.

Traversal Options:

	'--max-depth=<integer>' : choose a maximum depth for the output graph, the depth must be an integer
	'--threading' : threading will improve the speed of the script at the expense of the output readability,
	the option is set to false by default.

Output Selection:

	'--json' : change the default graphviz output to a JSON output.

Service Selection:

	'--iam' : show IAM and its childs (user / role / group / policy)
	'--rds' : show rds instances
	'--ec2' : show ec2 instances and volumes
	'--s3' : show s3 buckets
	'--network' : show the network resources (vpc, peering, subnets)
	'--cloudtrail' : show the trails and the buckets they forward the logs to.

## Configuration

### Configuration file

#### Configuration file syntax

The configuration is set in the config.json file.

	{
		"Config":
		{
			<OptionName>:<value>
		},
		"DefaultServicesSelection":
		{
			"s3":[true|false],
			"iam":[true|false],
			"ec2":[true|false],
			"rds":[true|false],
			"cloudtrail":[true|false]
		}
	}

#### Configuration file options

 * "ProfileName": AWS credential profile name used in single and IAM-federation connection options
 * "RoleSessionName": Session name used for IAM-federation assume role
 * "AssumedRoleName": Role name used to build the role ARN for the IAM federation assume role
 * "OrganizationScanningRoleArn": AWS role ARN assumed to get the list of account from AWS organization
 * "AccountName": Used to know if the current account is the root account in IAM federation
 * "HTTPS_PROXY": Optional option specifying a proxy for AWS API calls
 * "LOG_DIR": The directory where the logs are recorded
 * "LOG_LEVEL": [DEBUG|INFO|WARNING|ERROR]: Specifying the level of calls
 * "OutputType": [graphviz|json]: the output of the script
 * "OutputDir": The directory where the logs are recorded
 * "OutputImageFormat": The default output is svg and works the best, [possible formats](http://www.graphviz.org/doc/info/output.html)
 * "ConnectionType": [profile|access-key|iam-federation] see Connection options
 * "Accounts": [from-organization|from-json|single] see Connection options

## Connection options

### Accounts

The scanned accounts can be:
 * the default account.
 * the only configurated account.
 * provided from the accounts.json file.
 * fetched using AWS organisation.

#### single

Using the "ProfileName", an "AwsAccessKeyId" and "AwsSecretAccessKey" pair from the config.json file or the default boto3 session
as an account to scan.

#### from-json

Using the accouns.json file to store the account list to scan.

Just below is an example accounts.json:

	{
		"Accounts":
		[
			{
				"Name":<account name>,
				"Id":<account id>,
				"AwsAccessKeyId":false,
				"AwsSecretAccessKey":false,
				"ProfileName":false,
				"AssumedRoleName":false
			}
		]
	}

The access key / secret key pair or the profile name can be used to create a session for an account.
The assumed role name can be used in IAM federation to assume a specific role on an account.
The file can contain as many accounts as you want.

#### from-organization

The config "ProfileName" or the default profile will be used to assume the "OrganizationScanningRoleArn".
The session obtained from that assume role will be used to get the list of accounts from AWS organization.

### Connection type

The session used to scan an account can be built using:
 * a profile
 * an access key/secret key pair from the JSON list
 * the IAM federation.

#### Iam Federation

An IAM federation uses an IAM account federating the users to connect to roles in the resources account.

The script will build a role ARN using the "AssumedRoleName" from accounts.json or from the config.json file and targeted account id.

Then the targeted account "ProfileName" from accounts.json,  the "ProfileName" from the config.json file or default profile will be used to connect to a base session. If the account name is the same as the config.json file "AccountName" the session will be used for the scanning. Otherwise, the base session will be used to try an assume role on the role ARN built above.

## Operating Model

The script will use one of connection options to obtain boto3 sessions to scan the AWS accounts for AWS resources
and instantiate python Nodes for each resource to build a tree with an account as the root.
Then a tree traversal will be used on each tree to build the graphviz or JSON output.

## Node Tree Organization
The script will show:
* Account
	* IAM
		* Groups
			* Attached Policies
			* Group inline policies
			* Users
				* Attached Policies
				* User inline policies
				* Login Profile
				* Access Key
				* MFA device
				* Virtual MFA Device [TODO]
		* Users (outside of groups)
			(same children as users inside a group)
		* Roles
			* Role inline policies
			* Attached Policies
		* Detached Policies
	* S3 buckets
	* Region Node
		* CloudTrail configuration
			* (which accounts log flows to which S3)
		* VPC
			* VPC peerings (hard disabled in the code to protect the output readability) 
			* Subnets
				* EC2 instances
					* Attached EBS volumes
			* RDS instances
		* Detached EBS volumes
