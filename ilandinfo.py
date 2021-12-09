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
import datetime

from dateutil.relativedelta import relativedelta

class Inventory:
    def __init__(self, data: dict):
        self.company_id = data['company_id']
        self.company_name = data['company_name']
        self.entities = data['entities']

    def __str__(self):
        data = {
            'company_id'  : self.company_id,
            'company_name': self.company_name,
            'entities'    : self.entities
        }
        return json.dumps(data, sort_keys=True, indent=2)

    def get_entity(self, object: str):
        """Convert the object type used in the CLI to the API entity label."""
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
        for item in self.entities[api_entity]:
            items.append(item)
        return items

    def csv_list_object(self, object: str):
        """Print out a CSV style inventory list of the object type specified."""
        entity_list = self.get_entity(object)
        print('Name, UUID')
        for item in entity_list:
            print(f"{item['name']}, {item['uuid']}")

class Report:
    def __init__(self, data: dict):
        if 'data' in data:
            self.data = data['data']
        else:
            self.data = data

    def __str__(self):
        return json.dumps(self.data, sort_keys=True, indent=2)

    def __repr__(self):
        return self.data

class Client:
    def __init__(self, credentials: dict):
        self.username = credentials['username']
        self.api = iland.Api(**credentials)

    def get_inventory(self) -> Inventory:
        """Return the inventory object for the user specified in the credentials file."""
        inventory = self.api.get(f"/users/{self.username}/inventory")
        return Inventory(inventory['inventory'][0])

    def get_org_billing_summary(self, uuid: str) -> Report:
        """Returns previous month, current month, previous hour, and current hour billing

        Example from iland console:
        https://console.ilandcloud.com/api/v1/orgs/{uuid}/billing-summary
        """
        return Report(self.api.get(f"/orgs/{uuid}/billing-summary"))

    def get_org_billing(self, uuid: str, date: datetime.date) -> Report:
        """Returns current billing information
        
        Example from iland console:
        https://console.ilandcloud.com/api/v1/orgs/{uuid}/billing
        """
        parameters = f"year={date.year}&month={date.month}"
        return Report(self.api.get(f"/orgs/{uuid}/billing?{parameters}"))

    def get_org_billing_by_vdc(self, uuid: str) -> Report:
        """Returns billing information by VDC
        
        No example use discovered in the iland console.
        """
        return Report(self.api.get(f"/orgs/{uuid}/billing-by-vdc"))

    def get_org_billing_historical(self, uuid: str, start: datetime.date, end: datetime.date) -> Report:
        """Returns a series of historical monthly org costs

        The console pulls the last 5 months to use in the montly bar graph on the billing tab:
        https://console.ilandcloud.com/api/v1/orgs/{uuid}/historical-billing?start=1624027630654&end=1637250430654
        """
        start_timestamp = int(time.mktime(start.timetuple())) * 1000
        end_timestamp = int(time.mktime(end.timetuple())) * 1000
        parameters = f"start={start_timestamp}&end={end_timestamp}"
        return Report(self.api.get(f"/orgs/{uuid}/historical-billing?{parameters}"))


    def get_org_billing_historical_vdc(self, uuid: str, start: datetime.date, end: datetime.date) -> Report:
        """Returns the historical billing data by VDC
        
        The console uses historical-billing-by-vdc to build the historical billing bar graphs.
        https://console.ilandcloud.com/api/v1/orgs/{uuid}/historical-billing-by-vdc?startMonth=7&startYear=2021&endMonth=11&endYear=2021
        """
        parameters = f"startYear={start.year}&startMonth={start.month}&endYear={end.year}&endMonth={end.month}"
        return Report(self.api.get(f"/orgs/{uuid}/historical-billing-by-vdc?{parameters}"))

    def get_o365_billing(self, company: str, location: str, start: datetime.date, end: datetime.date) -> Report:
        """Returns the O365 billing for a location
        
        Get company from: ilandinfo inventory company
        Get location from: ilandinfo inventory o365-org; Sub-string of UUID before the first ":"

        Console example:
        https://console.ilandcloud.com/api/v1/companies/{company}/location/lon02.ilandcloud.com/o365-billing?startYear=2021&startMonth=9&endYear=2021&endMonth=11
        """
        parameters = f"startYear={start.year}&startMonth={start.month}&endYear={end.year}&endMonth={end.month}"
        return Report(self.api.get(f"/companies/{company}/location/{location}/o365-billing?{parameters}"))

    # vdcs-cost-over-invoice-period ? year, month
    # Returns a time series (1 hour increments) of VDCs sum costs for the VDC Cost Accrual Breakdown graph
    # https://console.ilandcloud.com/api/v1/orgs/{uuid}/vdcs-cost-over-invoice-period?year={YYYY}&month={MM}

