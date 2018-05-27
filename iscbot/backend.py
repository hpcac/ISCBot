#!/usr/bin/env python3

import getpass
import sys
import time
from datetime import datetime
from subprocess import Popen, PIPE

from pexpect import spawn

class Backend(object):

    ips = []
    teams = {}
    team_peaks = {}
    lngst_name = 0

    K_UP = '\x1b[A'
    K_DOWN = '\x1b[B'
    # power value stored as tenth of actual value, e.g. 3kW means 300
    LIMIT = 300
    # Password is set during initialization
    pwd = None
    
    def __init__(self):
        print('Initialize backend')
        # Get password for Rack PDU for the duration of the runtime
        self.pwd = getpass.getpass(prompt='Password for user \'apc\': ')
        # Read in the IPs and team names
        with open('ips.csv', 'r') as f:
            for line in f:
                ip,name = line.rstrip().split(',')
                ip = int(ip)
                self.ips.append(ip)
                self.teams[ip] = name.lstrip()
                self.team_peaks[ip] = 0
                if(len(name) > self.lngst_name):
                    self.lngst_name = len(name)
        print('Successfully read in IP addresses!')

    
    def current(self):
        """
        Reads out the current power for each team and returns everything as a string 
        including a timestamp of the request.

        Returns
        -------
        string
            All current power values 
        """
        out = datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'\nCurrent power values:\n'
        for ip in self.ips:
            sn = ['snmpget', '-v', '2c', '-c', 'public', '192.168.1.'+str(ip)+':161', 
                  '.1.3.6.1.4.1.318.1.1.26.6.3.1.7.1']
            p = Popen(sn, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            output, err = p.communicate(b'input data that is passed to stdin of subprocess')
            rc = p.returncode
            power = int(str(output).split(':')[-1][1:-3])*10
            out += '{}(.{}): {} W\n'.format(self.teams[ip].ljust(self.lngst_name),
                                            ip, power)
        return out

    def peaks(self):
        """
        Reads out the current peak power values for each team and returns everything as a
        string including a timestamp of the request.

        Returns
        -------
        string
            All current peak power values
        """
        out = datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'\nPeak power values:\n'
        for ip in self.ips:
            sn = ['snmpget', '-v', '2c', '-c', 'public', '192.168.1.'+str(ip)+':161', 
                  '.1.3.6.1.4.1.318.1.1.26.4.3.1.6.1']
            p = Popen(sn, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            output, err = p.communicate(b'input data that is passed to stdin of subprocess')
            rc = p.returncode
            power = int(str(output).split(':')[-1][1:-3])*10
            out += '{}(.{}): {} W\n'.format(self.teams[ip].ljust(self.lngst_name),
                                            ip, power)
        return out

    def check_exceedings(self):
        """
        Snoops all current peak power values, checks against exceeding and returns list of them.
        Returns an empty list if every team is inside the power limit.

        Returns
        -------
        [(string), ...]
            List of strings with IP and peak value for each exceeder
        """
        exceeders = []
        for ip in self.ips:
            sn = ['snmpget', '-v', '2c', '-c', 'public', '192.168.1.'+str(ip)+':161',
                  '.1.3.6.1.4.1.318.1.1.26.4.3.1.6.1']
            p = Popen(sn, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            output, err = p.communicate(b'input data that is passed to stdin of subprocess')
            rc = p.returncode
            peak = int(str(output).split(':')[-1][1:-3])
            if(peak > self.LIMIT and self.team_peaks[ip] < self.LIMIT):
                self.team_peaks[ip] = peak
                exceeders.append('{}(.{}):\nAbove power limit ({} W)!'.format(
                                 self.teams[ip], ip, peak*10))
        return exceeders

    def reset(self, ip):
        """
        Resets peak power value of certain PDU given by ip.

        Parameters
        ----------
        ip : int
            last three digits of IP address for the PDU to reset

        Returns
        -------
        bool
            True    if resetting was successful
            False   if pexpect.TIMOUT appeared
        """
        print('Start...', end='', flush=True)
        # Start ELinks
        try:
            child = spawn('elinks 192.168.1.' + str(ip))
            print('wait to establish connection...', end='')
            child.expect('Log On', timeout=10)
            # Open PDU connection and navigate to Configurations -> Device
            time.sleep(1)
            child.sendline(self.K_DOWN)
            child.send('apc')
            child.sendline(self.K_DOWN)
            child.sendline(self.pwd)
            child.sendline('')
            child.expect('Rack PDU 2G', timeout=10)
            time.sleep(1)
            print('Logged in...', end='', flush=True)
            child.sendline('/Device')
            child.sendline('n')
            child.expect('Rack PDU 2G', timeout=10)
            time.sleep(1)
            print('Reseting...', end='', flush=True)
            # Reset PDU peak power
            child.sendline('/Reset (last')
            child.send(self.K_DOWN * 20)
            child.sendline(self.K_UP * 7)
            child.sendline(self.K_DOWN * 2)
            child.sendline('')
            child.expect('Rack PDU 2G', timeout=10)
            time.sleep(4.5)
            # Log off
            child.sendline(self.K_DOWN * 2)
            child.expect('You are now logged off', timeout=10)
            time.sleep(1)
            child.sendline('')
            print('Done!', flush=False)
            # End ELinks
            child.sendline('q')
            child.kill(0)
            
            self.team_peaks[ip] = 0
            print('PDU of '+self.teams[ip]+' successfully reset!')
        except pexpect.TIMEOUT:
            print('Expect Timeout reached. Reset probably did not finish.', 
                  file=sys.stderr, flush=False)
            if(not child.terminate()):
                print('Could not terminate child regularly.', file=sys.stderr)
                child.terminate(force=True)
            return False
        return True
