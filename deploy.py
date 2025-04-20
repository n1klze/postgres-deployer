#!/usr/bin/env python3
import sys
import subprocess


SSH_USER = 'root'
SSH_KEY  = '~/.ssh/id_rsa'


class PostgresDeployer:
    def __init__(self, servers):
        self.servers = servers

    def create_inventory(self):
        with open('./ansible/hosts.ini', 'w') as hosts:
            hosts.write('[servers]\n')
            for server in self.servers:
                hosts.write(
                    f'{server} ansible_host={server} ansible_user={SSH_USER} '
                    f'ansible_ssh_private_key_file={SSH_KEY}\n'
                )
        return 'ansible/hosts.ini'

    def select_target_server(self, inventory_file):
        cmd = [
            'ansible', '-i', inventory_file, 'servers',
            '-m', 'shell',
            '-a', 'cat /proc/loadavg | awk \'{print $1}\'',
            '--one-line'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(result.stderr)
        
        loads = {}
        for line in result.stdout.split('\n'):
            if not line.strip():
                continue
            host = line.split()[0].strip()
            load = float(line.split()[-1].strip())
            loads[host] = load
            print(f'Server: {host}\tload: {load}')

        return min(loads, key=lambda e: loads[e])
    
    def run_ansible_playbook(self, inventory_file, target_server, other_server):    
        cmd = [
            'ansible-playbook', '-i', inventory_file,
            './ansible/playbook.yml',
            '--extra-vars', f'target_server={target_server}  other_server_ip={other_server}',
            '-v'
        ]

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                 universal_newlines=True)
        for line in process.stdout:
            print(line.strip())
        process.wait()
        if process.returncode != 0:
            raise Exception(f'Playbook execution error: {process.stderr.read()}')

    def run(self):
        if len(self.servers) < 2:
            raise Exception('You need to use at least 2 servers')

        inventory_file = self.create_inventory()
        print(f'Inventory file created: {inventory_file}')

        print('Getting information about load on servers...')
        target_server = self.select_target_server(inventory_file)
        other_server = next(s for s in self.servers if s != target_server)
        print('Target server is: ', target_server)

        self.run_ansible_playbook(inventory_file, target_server, other_server)
        print('Deployment completed successfully.')
        print(f'PostgreSQL installed on {target_server}')
        print(f"User 'student' can only connect from {other_server}")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python deploy.py <server1, server2>')
        sys.exit(1)

    servers = [s.strip() for s in sys.argv[1].split(',')]
    try:
        deployer = PostgresDeployer(servers)
        deployer.run()
    except Exception as e:
        print(e)
        sys.exit(1)