def get_args() -> argparse.Namespace:
    """ Setup the argument parser and parse the arguments.

        ilandinfo inventory <object>
        ilandinfo billing <service>
        
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
            'o365',
            'org',
            'org-by-vdc',
            'org-summary',
            'org-historical',
            'org-historical-by-vdc',
            'vapp',
            'vdc',
            'vm',
            'vm-summary'
        ]
    )
    billing_parser.add_argument(
        '--uuid',
        type=str,
        help='service UUID to report on'
    )
    billing_parser.add_argument(
        '--start',
        type=str,
        help='start date in YYYY-MM-DD format'
    )
    billing_parser.add_argument(
        '--end',
        type=str,
        help='end date in YYYY-MM-DD format'
    )
    billing_parser.add_argument(
        '--date',
        type=str,
        help='date in YYYY-MM-DD format'
    )
    billing_parser.add_argument(
        '--company',
        type=str,
        help='company number'
    )
    billing_parser.add_argument(
        '--location',
        type=str,
        help='location in LLL##.ilandcloud.com format'
    )

    return parser.parse_args()

def get_credentials(credentials_file: str) -> dict:
    """Open the JSON format credentials file and import the credentials."""
    with open(credentials_file, 'r') as file:
        credentials = json.load(file)
    return credentials

def parse_date(date_string: str) -> datetime.date:
    """Take a string with the format YYYY-MM-DD and return a datetime.date"""
    try:
        time_struct = datetime.date.fromisoformat(date_string)
    except ValueError:
        sys.exit('Incorrect date format. Correct format is YYYY-MM-DD.\n  \
            YYYY is the four-digit year.\n  \
            MM is the two-digit month.\n  \
            DD is the two-digit day.')

    return time_struct

def check_required_arguments(args: argparse.Namespace, *arguments) -> None:
    """Send an error if required optional arguments are not provided."""
    missing_arguments = []
    print(vars(args))
    for argument in arguments:
        if not vars(args)[argument]:
            missing_arguments.append(f"--{argument}")

    if missing_arguments:
        sys.exit(f'Missing arguments. {args.command} {args.service} requires: {" ,".join(missing_arguments)}')

def main() -> None:
    args = get_args()
    credentials = get_credentials(args.credentials_file)
    client = Client(credentials)

    # Set iland logger level to WARNING to reduce noise
    iland.log.LOG.setLevel(logging.WARNING)

    if args.command == 'inventory':
        inventory = client.get_inventory()
        inventory.csv_list_object(args.object)

    if args.command == 'billing':
        if args.service == 'org':
            check_required_arguments('uuid')
            if args.date:
                date = parse_date(args.date)
            else:
                date = datetime.date.today()
            report = client.get_org_billing(args.uuid, date)
        elif args.service == 'org-by-vdc':
            check_required_arguments(args, 'uuid')
            report = client.get_org_billing_by_vdc(args.uuid)
        elif args.service == 'org-summary':
            check_required_arguments(args, 'uuid')
            report = client.get_org_billing_summary(args.uuid)
        elif args.service == 'org-historical':
            check_required_arguments(args, 'start', 'end')
            start = parse_date(args.start)
            end = parse_date(args.end)
            report = client.get_org_billing_historical(args.uuid, start, end)
        elif args.service == 'org-historical-by-vdc':
            check_required_arguments(args, 'start', 'end')
            start = parse_date(args.start)
            end = parse_date(args.end)
            report = client.get_org_billing_historical_vdc(args.uuid, start, end)
        elif args.service== 'o365':
            check_required_arguments(args, 'company', 'location')
            if args.start and args.end:
                start = parse_date(args.start)
                end = parse_date(args.end)
            else:
                end = datetime.date.today()
                start = end + relativedelta(months=-6)

        report = client.get_o365_billing(args.company, args.location, start, end)

        print(report)

if __name__ == '__main__':
    main()
