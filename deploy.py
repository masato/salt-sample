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

PATH='/client/api'
SSH_IF='private_ips'
SALT_NODES=['salt','minion1','minion2']
IMAGE_NAME=r'Ubuntu Server 14.04'
SIZE_NAME='light.S1'

class Salt(object):

    def __init__(self):
        self.cls = get_driver(Provider.CLOUDSTACK)
        self.create_driver()
        self.default_offering()
        self.list_nodes()

    def create_driver(self):
        access_key = os.environ.get('IDCF_COMPUTE_API_KEY')
        secret_key = os.environ.get('IDCF_COMPUTE_SECRET_KEY')
        host = os.environ.get('IDCF_COMPUTE_HOST')
        self.ssh_key_file = os.environ.get('IDCF_SSH_KEY_FILE')

        if not access_key:
            print_exit('IDCF_COMPUTE_API_KEY')
        if not secret_key:
            print_exit('IDCF_COMPUTE_SECRET_KEY')
        if not host:
            print_exit('IDCF_COMPUTE_HOST')
        try:
            self.ssh_key = os.path.join(
                os.path.expanduser('~'),
                '.ssh',
                self.ssh_key_file)
        except:
            print_exit('IDCF_SSH_KEY_FILE')

        if not os.path.exists(self.ssh_key):
            print_exit('{0} is not found'.format(self.ssh_key))

        self.driver = self.cls(key=access_key,
                               secret=secret_key,
                               host=host,
                               path=PATH)

    def default_offering(self):
        p = re.compile(IMAGE_NAME)
        self.image = [i for i in self.driver.list_images()
                        if p.match(i.name)][0]
        self.size = [s for s in self.driver.list_sizes()
                        if s.name == SIZE_NAME][0]
        keynames = [k for k in self.driver.list_key_pairs()
                        if k.name == self.ssh_key_file]
        if len(keynames) > 0:
            self.keyname = keynames[0].name
        else:
            print('{0} key name does not exisit in cloud'.format(self.ssh_key_file))
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
                print('{0} already exists, please destroy this vm beforehand'.format(n.name))
                sys.exit(1)

    def deploy(self,name,bootstrap):
        self.exit_if_vm_exists()
        start = time.time()
        print('start {0}'.format(name))
        script = ScriptDeployment(bootstrap)
        msd = MultiStepDeployment([script])
        node = self.driver.deploy_node(name=name,
                                  image=self.image,
                                  size=self.size,
                                  ssh_key=self.ssh_key,
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
    command = args.command
    if command == 'deploy':
        salt.deploy('salt',master_bootstrap)
        for i in range(1, 3):
            name = 'minion{0}'.format(i)
            salt.deploy(name,minion_bootstrap)
    elif command == 'list':
        salt.print_nodes()
    else:
        print 'env does not exists: {0}'.format(args.env)
        sys.exit(1)

def parse_arguments():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("command",type=str,help="Simple Salt Command",
                        default='list', 
                        choices=["deploy","list"])
    args = parser.parse_args()
    return args

def main():
    args = parse_arguments()
    action(args)

def print_exit(msg):
    print('please set {0} in your environment'.format(msg))
    sys.exit(1)

if __name__ == "__main__":
    main()
