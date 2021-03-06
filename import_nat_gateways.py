import json
import os
import boto3
import uuid
import logging
from sts import establish_role
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def import_nat_gateways(event, context):
    dynamodb = boto3.resource('dynamodb')
    client = boto3.client('ec2')
    nat_table = dynamodb.Table(os.environ['DYNAMODB_TABLE_NAT_GATEWAYS'])
    cidr_table = dynamodb.Table(os.environ['DYNAMODB_TABLE_CIDRS'])
    accounts_table = dynamodb.Table(os.environ['DYNAMODB_TABLE_ACCOUNTS'])
    accounts = accounts_table.scan()['Items']
    cidrs = cidr_table.scan()['Items']
    regions = [region['RegionName'] for region in client.describe_regions()['Regions']]

    for region in regions:
        for acct in accounts:
            ACCESS_KEY, SECRET_KEY, SESSION_TOKEN = establish_role(acct)
            client = boto3.client('ec2',
                                  aws_access_key_id=ACCESS_KEY,
                                  aws_secret_access_key=SECRET_KEY,
                                  aws_session_token=SESSION_TOKEN,
                                  region_name=region
                                 )
            nats = client.describe_nat_gateways()

            for nat in nats['NatGateways']:
                public_ip = nat['NatGatewayAddresses'][0]['PublicIp']
                acct_id = acct['id']
                nat_id = nat['NatGatewayId']
                nat_vpc_id = nat['VpcId']

                logger.info('Logging NAT Gateway: {0} for account {1}'.format(
                    public_ip, acct)
                )

                response = nat_table.put_item(
                    Item={
                        'id': nat_id,
                        'PublicIp': public_ip,
                        'AccountID': acct_id,
                        'VpcId': nat_vpc_id,
                        'Region': region
                    },
                    ConditionExpression='attribute_not_exists(nat_id)'
                )
