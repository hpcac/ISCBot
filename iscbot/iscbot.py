#!/usr/bin/env python3

import logging
from datetime import datetime
from functools import wraps

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import ParseMode, ReplyKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from telegram.ext import CommandHandler, Filters, MessageHandler
from telegram.ext import Updater

from backend import Backend


class ISCBot(object):

    updater = None
    queue = None
    pdus = None
    wait_for_reply = False
    counter = 15
    last_nr = []
    last_msg = {}

    # Chat IDs for permissions
    ISC_grpID = 0
    access_list = []

    def __init__(self):
        print('Initialize frontend')
        # Read in the chat IDs for the access group
        with open('accesslist.conf', 'r') as f:
            for line in f:
                try:
                    tmp_id = int(line.lstrip().split()[0])
                    self.access_list.append(tmp_id)
                except (ValueError, IndexError) as e:
                    continue
        # First item is group ID
        self.ISC_grpID = self.access_list.pop(0)
        print('Successfully read in chat IDs!')

        # Initialize logging
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.INFO)
        # Start backend
        self.pdus = Backend()
        print('Successfully initialized backend!')

        # Start Bot
        self.updater = Updater(token='565616615:AAHeVav01akOO_ox2RLED8jdLqMISLL-Hfc')
        dispatcher = self.updater.dispatcher
        self.queue = self.updater.job_queue

        # Add handler
        start_handler = CommandHandler('start', self.start)
        dispatcher.add_handler(start_handler)

        help_handler = CommandHandler('help', self.get_help)
        dispatcher.add_handler(help_handler)

        #grp_handler = CommandHandler('grp', self.send_group)
        #dispatcher.add_handler(grp_handler)

        curr_power_handler = CommandHandler('current', self.current)
        dispatcher.add_handler(curr_power_handler)

        peak_power_handler = CommandHandler('peaks', self.peaks)
        dispatcher.add_handler(peak_power_handler)

        peak_dates_handler = CommandHandler('peakdates', self.peak_dates)
        dispatcher.add_handler(peak_dates_handler)

        #reset_handler = CommandHandler('reset', self.reset_pdu)
        #dispatcher.add_handler(reset_handler)

        inline_handler = CommandHandler('reset', self.reset_pdu_inline)
        dispatcher.add_handler(inline_handler)

        cbquery_handler = CallbackQueryHandler(self.cb_query)#, pass_groups=True)
        dispatcher.add_handler(cbquery_handler)

        # Unknown commands
        unknw_handler = MessageHandler(Filters.command, self.unknown)
        dispatcher.add_handler(unknw_handler)

    #-------Permission Config--------#
    def restricted(func):
        @wraps(func)
        def wrapped(self, bot, update, *args, **kwargs):
            user_id = update.effective_user.id
            chat_id = update.effective_message.chat.id
            if user_id not in self.access_list and chat_id != self.ISC_grpID:
                print("Unauthorized access denied for {}.".format(user_id))
                return
            return func(self, bot, update, *args, **kwargs)
        return wrapped

    #---------Main functions---------#
    def current(self, bot, update):
        """
        Gets current power usage of all teams from backend and sends it to the user.
        """
        bot.send_message(chat_id=update.message.chat_id, text=self.pdus.current())

    def peaks(self, bot, update):
        """
        Gets the peak power values of all teams from backend and sends it to the user.
        """
        bot.send_message(chat_id=update.message.chat_id, text=self.pdus.peaks())

    def peak_dates(self, bot, update):
        """
        Gets the peak power values of all teams with corresponding timestamps from backend
        and sends it to the user.
        """
        bot.send_message(chat_id=update.message.chat_id, text=self.pdus.peak_dates())

    def check_limits(self, bot, job):
        """
        Gets list of all teams off the power limit from the backend and sends push notifications.
        Possible ways for sending it: a) First user in access list, b) in the group.
        """
        exceeders, not_reachable = self.pdus.check_exceedings()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\n'
        self.counter += 1
        if(len(exceeders) > 0):
            for ex in exceeders:
                print(now + ex)
                #for rcv in self.access_list:
                #    bot.send_message(chat_id=rcv, text=ex)
                bot.send_message(chat_id=self.access_list[0], text=ex)
                #bot.send_message(chat_id=self.access_list[1], text=ex)

                #Additionally, log in file
                with open('exceedings.log', 'a') as f:
                    f.write((now + '--- ' + ex).replace('\n', ' ') + '\n')
        #if(len(not_reachable) > 0 and self.counter > 15 ):
        #    self.counter = 0
        #    for nr in not_reachable:
        #        if(nr in self.last_nr):
        #            self.last_nr.remove(nr)
        #            print(now + nr)
                    #bot.send_message(chat_id=self.access_list[0], text=nr)

                    #Additionally, log in file
        #            with open('exceedings.log', 'a') as f:
        #                f.write((now + '--- ' + nr).replace('\n', ' ') + '\n')
        #        else:
        #            self.last_nr.append(nr)



    @restricted
    def reset_pdu_inline(self, bot, update):
        """
        Resets the peak power of PDU for certain IP address via new inline KeyboardMarkup.
        """
        txt = 'Please choose the team to reset their PDU: '
        markup = InlineKeyboardMarkup(inline_keyboard=self.create_inline_keyboard())
        bot.send_message(chat_id=update.message.chat_id, text=txt, reply_markup=markup)

    #--------------------------------#

    # Only for testing purposes
    @restricted
    def send_group(self, bot, update):
        bot.send_message(chat_id=self.ISC_grpID, text='Hello Group from {}'.format(
                         update.message.from_user.first_name))

    def start(self, bot, update):
        """
        Starting point for everybody texting ISCBot for the first time. Start via /start.
        """
        bot.send_message(chat_id=update.message.chat_id, text=('Hi there! I am the ISC PDU Bot '
                         + 'and can help you monitoring the PDUs. Type in your commands '
                         + 'with a \'/\' in the beginning.'))


    def get_help(self, bot, update):
        """
        List of all commands and brief explanations. Start via /help.
        """
        helptext = ''
        # Read in help.txt
        with open('help.txt', 'r') as f:
            for line in f:
                helptext += line

        bot.send_message(chat_id=update.message.chat_id, text=helptext,
                         parse_mode=ParseMode.MARKDOWN)

    def unknown(self, bot, update):
        """
        Default output for invalid commands or other messages in private chat.
        """
        update.message.reply_text('Sorry, I didn\'t understand that command.')


    @restricted
    def cb_query(self, bot, update):
        """
        Helper function for resetting the Rack PDUs.
        """
        team = update.callback_query.data
        bot.answer_callback_query(callback_query_id=update.callback_query.id,
                                  text=('Resetting PDU of {}. '
                                       + 'Please wait...').format(team))
        if(self.pdus.reset(team)):
            ips = ", ".join([str(ip) for ip in sorted(self.pdus.teams[team].keys())])
            self.edit_message_text_wrapper(bot,
                                  update.callback_query.message.chat_id,
                                  update.callback_query.message.message_id,
                                  ('Peak Power of PDU of team {} ({}) successfully '
                                  + 'reset.').format(team, ips))
            #Additionally, log in file
            ex = team + ' (.' + ips + '): Reset\n'
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open('exceedings.log', 'a') as f:
                f.write(now + ' --- ' + ex)
            return True
        else:
            self.edit_message_text_wrapper(bot,
                                  update.callback_query.message.chat_id,
                                  update.callback_query.message.message_id,
                                  ('Something went wrong during resetting PDU of team {} ({}). You '
                                  + 'might want to try it again!').format(team, ips))
            return False

    # Avoid telegram.error.BadRequest
    def edit_message_text_wrapper(self, bot, chat_id, message_id, text):
        if ('chat_id' not in self.last_msg
            or self.last_msg['chat_id'] != chat_id
            or self.last_msg['message_id'] != message_id
            or self.last_msg['text'] != text
            ):
            # Change message
            self.last_msg['chat_id'] = chat_id
            self.last_msg['message_id'] = message_id
            self.last_msg['text'] = text
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text)
            return
        else:
            # Nothing to do
            return


    def create_inline_keyboard(self):
        """
        Creates dynamically an inline keyboard layout for markup.
        """
        i = 0
        keyb = []
        tmp = []
        # If we don't need to reset HPCAC PDU, we don't show it here with ...ips[:-1]
        for team in sorted(self.pdus.teams):
            i += 1
            tmp.append(InlineKeyboardButton(str(team), callback_data=str(team)))
            if(i%4 == 0):
                keyb.append(tmp)
                tmp =[]
        keyb.append(tmp)
        return keyb


#-------Main method-------#

def main():
    VERSION = '1.4'
    print('Start ISCBot v{}'.format(VERSION))
    iscbot = ISCBot()
    # Start polling
    iscbot.queue.run_repeating(iscbot.check_limits, interval=2, first=0)
    iscbot.updater.start_polling()


#-------Main method-------#
if __name__ == '__main__':
    main()
