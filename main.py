#!/usr/bin/env python3

"""
Gitlab-webhook-telegram
"""

import json
import logging
import os
import socketserver
import sys
import time
from http.server import BaseHTTPRequestHandler

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)

import handlers

"""
Here comes constant definitions
"""
MODE_NONE = 0
MODE_ADD_PROJECT = 1
MODE_REMOVE_PROJECT = 2
MODE_CHANGE_VERBOSITY_1 = 3
MODE_CHANGE_VERBOSITY_2 = 4

PUSH = "Push Hook"
TAG = "Tag Push Hook"
RELEASE = "Release Hook"
ISSUE = "Issue Hook"
CONFIDENTIAL_ISSUE = "Confidential Issue Hook"
NOTE = "Note Hook"
CONFIDENTIAL_NOTE = "Confidential Note Hook"
MR = "Merge Request Hook"
JOB = "Job Hook"
WIKI = "Wiki Page Hook"
PIPELINE = "Pipeline Hook"

HANDLERS = {
    PUSH: handlers.push_handler,
    TAG: handlers.tag_handler,
    RELEASE: handlers.release_handler,
    ISSUE: handlers.issue_handler,
    CONFIDENTIAL_ISSUE: handlers.issue_handler,
    NOTE: handlers.note_handler,
    CONFIDENTIAL_NOTE: handlers.note_handler,
    MR: handlers.merge_request_handler,
    JOB: handlers.job_event_handler,
    WIKI: handlers.wiki_event_handler,
    PIPELINE: handlers.pipeline_handler,
}

V = 0
VV = 1
VVV = 2
VVVV = 3

VERBOSITIES = [
    (
        V,
        "Print all except issues descriptions, assignees, due dates, labels, commit messages and URLs and reduce commit messages to 1 line",
    ),
    (
        VV,
        "Print all except issues descriptions, assignees, due dates and labels and reduce commit messages to 1 line",
    ),
    (
        VVV,
        "Print all but issues descriptions and reduce commit messages to 1 line",
    ),
    (
        VVVV,
        "Print all",
    ),
]


