#!/usr/bin/env python3

import logging
from datetime import datetime
from functools import wraps

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import ReplyKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, ContextTypes
from telegram.ext import CommandHandler, filters, MessageHandler
from telegram.ext import Application

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
        # set higher logging level for httpx to avoid all GET and POST requests being logged
        logging.getLogger("httpx").setLevel(logging.WARNING)
        # Start backend
        self.pdus = Backend(bot=self)
        print('Successfully initialized backend!')

        # Start Bot
        self.application = Application.builder().token('565616615:AAHeVav01akOO_ox2RLED8jdLqMISLL-Hfc').build()
        app = self.application
        self.queue = self.application.job_queue

        # Add handler
        start_handler = CommandHandler('start', self.start)
        app.add_handler(start_handler)

        help_handler = CommandHandler('help', self.get_help)
        app.add_handler(help_handler)

        #grp_handler = CommandHandler('grp', self.send_group)
        #app.add_handler(grp_handler)

        curr_power_handler = CommandHandler('current', self.current)
        app.add_handler(curr_power_handler)

        peak_power_handler = CommandHandler('peaks', self.peaks)
        app.add_handler(peak_power_handler)

        peak_dates_handler = CommandHandler('peakdates', self.peak_dates)
        app.add_handler(peak_dates_handler)

        #reset_handler = CommandHandler('reset', self.reset_pdu)
        #app.add_handler(reset_handler)

        inline_handler = CommandHandler('reset', self.reset_pdu_inline)
        app.add_handler(inline_handler)

        cbquery_handler = CallbackQueryHandler(self.cb_query)#, pass_groups=True)
        app.add_handler(cbquery_handler)

        # Unknown commands
        unknw_handler = MessageHandler(filters.COMMAND, self.unknown)
        app.add_handler(unknw_handler)

    #-------Permission Config--------#
    def restricted(func):
        @wraps(func)
        def wrapped(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            chat_id = update.effective_message.chat.id
            if user_id not in self.access_list and chat_id != self.ISC_grpID:
                print("Unauthorized access denied for {}.".format(user_id))
                return
            return func(self, update, context, *args, **kwargs)
        return wrapped

    #---------Main functions---------#
    async def current(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Gets current power usage of all teams from backend and sends it to the user.
        """
        await update.message.reply_text(text=self.pdus.current())


    async def peaks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Gets the peak power values of all teams from backend and sends it to the user.
        """
        await update.message.reply_text(text=self.pdus.peaks())


    async def peak_dates(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Gets the peak power values of all teams with corresponding timestamps from backend
        and sends it to the user.
        """
        await update.message.reply_text(text=self.pdus.peak_dates())


    async def check_limits(self, context: ContextTypes.DEFAULT_TYPE):
        """
        Gets list of all teams off the power limit from the backend and sends push notifications.
        Possible ways for sending it: a) First user in access list, b) in the group.
        """
        exceeders, not_reachable = self.pdus.check_exceedings()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\n'
        self.counter += 1
        bot = context.bot
        if(len(exceeders) > 0):
            for ex in exceeders:
                print(now + ex)
                # for all users in the access list
                #for chat in self.access_list:
                #    await bot.send_message(chat_id=chat, text=ex)
                # for the first user in the access list
                await bot.send_message(chat_id=self.access_list[0], text=ex)

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
    async def reset_pdu_inline(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Resets the peak power of PDU for certain IP address via new inline KeyboardMarkup.
        """
        txt = 'Please choose the team to reset their PDU: '
        markup = InlineKeyboardMarkup(inline_keyboard=self.create_inline_keyboard())
        await update.message.reply_text(text=txt, reply_markup=markup)

    #--------------------------------#

    # Only for testing purposes
    @restricted
    def send_group(self, bot, update):
        bot.send_message(chat_id=self.ISC_grpID, text='Hello Group from {}'.format(
                         update.message.from_user.first_name))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Starting point for everybody texting ISCBot for the first time. Start via /start.
        """
        await update.message.reply_text(text=('Hi there! I am the ISC PDU Bot '
                         + 'and can help you monitoring the PDUs. Type in your commands '
                         + 'with a \'/\' in the beginning.'))


    async def get_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        List of all commands and brief explanations. Start via /help.
        """
        helptext = ''
        # Read in help.txt
        with open('help.txt', 'r') as f:
            for line in f:
                helptext += line

        await update.message.reply_text(text=helptext, parse_mode=ParseMode.MARKDOWN_V2)


    async def unknown(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Default output for invalid commands or other messages in private chat.
        """
        await update.message.reply_text('Sorry, I didn\'t understand that command.')


    @restricted
    async def cb_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Helper function for resetting the Rack PDUs.
        """
        query = update.callback_query
        team = query.data
        await context.bot.answer_callback_query(callback_query_id=query.id,
                                  text=('Resetting PDU of {}. '
                                       + 'Please wait until the bot replies...').format(team))

        progress_msg = await context.bot.send_message(chat_id=query.message.chat_id, text="Start resetting PDU of {}".format(team), parse_mode=ParseMode.MARKDOWN_V2)
        if(await self.pdus.reset(team, context, progress_msg)):
            # In case of success, remove progress message
            await context.bot.delete_message(progress_msg.chat_id, progress_msg.message_id)
            ips = ", ".join([str(ip) for ip in sorted(self.pdus.teams[team].keys())])
            await self.edit_message_text_wrapper(context.bot,
                                  query.message.chat_id,
                                  query.message.message_id,
                                  ('Peak Power of PDU of team {} ({}) successfully '
                                  + 'reset.').format(team, ips))
            #Additionally, log in file
            ex = team + ' (.' + ips + '): Reset\n'
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open('exceedings.log', 'a') as f:
                f.write(now + ' --- ' + ex)
            return True
        else:
            await self.edit_message_text_wrapper(context.bot,
                                  query.message.chat_id,
                                  query.message.message_id,
                                  ('Something went wrong during resetting PDU of team {} ({}). You '
                                  + 'might want to try it again!').format(team, ips))
            return False


    # Avoid telegram.error.BadRequest
    async def edit_message_text_wrapper(self, bot, chat_id, message_id, text, parse_mode=None):
        if parse_mode == "md":
            parse_mode = ParseMode.MARKDOWN_V2
        if ('chat_id' not in self.last_msg
            or self.last_msg['chat_id'] != chat_id
            or self.last_msg['message_id'] != message_id
            or self.last_msg['text'] != text
            ):
            # Change message
            self.last_msg['chat_id'] = chat_id
            self.last_msg['message_id'] = message_id
            self.last_msg['text'] = text
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode=parse_mode)
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
    VERSION = '1.6'
    print('Start ISCBot v{}'.format(VERSION))
    iscbot = ISCBot()
    # Create repeating check for power limits
    check_job = iscbot.queue.run_repeating(iscbot.check_limits, interval=2, first=0)
    # disable logging of running check job
    logging.getLogger('apscheduler.scheduler').setLevel(logging.ERROR)
    logging.getLogger('apscheduler.executors.default').setLevel(logging.ERROR)
    # Start polling
    iscbot.application.run_polling(allowed_updates=Update.ALL_TYPES)


#-------Main method-------#
if __name__ == '__main__':
    main()
