#!/usr/bin/env python3

import getpass
import sys
import time
from datetime import datetime
import subprocess
from subprocess import PIPE, STDOUT

import pexpect
from pexpect import spawn


class Backend(object):

    ips = []
    ip_dict = {}
    teams = {}
    team_peaks = {}
    lngst_name = 0
    bot = None

    K_UP = "\x1b[A"
    K_DOWN = "\x1b[B"
    oid_current = ".1.3.6.1.4.1.318.1.1.26.6.3.1.7.1"
    oid_peak = ".1.3.6.1.4.1.318.1.1.26.4.3.1.6.1"
    oid_peak_timestamp = ".1.3.6.1.4.1.318.1.1.26.4.3.1.7.1"
    oid_peak_reset = ".1.3.6.1.4.1.318.1.1.26.4.1.1.10.1"
    oid_peak_reset_type = "i"
    oid_peak_reset_val = "2"
    snmp_timeout = "0.5"
    # threshold power in Watt
    LIMIT = 6000
    # Password is set during initialization
    pwd = None
    snmpv3_auth_pass = None
    snmpv3_priv_pass = None

    def __init__(self, bot=None):
        print("Initialize backend")
        # Get password for Rack PDU for the duration of the runtime
        self.snmpv3_auth_pass = getpass.getpass(
            prompt="Enter SNMPv3 authentication passphrase for user 'apc': "
        )
        self.snmpv3_priv_pass = getpass.getpass(
            prompt="Enter SNMPv3 privacy passphrase for user 'apc': "
        )
        # if empty, set the same for privacy and authentication passphrase
        if len(self.snmpv3_priv_pass) == 0:
            self.snmpv3_priv_pass = self.snmpv3_auth_pass
        self.bot = bot
        # Read in the IPs and team names
        with open("ips.csv", "r") as f:
            for line in f:
                ip, name, team = line.rstrip().split(",")
                ip = int(ip)
                self.ips.append(ip)
                if self.teams.get(team):
                    self.teams[team][ip] = name.strip()
                else:
                    self.teams[team] = {ip: name.strip()}
                self.ip_dict[ip] = team
                self.team_peaks[team] = 0
                if len(team) > self.lngst_name:
                    self.lngst_name = len(team)
        print("Successfully read in IP addresses!")

    def current(self):
        """
        Reads out the current power for each team and returns everything as a string
        including a timestamp of the request.

        Returns
        -------
        string
            All current power values
        """
        out = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\nCurrent power values:\n"
        for team in sorted(self.teams.keys()):
            team_power = 0
            ip_list = ", ".join([str(ip) for ip in self.teams[team].keys()])
            for ip in self.teams[team].keys():
                sn = [
                    "snmpget",
                    "-v2c",
                    "-t",
                    self.snmp_timeout,
                    "-cpublic",
                    "192.168.1." + str(ip),
                    self.oid_current,
                ]
                res = subprocess.run(sn, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
                if res.returncode != 0:
                    print(
                        "Could not read current power from " + str(team) + "(" + str(ip) + ").",
                        file=sys.stderr,
                    )
                    team_power = -1
                    break
                else:
                    team_power += (
                        int(res.stdout.decode("utf-8").replace("\n", "").split(":")[-1]) * 10
                    )
            out += "{}({}): {} W\n".format(team.ljust(self.lngst_name), ip_list, team_power)
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
        out = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\nPeak power values:\n"
        for team in sorted(self.teams.keys()):
            team_peak = 0
            ip_list = ", ".join([str(ip) for ip in self.teams[team].keys()])
            for ip in self.teams[team].keys():
                sn = [
                    "snmpget",
                    "-v2c",
                    "-t",
                    self.snmp_timeout,
                    "-cpublic",
                    "192.168.1." + str(ip),
                    self.oid_peak,
                ]
                res = subprocess.run(sn, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
                if res.returncode != 0:
                    print(
                        "Could not read peak power from " + str(team) + "(" + str(ip) + ").",
                        file=sys.stderr,
                    )
                    team_peak = -1
                    break
                else:
                    team_peak += (
                        int(res.stdout.decode("utf-8").replace("\n", "").split(":")[-1]) * 10
                    )
            out += "{}({}): {} W\n".format(team.ljust(self.lngst_name), ip_list, team_peak)
        return out

    def peak_dates(self):
        """
        Reads out the current peak power values together with the timestamp when the peak was
        reached for each team and returns everything as a string including the current date.

        Returns
        -------
        string
            All current peak power values with corresponding timestamps
        """
        out = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\nPeak power values:\n"
        for team in sorted(self.teams.keys()):
            team_peak = 0
            ip_list = ", ".join([str(ip) for ip in self.teams[team].keys()])
            for ip in self.teams[team].keys():
                sn = [
                    "snmpget",
                    "-v2c",
                    "-t",
                    self.snmp_timeout,
                    "-cpublic",
                    "192.168.1." + str(ip),
                    self.oid_peak,
                ]
                sn_time = [
                    "snmpget",
                    "-v2c",
                    "-t",
                    self.snmp_timeout,
                    "-cpublic",
                    "192.168.1." + str(ip),
                    self.oid_peak_timestamp,
                ]
                res = subprocess.run(sn, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
                res_timestamp = subprocess.run(sn_time, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
                if res.returncode != 0 or res_timestamp.returncode != 0:
                    print(
                        "Could not read peak power or timestamp from "
                        + str(team)
                        + "("
                        + str(ip)
                        + ").",
                        file=sys.stderr,
                    )
                    team_peak = -1
                    break
                else:
                    team_peak += (
                        int(res.stdout.decode("utf-8").replace("\n", "").split(":")[-1]) * 10
                    )
                    date = res_timestamp.stdout.decode("utf-8").split('"')[1]
            out += "{}({}): {} W\n    {}\n".format(
                team.ljust(self.lngst_name), ip_list, team_peak, date
            )
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
        not_reachable = []
        for team in sorted(self.teams.keys()):
            team_peak = 0
            ip_list = ", ".join([str(ip) for ip in self.teams[team].keys()])
            for ip in self.teams[team].keys():
                sn = [
                    "snmpget",
                    "-v2c",
                    "-t",
                    self.snmp_timeout,
                    "-cpublic",
                    "192.168.1." + str(ip),
                    self.oid_peak,
                ]
                res = subprocess.run(sn, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
                if res.returncode != 0:
                    print(
                        "Could not read peak power from " + str(team) + "(" + str(ip) + ").",
                        file=sys.stderr,
                    )
                    team_peak = -1
                    not_reachable.append("{}({}):\nPDU not reachable!".format(team, ip))
                    break
                else:
                    team_peak += (
                        int(res.stdout.decode("utf-8").replace("\n", "").split(":")[-1]) * 10
                    )
            if team_peak > self.LIMIT and self.team_peaks[team] < self.LIMIT:
                self.team_peaks[team] = team_peak
                exceeders.append(
                    "{}({}):\nAbove power limit ({} W)!".format(team, ip_list, team_peak)
                )
        return (exceeders, not_reachable)

    async def reset_elinks(self, team, context=None, progress_msg=None):
        """
        Resets peak power value of certain PDU given by ip.

        Parameters
        ----------
        ip : int
            last three digits of IP address for the PDU to reset
        context : telegram.Context
            context for identifying the bot
        progress_msg : telegram.Message
            message to be updated during the reset process

        Returns
        -------
        bool
            True    if resetting was successful
            False   if pexpect.TIMOUT appeared
        """
        progress_bar = "`\|\=          \|`\n"
        for ip in sorted(self.teams[team].keys()):
            print("Start...", end="", flush=True)
            # Start ELinks
            try:
                child = spawn("elinks 192.168.1." + str(ip))
                print("wait to establish connection to {}...".format(ip), end="")
                if progress_msg != None:
                    progress_bar = progress_bar.replace("= ", "=\=")
                    progress_txt = "Wait to establish connection to PDU\.\.\."
                    await self.bot.edit_message_text_wrapper(
                        context.bot,
                        progress_msg.chat_id,
                        progress_msg.message_id,
                        progress_bar + progress_txt,
                        parse_mode="md",
                    )
                child.expect("Log On", timeout=10)
                # Open PDU connection and navigate to Configurations -> Device
                time.sleep(1)
                child.sendline(self.K_DOWN)
                child.send("apc")
                child.sendline(self.K_DOWN)
                child.sendline(self.pwd)
                child.sendline("")
                child.expect("Rack PDU 2G", timeout=10)
                time.sleep(1)
                print("Logged in...", end="", flush=True)
                if progress_msg != None:
                    progress_bar = progress_bar.replace("= ", "=\=")
                    progress_txt = "Logged in"
                    await self.bot.edit_message_text_wrapper(
                        context.bot,
                        progress_msg.chat_id,
                        progress_msg.message_id,
                        progress_bar + progress_txt,
                        parse_mode="md",
                    )
                child.send("/")
                child.sendline(self.K_DOWN)
                child.send(self.K_UP)
                child.sendline("Device")
                child.sendline("n")
                child.expect("Rack PDU 2G", timeout=10)
                time.sleep(1)
                print("Resetting...", end="", flush=True)
                if progress_msg != None:
                    progress_bar = progress_bar.replace("= ", "=\=")
                    progress_txt = "Resetting PDU\.\.\."
                    await self.bot.edit_message_text_wrapper(
                        context.bot,
                        progress_msg.chat_id,
                        progress_msg.message_id,
                        progress_bar + progress_txt,
                        parse_mode="md",
                    )
                # Reset PDU peak power
                child.sendline("/Reset (")
                child.send(self.K_DOWN * 20)
                child.sendline(self.K_UP * 7)
                child.sendline(self.K_DOWN * 2)
                child.sendline("")
                child.expect("Rack PDU 2G", timeout=12)
                time.sleep(8)
                # Log off
                print("Disconnecting...", end="", flush=True)
                if progress_msg != None:
                    progress_bar = progress_bar.replace("= ", "=\=")
                    progress_txt = "Disconnecting from PDU\.\.\."
                    await self.bot.edit_message_text_wrapper(
                        context.bot,
                        progress_msg.chat_id,
                        progress_msg.message_id,
                        progress_bar + progress_txt,
                        parse_mode="md",
                    )
                child.sendline(self.K_DOWN * 2)
                # child.expect('You are now logged off', timeout=20)
                time.sleep(1)
                child.sendline("")
                print("Done!", flush=False)
                if progress_msg != None:
                    progress_bar = progress_bar.replace("= ", "=\=")
                    progress_txt = "Done"
                    await self.bot.edit_message_text_wrapper(
                        context.bot,
                        progress_msg.chat_id,
                        progress_msg.message_id,
                        progress_bar + progress_txt,
                        parse_mode="md",
                    )
                # End ELinks
                child.sendline("q")
                child.kill(0)

                self.team_peaks[team] = 0
                print("PDU of " + team + " (" + str(ip) + ") successfully reset!")
            except pexpect.TIMEOUT:
                # print('Expect Timeout reached for '+self.teams[team]+'('+str(ip)+'). Reset '
                print(
                    "Expect Timeout reached for "
                    + str(team)
                    + "("
                    + str(ip)
                    + "). Reset "
                    + "may  not be finished.",
                    file=sys.stderr,
                    flush=False,
                )
                if not child.terminate():
                    print("Could not terminate child regularly.", file=sys.stderr)
                    child.terminate(force=True)
                return False
        return True

    async def reset(self, team, context=None, progress_msg=None):
        """
        Resets peak power value of certain PDU given by ip.

        Parameters
        ----------
        ip : int
            last three digits of IP address for the PDU to reset
        context : telegram.Context
            context for identifying the bot
        progress_msg : telegram.Message
            message to be updated during the reset process

        Returns
        -------
        bool
            True    if resetting was successful
            False   if pexpect.TIMEOUT appeared
        """
        error = False
        for ip in sorted(self.teams[team].keys()):
            sn = [
                "snmpset",
                "-v3",
                "-u",
                "apc",
                "-lAuthPriv",
                "-aSHA",
                "-A",
                self.snmpv3_auth_pass,
                "-xAES",
                "-X",
                self.snmpv3_priv_pass,
                "192.168.1." + str(ip),
                ".1.3.6.1.4.1.318.1.1.26.4.1.1.10.1",
                "i",
                "2",
            ]
            res = subprocess.run(sn, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
            if res.returncode != 0:
                print(
                    "Could not succesfully reset " + str(team) + "(" + str(ip) + ").",
                    file=sys.stderr,
                )
                error = True
                break
            progress_txt = "Done"
            await self.bot.edit_message_text_wrapper(
                context.bot,
                progress_msg.chat_id,
                progress_msg.message_id,
                progress_txt,
                parse_mode="md",
            )
        return True if not error else False
