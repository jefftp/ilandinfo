#!/usr/bin/env python3
#
# Copyright 2021 iland Internet Solutions Corporation
#
# Licensed under the 3-Clause BSD License (the "License"). You may not use
# this product except in compliance with the License. A copy of the License
# is located in the file LICENSE.
#

import iland, json, argparse, time, sys

def init_api_client():
    with open('./creds.json', 'r') as f:
        creds = json.load(f)
        return Client(creds['client_id'], creds['client_secret'], creds['username'], creds['password'])

class Client:
    def __init__(self, client_id, client_secret, username, password):
        self.username = username
        self.api = iland.Api(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password)

    def get_entity(self, entity):
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

        inventory = self.api.get(f"/users/{self.username}/inventory")

        api_entity = entity_lookup[entity]
        for company in inventory['inventory']:
            for item in company['entities'][api_entity]:
                items.append(item)
        return items

    def get_vm(self, uuid):
        vm_data = self.api.get(f"/vms/{uuid}")
        return VirtualMachine(self, vm_data)

class VirtualMachine:
    def __init__(self, client, vm_data):
        self.client = client
        self.uuid = vm_data['uuid']
        self.status = vm_data['status']

    def do_action(self, action):
        actions = {
            'power_on': '/vms/{}/actions/poweron',
            'shutdown': '/vms/{}/actions/shutdown',
            'power_off': '/vms/{}/actions/poweroff',
            'reboot': '/vms/{}/actions/reboot',
            'suspend': '/vms/{}/actions/suspend'}

        if action in actions:
            task_data = self.client.api.post(actions[action].format(self.uuid))
            return Task(self.client, task_data)

        sys.exit(f"Error: Virtual Machines do not support the {action} action.")

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

def handle_input(client,args):
    action_objects = {
        'list' : ('company', 'location', 'org', 'vdc', 'vapp', 'vm'),
        'power_on' : ('vm'),
        'shutdown' : ('vm'),
        'power_off' : ('vm'),
        'reboot' : ('vm'),
        'suspend' : ('vm')
    }

    if not (args.object in action_objects[args.action]):
        sys.exit(f"Error: Action {args.action} not supported on object {args.object}.")

    if args.action == 'list':
        if args.object == 'company':
            for company in client.get_entity(args.object):
                print(f"{company['name']}, {company['uuid']}")
        if args.object == 'location':
            for location in client.get_entity(args.object):
                print(f"{location['name']}")
        if args.object == 'org':
            for org in client.get_entity(args.object):
                print(f"{org['name']}, {org['uuid']}")
        if args.object == 'vdc':
            for vdc in client.get_entity(args.object):
                print(f"{vdc['name']}, {vdc['uuid']}")
        if args.object == 'vapp':
            for vapp in client.get_entity(args.object):
                print(f"{vapp['name']}, {vapp['uuid']}")
        if args.object == 'vm':
            for vm in client.get_entity(args.object):
                print(f"{vm['name']}, {vm['uuid']}")

    elif 'vm' in action_objects[args.action]:
        if args.uuid:
            vm = client.get_vm(args.uuid)
            task = vm.do_action(args.action)
            task.watch()
        else:
            sys.exit(f"Error: UUID required to perform action {args.action} on object {args.object}.")
        

if __name__ == '__main__':
    client = init_api_client()

    parser = argparse.ArgumentParser()
    parser.add_argument('action', help='available actions', choices=['list','power_on','shutdown','power_off','reboot', 'suspend'], default=None)
    parser.add_argument('object', help='target object type', choices=['company', 'location','org','vdc','vapp','vm'], default=None)
    parser.add_argument('--uuid', help='target object uuid', default=None, required=False)
    args = parser.parse_args()

    handle_input(client,args)
