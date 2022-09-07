#!/usr/bin/env python3

"""
gitlab-webhook-telegram
"""

import json
import logging
import os
import socketserver
import sys
from http.server import BaseHTTPRequestHandler
from typing import TypeVar

from telegram.ext import CallbackContext

import handlers
from classes.bot import Bot
from classes.context import Context

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


RequestHandlerType = TypeVar(
    "RequestHandlerType",
    bound="BaseHTTPRequestHandler",
)


def get_RequestHandler(bot: Bot, context: CallbackContext) -> RequestHandlerType:
    """
    A wrapper for the RequestHandler class to pass parameters
    """

    class RequestHandler(BaseHTTPRequestHandler):
        """
        The server request handler
        """

        def __init__(self, *args, **kwargs) -> None:
            self.bot = bot
            self.context = context
            super().__init__(*args, **kwargs)

        def _set_headers(self, code: int) -> None:
            """
            Send response with code and close headers
            """
            self.send_response(code)
            self.send_header("Content-type", "text/html")
            self.end_headers()

        def do_POST(self) -> None:
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

    def __init__(self, directory: str) -> None:
        self.directory = directory

    def run(self) -> None:
        """
        run is called when the app starts
        """
        context = Context(self.directory)
        context.get_config()
        context.migrate_table_config()
        logging.info("Starting gitlab-webhook-telegram app")
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