class Context:
    """
    A class to pass all the parameters and shared values
    """

    def __init__(self, directory):
        self.directory = directory
        self.button_mode = MODE_NONE
        self.wait_for_verification = False
        self.config = None
        self.verified_chats = None
        self.table = None

    def get_config(self):
        """
        Load the config file and transform it into a python usable var
        """
        try:
            with open(f"{self.directory}config.json") as config_file:
                self.config = json.load(config_file)
        except Exception as e:
            print(f"Unable to read {self.directory}config.json. Exception follows")
            print(str(e))
            sys.exit()

        if not all(
            key in self.config
            for key in (
                "gitlab-projects",
                "log-level",
                "passphrase",
                "port",
                "telegram-token",
            )
        ):
            print(
                f"{self.directory}config.json seems to be misconfigured, please follow the README instructions."
            )
            sys.exit()

        logging.basicConfig(
            level=self.config["log-level"],
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

        try:
            with open(f"{self.directory}verified_chats.json") as verified_chats_file:
                self.verified_chats = json.load(verified_chats_file)
        except FileNotFoundError:
            logging.warning(
                f"File {self.directory}verified_chats.json not found. Assuming empty"
            )
            self.verified_chats = []
        except Exception as e:
            logging.critical(
                f"Unable to read {self.directory}verified_chats.json. Exception follows"
            )
            logging.critical(str(e))
            sys.exit()
        try:
            with open(f"{self.directory}chats_projects.json") as table_file:
                self.table = {}
                tmp = json.load(table_file)
                for token in tmp:
                    self.table[token] = {}
                    for chat_id in tmp[token]:
                        self.table[token][int(chat_id)] = tmp[token][chat_id]
        except FileNotFoundError:
            logging.warning(
                f"File {self.directory}chats_projects.json not found. Assuming empty"
            )
            self.table = {}
        except Exception as e:
            logging.critical(
                f"Unable to read {self.directory}chats_projects.json. Exception follows"
            )
            logging.critical(str(e))
            sys.exit()
        return self.config, self.verified_chats, self.table

    def migrate_table_config(self):
        """
        Add missing keys to table config file if needed
        """
        for token in self.table:
            for kind in ("jobs", "pipelines"):
                if kind not in self.table[token]:
                    self.table[token][kind] = {}
                    logging.info(f"'{kind}' key missing from table, adding now")
        return self.table

    def write_verified_chats(self):
        """
        Save the verified chats file
        """
        with open(self.directory + "verified_chats.json", "w+") as outfile:
            json.dump(self.verified_chats, outfile)

    def write_table(self):
        """
        Save the verified chats file
        """
        with open(self.directory + "chats_projects.json", "w+") as outfile:
            json.dump(self.table, outfile)

    def is_authorized_project(self, token):
        """
        Test if the token is in the configuration
        """
        res = False
        for projet in self.config["gitlab-projects"]:
            if token == projet["token"]:
                res = True
        return res


class Bot:
    """
    A wrapper for the telegram bot
    """

    def __init__(self, token, context):
        self.token = token
        self.context = context
        self.updater = Updater(token=self.token, use_context=True)
        self.bot = self.updater.bot
        self.username = self.bot.username
        self.dispatcher = self.updater.dispatcher

        start_handler = CommandHandler("start", self.start)
        self.dispatcher.add_handler(start_handler)

        add_project_handler = CommandHandler("addProject", self.add_project)
        self.dispatcher.add_handler(add_project_handler)

        remove_project_handler = CommandHandler("removeProject", self.remove_project)
        self.dispatcher.add_handler(remove_project_handler)

        change_verbosity_handler = CommandHandler(
            "changeVerbosity", self.change_verbosity
        )
        self.dispatcher.add_handler(change_verbosity_handler)

        list_projects_handlers = CommandHandler("listProjects", self.list_projects)
        self.dispatcher.add_handler(list_projects_handlers)

        help_hanlder = CommandHandler("help", self.help)
        self.dispatcher.add_handler(help_hanlder)

        self.dispatcher.add_handler(CallbackQueryHandler(self.button))

        message_handler = MessageHandler(Filters.text, self.message)
        self.dispatcher.add_handler(message_handler)

        self.updater.start_polling()

    def send_message(self, chat_id, message, markup=None):
        """
        Send a message to a chat ID, split long text in multiple messages
        """
        max_message_length = 4096
        if len(message) <= max_message_length:
            message = self.bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=markup,
                parse_mode="HTML",
            )
            return message.message_id
        parts = []
        while len(message) > 0:
            if len(message) > max_message_length:
                part = message[:max_message_length]
                first_lnbr = part.rfind("\n")
                if first_lnbr != -1:
                    parts.append(part[:first_lnbr])
                    message = message[first_lnbr:]
                else:
                    parts.append(part)
                    message = message[max_message_length:]
            else:
                parts.append(message)
                break
        for part in parts:
            message = self.bot.send_message(
                chat_id=chat_id, text=part, reply_markup=markup, parse_mode="HTML"
            )
            time.sleep(0.25)
        return message.message_id

    def start(self, update, context):
        """
        Defines the handler for /start command
        """
        chat_id = update.message.chat_id
        bot = context.bot
        bot.send_message(
            chat_id=chat_id, text="Hi. I'm a simple bot triggered by GitLab webhooks."
        )
        if chat_id in self.context.verified_chats:
            bot.send_message(
                chat_id=chat_id,
                text="Since your chat is already verified, send /help to see the available commands.",
            )
        elif not self.context.config["passphrase"]:
            self.context.verified_chats.append(chat_id)
            self.context.write_verified_chats()
            bot.send_message(
                chat_id=chat_id,
                text="Your chat is now verified, send /help to see the available commands.",
            )
        else:
            bot.send_message(
                chat_id=chat_id,
                text="First things first : you need to verify this chat. Just send me the passphrase.",
            )
            self.context.wait_for_verification = True

    def add_project(self, update, context):
        """
        Defines the handler for /addProject command
        """
        chat_id = update.message.chat_id
        bot = context.bot
        if chat_id in self.context.verified_chats:
            self.context.button_mode = MODE_ADD_PROJECT
            inline_keyboard = []
            projects = [
                project
                for project in self.context.config["gitlab-projects"]
                if (
                    str(chat_id) in project["user-ids"]
                    and (
                        (
                            project["token"] in self.context.table
                            and chat_id not in self.context.table[project["token"]]
                        )
                        or project["token"] not in self.context.table
                    )
                )
            ]
            if len(projects) > 0:
                for project in projects:
                    inline_keyboard.append(
                        [
                            InlineKeyboardButton(
                                text=project["name"], callback_data=project["token"]
                            )
                        ]
                    )
                replyKeyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
                bot.send_message(
                    chat_id=chat_id,
                    reply_markup=replyKeyboard,
                    text="Choose the project you want to add.",
                )
            else:
                bot.send_message(chat_id=chat_id, text="No project to add.")
        else:
            bot.send_message(
                chat_id=chat_id,
                text="This chat is not verified, start with the command /start.",
            )

    def change_verbosity(self, update, context):
        """
        Defines the handler for /changeVerbosity command
        """
        chat_id = update.message.chat_id
        bot = context.bot
        if chat_id in self.context.verified_chats:
            self.context.button_mode = MODE_CHANGE_VERBOSITY_1
            inline_keyboard = []
            projects = [
                project
                for project in self.context.config["gitlab-projects"]
                if (
                    project["token"] in self.context.table
                    and chat_id in self.context.table[project["token"]]
                )
            ]
            if len(projects) > 0:
                for project in projects:
                    inline_keyboard.append(
                        [
                            InlineKeyboardButton(
                                text=project["name"], callback_data=project["token"]
                            )
                        ]
                    )
                replyKeyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
                bot.send_message(
                    chat_id=chat_id,
                    reply_markup=replyKeyboard,
                    text="Choose the project from which you want to change verbosity.",
                )
            else:
                bot.send_message(
                    chat_id=chat_id, text="No project configured on this chat."
                )
        else:
            bot.send_message(
                chat_id=chat_id,
                text="This chat is not verified, start with the command /start.",
            )

    def remove_project(self, update, context):
        """
        Defines the handler for /removeProject command
        """
        chat_id = update.message.chat_id
        bot = context.bot
        if chat_id in self.context.verified_chats:
            self.context.button_mode = MODE_REMOVE_PROJECT
            inline_keyboard = []
            projects = [
                project
                for project in self.context.config["gitlab-projects"]
                if (
                    project["token"] in self.context.table
                    and chat_id in self.context.table[project["token"]]
                )
            ]
            if len(projects) > 0:
                for project in projects:
                    inline_keyboard.append(
                        [
                            InlineKeyboardButton(
                                text=project["name"], callback_data=project["token"]
                            )
                        ]
                    )
                replyKeyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
                bot.send_message(
                    chat_id=chat_id,
                    reply_markup=replyKeyboard,
                    text="Choose the project you want to remove.",
                )
            else:
                bot.send_message(chat_id=chat_id, text="No project to remove.")
        else:
            bot.send_message(
                chat_id=chat_id,
                text="This chat is not verified, start with the command /start.",
            )

    def button(self, update, context):
        """
        Defines the handler for a click on button
        """
        query = update.callback_query
        bot = context.bot
        if self.context.button_mode == MODE_ADD_PROJECT:
            token = query.data
            chat_id = query.message.chat_id
            if token in self.context.table and chat_id in self.context.table[token]:
                bot.edit_message_text(
                    text="Project was already there. Changing nothing.",
                    chat_id=chat_id,
                    message_id=query.message.message_id,
                )
            else:
                if token not in self.context.table:
                    self.context.table[token] = {}
                self.context.table[token][chat_id]["verbosity"] = VVVV
                self.context.write_table()
                bot.edit_message_text(
                    text="The project was successfully added.",
                    chat_id=chat_id,
                    message_id=query.message.message_id,
                )
            self.context.button_mode = MODE_NONE
        elif self.context.button_mode == MODE_REMOVE_PROJECT:
            chat_id = query.message.chat_id
            token = query.data
            if (
                token not in self.context.table
                or chat_id not in self.context.table[token]
            ):
                bot.edit_message_text(
                    text="Project was not there. Changing nothing.", chat_id=chat_id
                )
            else:
                del self.context.table[token][chat_id]
                self.context.write_table()
                bot.edit_message_text(
                    text="The project was successfully removed.",
                    chat_id=chat_id,
                    message_id=query.message.message_id,
                )
        elif self.context.button_mode == MODE_CHANGE_VERBOSITY_1:
            chat_id = query.message.chat_id
            self.context.button_mode = MODE_CHANGE_VERBOSITY_2
            self.context.selected_project = query.data
            inline_keyboard = []
            for i, verbosity in enumerate(VERBOSITIES):
                inline_keyboard.append(
                    [
                        InlineKeyboardButton(
                            text=str(i) + ":" + verbosity[1], callback_data=i + 1
                        )
                    ]
                )
            replyKeyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
            message_verbosities = "Verbosities : \n"
            for verb in VERBOSITIES:
                message_verbosities += "- " + str(verb[0]) + " : " + verb[1] + "\n"
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=query.message.message_id,
                reply_markup=replyKeyboard,
                text=message_verbosities + "\nChoose the new verbosity.",
            )
        elif self.context.button_mode == MODE_CHANGE_VERBOSITY_2:
            chat_id = query.message.chat_id
            self.context.button_mode = MODE_NONE
            verbosity = int(query.data) - 1
            self.context.table[self.context.selected_project][chat_id][
                "verbosity"
            ] = verbosity
            self.context.write_table()
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=query.message.message_id,
                text="The verbosity of the project has been changed.",
            )
            self.context.selected_project = None
        else:
            pass

    def message(self, update, context):
        """
        The handler in case a simple message is posted
        """
        bot = context.bot
        if self.context.wait_for_verification:
            if update.message.text == self.context.config["passphrase"]:
                self.context.verified_chats.append(update.message.chat_id)
                self.context.write_verified_chats()
                bot.send_message(
                    chat_id=update.message.chat_id,
                    text="Thank you, your user ID is now verified. Send /help to see the available commands.",
                )
                self.context.wait_for_verification = False
            else:
                bot.send_message(
                    chat_id=update.message.chat_id,
                    text="The passphrase is incorrect. Still waiting for verification.",
                )

    def help(self, update, context):
        """
        Defines the handler for /help command
        """
        bot = context.bot
        message = "Project gitlab-webhook-telegram v1.0.0\n"
        message += "You can use the following commands : \n\n"
        message += "/listProjects : list tracked projects in this chat\n"
        message += "/addProject : add a project in this chat\n"
        message += "/removeProject : remove a project from this chat\n"
        message += "/changeVerbosity : change the level of information of a chat\n"
        message += "/help : display this message"
        bot.send_message(chat_id=update.message.chat_id, text=message)

    def list_projects(self, update, context):
        chat_id = update.message.chat_id
        bot = context.bot
        projects = [
            project
            for project in self.context.config["gitlab-projects"]
            if (
                project["token"] in self.context.table
                and chat_id in self.context.table[project["token"]]
            )
        ]
        message = "Projects : \n"
        if len(projects) == 0:
            message += "There is no project"
        for id, project in enumerate(projects):
            message += f'{id+1} - <b>{project["name"]}</b> (Verbosity: {self.context.table[project["token"]][chat_id]["verbosity"]})\n'
        bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")


