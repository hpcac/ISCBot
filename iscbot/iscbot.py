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

        # Start Bot
        self.updater = Updater(token='565616615:AAHeVav01akOO_ox2RLED8jdLqMISLL-Hfc')
        dispatcher = self.updater.dispatcher
        self.queue = self.updater.job_queue

        # Add handler
        msg_handler = MessageHandler(Filters.text, self.message_reply)
        dispatcher.add_handler(msg_handler)

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

    def check_limits(self, bot, job):
        """
        Gets list of all teams off the power limit from the backend and sends push notifications.
        Possible ways for sending it: a) First user in access list, b) in the group.
        """
        exceeders = self.pdus.check_exceedings()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\n'
        if(len(exceeders) > 0):
            for ex in exceeders:
                print(now + ex)
                #bot.send_message(chat_id=self.access_list[0], text=ex)

                #Additionally, log in file
                with open('exceedings.log', 'a') as f:
                    f.write((now + '--- ' + ex).replace('\n', ' ') + '\n')

    # depricated
    @restricted
    def reset_pdu(self, bot, update):
        """
        @Deprecated
        Resets the peak power of PDU for certain IP address via old KeyboardMarkup.
        """
        txt = 'Please type in the last 3 digits of the IP address to reset: '
        markup = ReplyKeyboardMarkup(keyboard=self.create_reply_keyboard(),
                                     one_time_keyboard=True)
        bot.send_message(chat_id=update.message.chat_id, text=txt, reply_markup=markup)
        self.wait_for_reply = True

    @restricted
    def reset_pdu_inline(self, bot, update):
        """
        Resets the peak power of PDU for certain IP address via new inline KeyboardMarkup.
        """
        txt = 'Please type in the last 3 digits of the IP address to reset: '
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

    # depricated
    @restricted
    def message_reply(self, bot, update):
        """
        @Deprecated
        Helper function for PDU reset via old KeyboardMarkup.
        """
        if(not self.wait_for_reply):
            return True
        else:
            if(update.message.text.lower() == 'stop'):
                self.wait_for_reply = False
                return True
            try:
                ip = int(update.message.text)
            except ValueError:
                txt = ('Your answer was no valid number. Please send me the last 3 digits '
                      + 'of the IP address of the PDU you want to reset.\nIf you want to '
                      + 'stop the resetting procedure, just type \'`stop`\'.') 
                markup = ReplyKeyboardMarkup(keyboard=self.create_reply_keyboard(),
                                             one_time_keyboard=True)
                bot.send_message(chat_id=update.message.chat_id, reply_markup=markup,
                                 text=txt, parse_mode=ParseMode.MARKDOWN)
                return False
            if(ip not in self.pdus.ips):
                txt = ('The given number is none of the controllable PDU IPs. Please send '
                      + 'send me the last 3 digits of the IP address of the PDU you want to '
                      + 'reset or add the new IP address in the `ips.csv` file.\nIf you want '
                      + 'to stop the resetting procedure, just type \'`stop`\'.') 
                markup = ReplyKeyboardMarkup(keyboard=self.create_reply_keyboard(),
                                             one_time_keyboard=True)
                bot.send_message(chat_id=update.message.chat_id, reply_markup=markup,
                                 text=txt, parse_mode=ParseMode.MARKDOWN)
                return False
            else:
                self.wait_for_reply = False
                if(self.pdus.reset(ip)):
                    bot.send_message(chat_id=update.message.chat_id, text='Peak Power of '
                                     + 'PDU with IP .{} ({}) successfully resetted.'.format(
                                     ip, self.pdus.teams[ip]))
                    return True
                else:
                    bot.send_message(chat_id=update.message.chat_id, text='Something went '
                                     + 'wrong. Please try again!')
                    return False

    @restricted
    def cb_query(self, bot, update):
        """
        Helper function for resetting the Rack PDUs.
        """
        ip = update.callback_query.data
        bot.answer_callback_query(callback_query_id=update.callback_query.id,
                                  text=('Resetting PDU with IP address .{}. '
                                       + 'Please wait...').format(ip))
        try:
            ip = int(ip)
        except ValueError:
            print('Corrupted Data! Please check for security.', file=sys.stdout)
            bot.edit_message_text(chat_id=update.callback_query.message.chat_id,
                                  message_id=update.callback_query.message.message_id, 
                                  text=('Please verify the source of your data, it might '
                                  + 'be corrupted'))
            return False
        if(self.pdus.reset(ip)):
            bot.edit_message_text(chat_id=update.callback_query.message.chat_id, 
                                  message_id=update.callback_query.message.message_id,
                                  text=(('Peak Power of PDU with IP .{} ({}) successfully '
                                  + 'resetted.').format(ip, self.pdus.teams[ip])))
            return True
        else:
            bot.edit_message_text(chat_id=update.callback_query.message.chat_id, 
                                  message_id=update.callback_query.message.message_id,
                                  text='Something went wrong. Please try again!')
            return False
    
    # deprecated
    def create_reply_keyboard(self):
        """
        @Deprecated
        Creates dynamically a keyboard layout for markup.
        """
        i = 0
        keyb = []
        tmp = []
        # We don't need to reset HPCAC PDU, so we don't show it here
        for ip in self.pdus.ips[:-1]:
            i += 1
            tmp.append(str(ip))
            if(i%4 == 0):
                keyb.append(tmp)
                tmp =[]
        keyb.append(tmp)
        return keyb

    def create_inline_keyboard(self):
        """
        Creates dynamically an inline keyboard layout for markup.
        """
        i = 0
        keyb = []
        tmp = []
        # We don't need to reset HPCAC PDU, so we don't show it here
        for ip in self.pdus.ips[:-1]:
            i += 1
            tmp.append(InlineKeyboardButton(str(ip), callback_data=str(ip)))
            if(i%4 == 0):
                keyb.append(tmp)
                tmp =[]
        keyb.append(tmp)
        return keyb
       

#-------Main method-------#

def main():
    VERSION = '1.2'
    print('Start ISCBot v{}'.format(VERSION))
    iscbot = ISCBot()
    # Start polling
    iscbot.queue.run_repeating(iscbot.check_limits, interval=2, first=0)
    iscbot.updater.start_polling()


#-------Main method-------#
if __name__ == '__main__':
    main()
