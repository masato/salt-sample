#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.compute.deployment import ScriptDeployment
from libcloud.compute.deployment import MultiStepDeployment

import os,sys
import time
import re
import argparse
import paramiko
paramiko.util.log_to_file("salt.log")

ACCESS_KEY=os.environ.get('IDCF_COMPUTE_API_KEY')
SECRET_KEY=os.environ.get('IDCF_COMPUTE_SECRET_KEY')
HOST=os.environ.get('IDCF_COMPUTE_HOST')
PATH='/client/api'
SSH_KEY_FILE=os.environ.get('IDCF_SSH_KEY_FILE')

SSH_IF='private_ips'

SALT_NODES=['salt','minion1','minion2']
IMAGE_NAME=r'Ubuntu Server 14.04'
SIZE_NAME='light.S1'

class Salt(object):

    def __init__(self):
        self.cls = get_driver(Provider.CLOUDSTACK)
        self.driver = self.cls(key=ACCESS_KEY,
                               secret=SECRET_KEY,
                               host=HOST,
                               path=PATH)
        self.default_offering()
        self.list_nodes()
        self.exit_if_vm_exists()

    def default_offering(self):
        p = re.compile(IMAGE_NAME)
        self.image = [i for i in self.driver.list_images()
                        if p.match(i.name)][0]
        self.size = [s for s in self.driver.list_sizes()
                        if s.name == SIZE_NAME][0]
        keynames = [k for k in self.driver.list_key_pairs()
                        if k.name == SSH_KEY_FILE]
        if len(keynames) > 0:
            self.keyname = keynames[0].name
        else:
            print('{0} key name does not exisit in cloud'.format(SSH_KEY_FILE))
            exit(1)

    def list_nodes(self):
        self.nodes = self.driver.list_nodes()

    def print_nodes(self):
        if len(self.nodes) < 1:
            print('nodes not found')
        for n in self.nodes:
            print('{0}'.format(n.name))

    def exit_if_vm_exists(self):
        for n in self.nodes:
            if n.name in SALT_NODES:
                print('{0} already exists, please destroy this vm beforehand')
                sys.exit(1)

    def destroy(self,name):
        for n in self.nodes:
            if name == n.name and n.name in SALT_NODES:
                retval = self.driver.destroy_node(n)
                print('{0} is destoyed: {1}'.format(name,retval))

    def deploy(self,name,bootstrap):
        start = time.time()
        print('start {0}'.format(name))
        script = ScriptDeployment(bootstrap)
        msd = MultiStepDeployment([script])
        node = self.driver.deploy_node(name=name,
                                  image=self.image,
                                  size=self.size,
                                  ssh_key=SSH_KEY_FILE,
                                  ex_keyname=self.keyname,
                                  ssh_interface=SSH_IF,
                                  deploy=msd)
        end = time.time()
        elapsed = end - start
        print('end {0}, eplapsed: {1}'.format(name,elapsed))


def action(args):

    master_bootstrap = '''#!/bin/bash
curl -L http://bootstrap.saltstack.com | sh -s -- -M
'''
    minion_bootstrap = '''#!/bin/bash
curl -L http://bootstrap.saltstack.com | sh
'''
    salt = Salt()
    command = args.command[0]
    if command == 'deploy':
        salt.deploy('salt',master_bootstrap)
        for i in range(1, 3):
            name = 'minion{0}'.format(i)
            salt.deploy(name,minion_bootstrap)
    elif command == 'list':
        salt.print_nodes()
    elif command == 'destroy':
        salt.destroy(command[1])
    else:
        print 'env does not exists: {0}'.format(args.env)
        sys.exit(1)

def parse_arguments():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("command",type=str,help="Simple Salt Command",
                        default='list', nargs='+',
                        choices=["deploy","destroy","list"])
    args = parser.parse_args()
    return args

def main():
    args = parse_arguments()
    action(args)

def print_exit(msg):
    print('please set {0} in your environment'.format(msg))
    sys.exit(1)

def check_environments():
    if not ACCESS_KEY:
        print_exit('IDCF_COMPUTE_API_KEY')
    if not SECRET_KEY:
        print_exit('IDCF_COMPUTE_SECRET_KEY')
    if not HOST:
        print_exit('IDCF_COMPUTE_HOST')
        print_exit('IDCF_SSH_KEY_FILE')
    try:
        ssh_key_file=os.path.join(
            os.path.expanduser('~'),
            '.ssh',
            SSH_KEY_FILE)
        if not os.path.exists(ssh_key_file):
            print_exit('{0} is not found'.format(ssh_key_file))
    except:
        print_exit('IDCF_SSH_KEY_FILE')
        
if __name__ == "__main__":
    check_environments()
    main()