def get_RequestHandler(bot, context):
    """
    A wrapper for the RequestHandler class to pass parameters
    """

    class RequestHandler(BaseHTTPRequestHandler):
        """
        The server request handler
        """

        def __init__(self, *args, **kwargs):
            self.bot = bot
            self.context = context
            super(RequestHandler, self).__init__(*args, **kwargs)

        def _set_headers(self, code):
            """
            Send response with code and close headers
            """
            self.send_response(code)
            self.send_header("Content-type", "text/html")
            self.end_headers()

        def do_POST(self):
            """
            Handler for POST requests
            """
            token = self.headers["X-Gitlab-Token"]
            if self.context.is_authorized_project(token):
                type = self.headers["X-Gitlab-Event"]
                content_length = int(self.headers["Content-Length"])
                data = self.rfile.read(content_length)
                body = json.loads(data.decode("utf-8"))
                if type in HANDLERS:
                    if token in self.context.table and self.context.table[token]:
                        chats = [
                            {
                                "id": chat,
                                "verbosity": self.context.table[token][chat][
                                    "verbosity"
                                ],
                            }
                            for chat in self.context.table[token]
                            if chat in self.context.verified_chats
                        ]
                        HANDLERS[type](body, bot, chats, token)
                        self._set_headers(200)
                    else:
                        logging.warning("No chats.")
                        self._set_headers(200)
                else:
                    logging.error("No handler for the event " + type)
                    self._set_headers(404)
            else:
                logging.warning("Unauthorized project : token not in config.json")
                self._set_headers(403)

    return RequestHandler


