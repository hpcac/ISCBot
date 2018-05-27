|img_isc| |img_hpcac|



ISC Bot
======= 
Bot for power monitoring of the HPCAC SCC of the ISC events.
It can show current and peak power values, sends notifications in case of a team exceeds the power limit and can reset the actual peak power values on certain PDUs.

Version: 1.2

Getting Started
===============
For running the Bot, no installation is necessary.
Just clone this repository using ``git clone https://github.com/JanLJL/Telegram_Bots`` and go to the ``ISCBot`` directory.

Dependencies
~~~~~~~~~~~
Additional requirements are:

-  `Net-SNMP <http://www.net-snmp.org/>`_
-  `ELinks <http://elinks.or.cz/>`_
-  `Python3 <https://www.python.org/>`_
-  `Pexpect <https://github.com/pexpect/pexpect>`_
-  `python-telegram-bot <https://github.com/python-telegram-bot/python-telegram-bot>`_

Configuration
~~~~~~~~~~~~~
There are two configurable files in the ISCBot directory that one has to customize.

``accesslist.conf``
  This file contains all user `chat_id`s that going to have access to the reset functions.
  If the first `chat_id` is a `group_id`, all members of this group have access to the functions.
  Comment lines can be inserted via '``#``'.
  Example access list::

    # ACCESS LIST FOR THE CHAT_IDs FOR ALL GROUP MEMBER
    -123456789    # <-- This is our group_id
    424242424     # <-- chat_id of users which are allowed
    133742241     #     to communicate in private chats
    
  If you do not know the ``chat_id`` for a certain user, the ID will be shown as terminal output of the host 
  while the user is trying to access a restricted function.
  You then can copy the ``chat_id`` to your access list.
   
``ips.csv``
  This file contains all PDUs for monitoring and resetting.
  Each line shows the last 3 digits of the ip address and the name of the associated team.
  Only lines in form of `NUM,NAME` are allowed.
  Example (let's say we have 3 PDUs in the range of 192.168.1.101 to 192.168.1.103)::
  
    101, Name_of_PDU
    102, Second_PDU
    103, Something completely different

Usage
=====

Host
~~~~
As the host of the bot, just type ``./iscbot.py`` in the ``ISCBot/iscbot`` directory to initialize the bot.
You will get asked for the password for the PDU super user to be able to reset the peak power values.

Client
~~~~~~
As a client, you can either communicate with the bot in a group or a single chat. Mind that in a group
the ISCBot is only able to listen to commands starting with '``/``'.

| **First Use**

If you never interacted with the bot before, search in the Telegram search field for

::
  
  @ISC_PDU_Bot
  
and type ``/start`` for starting a conversation.

| **Commands**

``/current``
  Sends a list of the current power usage for each team.
  
``/peaks``
  Sends a list of the peak power for each team.
  
``/reset``
  ``@restricted``
  
  Resets PDU's peak power value specified by a given IP.
  After starting the command, please answer to the bot asking you for the IP address of the PDU to reset by
  sending the last 3 digits of the IP address.
  
``/help``
  Prints out help.
  
Snooping
~~~~~~~~
In the background the bot checks every 2 seconds for a team exceeding the power limit.
If so, the peak power value, the PDU name and a timestamp will be send via message to a specific group of users.
We propose either to send push notifications to the assigned group or to all users included in the access list.
Both variants are implement in the source code, by default the bot sends the notification to all access list users.
Additionally, all limit exceedings will be logged in the file ``exceedings.log``.

Credits
=======
**Implementation**: Jan Laukemann

**Images**

-  ISC logo: |copy| 2018 Prometeus GmbH
-  HPCAC logo: |copy| 2018 HPC Advisory Council

License
=======
`AGPL-3.0 </LICENSE>`_


.. |copy| unicode:: 0xA9 .. copyright sign

.. |img_isc| raw:: html

    <a href="https://www.isc-hpc.com/"><img src="docs/ISC-logo.png" width="45%" align="left" alt="ISC logo">
    
.. |img_hpcac| raw:: html

    <a href="http://hpcadvisorycouncil.com/"><img src="docs/hpcac-logo.png" width="40%" align="right" alt="HPCAC logo">
    <br clear="all" />
    
