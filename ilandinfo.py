#!/usr/bin/env python3
#
# Copyright 2021 iland Internet Solutions Corporation
#
# Licensed under the 3-Clause BSD License (the "License"). You may not use
# this product except in compliance with the License. A copy of the License
# is located in the file LICENSE.
#

__version__ = '1.0.0'

import iland
import argparse
import logging
import json
import time
import sys

class Credentials:
    def __init__(self, credentials_file):
        with open(credentials_file, 'r') as file:
            credentials = json.load(file)

        self.client_id = credentials['client_id']
        self.client_secret = credentials['client_secret']
        self.username = credentials['username']
        self.password = credentials['password']

class Client:
    def __init__(self, credentials):
        self.username = credentials.username
        self.api = iland.Api(
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            username=credentials.username,
            password=credentials.password
        )

    def get_inventory(self):
        return Inventory(self.api.get(f"/users/{self.username}/inventory"))

class Task:
    def __init__(self, client, task_data):
        self.client = client
        self.uuid = task_data['uuid']
        self.status = task_data['status']
        self.active = task_data['active']
        self.message = task_data['message']
        self.operation = task_data['operation']

    def refresh(self):
        task = self.client.api.get(f"/tasks/{self.uuid}")
        self.status = task['status']
        self.active = task['active']
        self.message = task['message']
        self.operation = task['operation']
        return

    def watch(self):
        while True:
            self.refresh()
            if self.active == False:
                if self.status == 'success':
                    print(f"{self.operation} - {self.status}")
                else:
                    print(f"{self.operation} - {self.status} ({self.message})")
                return
            else:
                print(f"{self.operation} - {self.status}")
            time.sleep(5)

class Inventory:
    def __init__(self, data):
        self.data = data

    def get_entity(self, object):
        items = []
        entity_lookup = {
            'catalog'       : 'IAAS_CATALOG',
            'company'       : 'COMPANY',
            'edge'          : 'IAAS_EDGE',
            'location'      : 'IAAS_LOCATION',
            'media'         : 'IAAS_MEDIA',
            'network'       : 'IAAS_INTERNAL_NETWORK',
            'o365_job'      : 'O365_JOB',
            'o365_location' : 'O365_LOCATION',
            'o365_org'      : 'O365_ORGANIZATION',
            'o365_restore'  : 'O365_RESTORE_SESSION',
            'org'           : 'IAAS_ORGANIZATION',
            'template'      : 'IAAS_VAPP_TEMPLATE',
            'vdc'           : 'IAAS_VDC',
            'vapp'          : 'IAAS_VAPP',
            'vapp_network'  : 'IAAS_VAPP_NETWORK',
            'vcc_location'  : 'VCC_BACKUP_LOCATION',
            'vcc_tenant'    : 'VCC_BACKUP_TENANT',
            'vpg'           : 'IAAS_VPG',
            'vm'            : 'IAAS_VM'
        }
        api_entity = entity_lookup[object]
        for company in self.data['inventory']:
            for item in company['entities'][api_entity]:
                items.append(item)
        return items

    def csv_list_object(self, object):
        entity_list = self.get_entity(object)
        print('Name, UUID')
        for item in entity_list:
            print(f"{item['name']}, {item['uuid']}")

def get_args():
    """ Setup the argument parser and parse the arguments.

        ilandinfo inventory object
        
        -c, --credential-file  default=creds.json
    """
    parser = argparse.ArgumentParser(
        description='Collect information about your iland Cloud environment using the iland cloud API'
    )
    parser.add_argument(
        '--credentials-file', '-c',
        type=str,
        default='creds.json',
        help='Credentials file (JSON format)'
    )

    subparsers = parser.add_subparsers(
        dest='command',
        required=True
    )
    inventory_parser = subparsers.add_parser(
        'inventory',
        help='Display the inventory for the specified object'
    )
    inventory_parser.add_argument(
        'object',
        choices=['backup', 'company', 'location', 'o365_org', 'org', 'vapp', 'vdc', 'vm'],
        default=None,
        help='Type of object to list'
    )
    return parser.parse_args()

def main():
    args = get_args()
    credentials = Credentials(args.credentials_file)
    client = Client(credentials)

    # Set iland logger level to WARNING to reduce noise
    iland.log.LOG.setLevel(logging.WARNING)

    if args.command == 'inventory':
        inventory = client.get_inventory()
        inventory.csv_list_object(args.object)


if __name__ == '__main__':
    main()