class App:
    """
    A class to run the app.
    Override init and run command
    """

    def __init__(self, directory):
        self.directory = directory

    def run(self):
        """
        run is called when the app starts
        """
        context = Context(self.directory)
        context.get_config()
        context.migrate_table_config()
        logging.info("Starting gitlab-webhook-telegram app")
        logging.info(
            "config.json, chats_projects.json and verified_chats.json found. Using them for configuration."
        )
        logging.debug("Getting bot with token " + context.config["telegram-token"])
        try:
            bot = Bot(context.config["telegram-token"], context)
            logging.info("Bot " + bot.username + " grabbed. Let's go.")
        except Exception as e:
            logging.critical("Failed to grab bot. Stopping here the program.")
            logging.critical("Exception : " + str(e))
            sys.exit()
        logging.info(
            "Starting server on http://localhost:" + str(context.config["port"])
        )
        try:
            RequestHandler = get_RequestHandler(bot, context)
            httpd = socketserver.TCPServer(("", context.config["port"]), RequestHandler)
            httpd.serve_forever()
        except KeyboardInterrupt:
            logging.info("Keyboard interruption received. Shutting down the server")
        httpd.server_close()
        httpd.shutdown()
        logging.info("Server is down")
        os._exit(0)


def main():
    directory = os.getenv("GWT_DIR", "./configs/")
    app = App(directory)
    app.run()


if __name__ == "__main__":
    main()
