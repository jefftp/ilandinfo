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
        """Return the inventory object for the user specified in the credentials file."""
        return Inventory(self.api.get(f"/users/{self.username}/inventory"))

    def get_org_billing_summary(self, uuid):
        """Returns previous month, current month, previous hour, and current hour billing

        Example from iland console:
        https://console.ilandcloud.com/api/v1/orgs/{uuid}/billing-summary
        """
        return Report(self.api.get(f"/orgs/{uuid}/billing-summary"))

    def get_org_billing(self, uuid, date):
        """Returns current billing information
        
        Example from iland console:
        https://console.ilandcloud.com/api/v1/orgs/{uuid}/billing
        """
        parameters = f"year={date.tm_year}&month={date.tm_mon}"
        return Report(self.api.get(f"/orgs/{uuid}/billing?{parameters}"))

    def get_org_billing_by_vdc(self, uuid):
        """Returns billing information by VDC
        
        No example use discovered in the iland console.
        """
        return Report(self.api.get(f"/orgs/{uuid}/billing-by-vdc"))

    def get_org_billing_historical(self, uuid, start_struct, end_struct):
        """Returns a series of historical monthly org costs

        The console pulls the last 5 months to use in the montly bar graph on the billing tab:
        https://console.ilandcloud.com/api/v1/orgs/{uuid}/historical-billing?start=1624027630654&end=1637250430654
        """
        start = int(time.mktime(start_struct)) * 1000
        end = int(time.mktime(end_struct)) * 1000
        parameters = f"start={start}&end={end}"
        return Report(self.api.get(f"/orgs/{uuid}/historical-billing?{parameters}"))


    def get_org_billing_historical_vdc(self, uuid, start, end):
        """Returns the historical billing data by VDC
        
        The console uses historical-billing-by-vdc to build the historical billing bar graphs.
        https://console.ilandcloud.com/api/v1/orgs/{uuid}/historical-billing-by-vdc?startMonth=7&startYear=2021&endMonth=11&endYear=2021
        """
        parameters = f"startYear={start.tm_year}&startMonth={start.tm_mon}&endYear={end.tm_year}&endMonth={end.tm_mon}"
        return Report(self.api.get(f"/orgs/{uuid}/historical-billing-by-vdc?{parameters}"))

    # vdcs-cost-over-invoice-period ? year, month
    # Returns a time series (1 hour increments) of VDCs sum costs for the VDC Cost Accrual Breakdown graph
    # https://console.ilandcloud.com/api/v1/orgs/{uuid}/vdcs-cost-over-invoice-period?year=2021&month=11


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
            'o365-job'      : 'O365_JOB',
            'o365-location' : 'O365_LOCATION',
            'o365-org'      : 'O365_ORGANIZATION',
            'o365-restore'  : 'O365_RESTORE_SESSION',
            'org'           : 'IAAS_ORGANIZATION',
            'template'      : 'IAAS_VAPP_TEMPLATE',
            'vdc'           : 'IAAS_VDC',
            'vapp'          : 'IAAS_VAPP',
            'vapp-network'  : 'IAAS_VAPP_NETWORK',
            'vcc-location'  : 'VCC_BACKUP_LOCATION',
            'vcc-tenant'    : 'VCC_BACKUP_TENANT',
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

class Report:
    def __init__(self, data):
        if 'data' in data:
            self.data = data['data']
        else:
            self.data = data

    def __str__(self):
        return json.dumps(self.data, sort_keys=True, indent=2)

    def __repr__(self):
        return self.data

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
        choices=[
            'backup',
            'company',
            'location',
            'o365-org',
            'org',
            'vapp',
            'vdc',
            'vm'
        ],
        default=None,
        help='Type of object to list'
    )
    billing_parser = subparsers.add_parser(
        'billing',
        help='Display the billing report for the specified service'
    )
    billing_parser.add_argument(
        'service',
        choices=[
            'org',
            'org-by-vdc',
            'org-summary',
            'backup',
            'org-historical',
            'org-historical-by-vdc',
            'vapp',
            'vdc',
            'vm',
            'vm-summary'
        ]
    )
    billing_parser.add_argument(
        'uuid',
        type=str,
        help='service UUID to report on'
    )
    billing_parser.add_argument(
        '--start',
        type=str,
        help='start date in YYYY-MM format'
    )
    billing_parser.add_argument(
        '--end',
        type=str,
        help='end date in YYYY-MM format'
    )
    billing_parser.add_argument(
        '--date',
        type=str,
        help='date in YYYY-MM format'
    )

    return parser.parse_args()

# Billing code points in iland API:
# ?, '/orgs/{uuid}/generate-billing-report' csv only
# ?, '/orgs/{uuid}/billing-reports' supports format param
# 'vac', '/companies/{companyId}/vac-backup-tenants-billing'
# 'backup', '/companies/{companyId}/vcc-backup-tenants-billing'
# 'vapp', '/vapps/{uuid}/billing'
# 'vdc', '/vdcs/{uuid}/billing'
# 'vm', '/vms/{uuid}/billing'
# 'vm-summary', '/vms/{uuid}/billing-summary'

def parse_time(time_string):
    """Take a string with the format YYYY-MM and return a time.struct_time"""
    try:
        time_struct = time.strptime(time_string, '%Y-%m')
    except ValueError:
        sys.exit('Incorrect date format. Correct format is YYYY-MM where YYYY is the four-digit year and MM is the 2 digit month.')

    return time_struct

def requires_start_end(args):
    if not args.start or not args.end:
        sys.exit(f'Missing parameters. {args.command} {args.service} requires --start and --end options.')

def main():
    args = get_args()
    credentials = Credentials(args.credentials_file)
    client = Client(credentials)

    # Set iland logger level to WARNING to reduce noise
    iland.log.LOG.setLevel(logging.WARNING)

    if args.command == 'inventory':
        inventory = client.get_inventory()
        inventory.csv_list_object(args.object)

    if args.command == 'billing':
        if args.service == 'org':
            if args.date:
                date = parse_time(args.date)
            else:
                date = time.localtime()
            report = client.get_org_billing(args.uuid, date)
            print(report)
        elif args.service == 'org-by-vdc':
            report = client.get_org_billing_by_vdc(args.uuid)
            print(report)
        elif args.service == 'org-summary':
            report = client.get_org_billing_summary(args.uuid)
            print(report)
        elif args.service == 'org-historical':
            requires_start_end()
            start = parse_time(args.start)
            end = parse_time(args.end)
            report = client.get_org_billing_historical(args.uuid, start, end)
            print(report)
        elif args.service == 'org-historical-by-vdc':
            requires_start_end()
            start = parse_time(args.start)
            end = parse_time(args.end)
            report = client.get_org_billing_historical_vdc(args.uuid, start, end)
            print(report)


if __name__ == '__main__':
    main()
