#!/usr/bin/env python3

"""
gitlab-webhook-telegram
"""

import json
import logging
import sys
from typing import List, Tuple

MODE_NONE = 0


class Context:
    """
    A class to pass all the parameters and shared values
    """

    def __init__(self, directory: str) -> None:
        self.directory = directory
        self.button_mode = MODE_NONE
        self.wait_for_verification = False
        self.config = None
        self.verified_chats = None
        self.table = None

    def get_config(self) -> Tuple[dict, List[int], dict]:
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
                f"{self.directory}config.json кажется, неправильно настроен, пожалуйста, следуйте"
                " инструкциям README."
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
                f"File {self.directory}verified_chats.json не найден. Возможно пустой"
            )
            self.verified_chats = []
        except Exception as e:
            logging.critical(
                f"Невозможно прочитать файл {self.directory}verified_chats.json."
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
                        print(self.table[token][int(chat_id)])
        except FileNotFoundError:
            logging.warning(
                f"Файл {self.directory}chats_projects.json не найден. Возможно пустой"
            )
            self.table = {}
        except Exception as e:
            logging.critical(
                f"Невозможно прочитать файл {self.directory}chats_projects.json."
            )
            logging.critical(str(e))
            sys.exit()
        return self.config, self.verified_chats, self.table

    def migrate_table_config(self) -> dict:
        """
        Add missing keys to table config file if needed
        """
        for token in self.table:
            for kind in ("jobs", "pipelines", "merge_requests"):
                if kind not in self.table[token]:
                    self.table[token][kind] = {}
                    logging.info(f"'{kind}' ключ отсутствует в таблице, добавляю")
        return self.table

    def write_verified_chats(self) -> None:
        """
        Save the verified chats file
        """
        with open(self.directory + "verified_chats.json", "w+") as outfile:
            json.dump(self.verified_chats, outfile)

    def write_table(self) -> None:
        """
        Save the verified chats file
        """
        with open(self.directory + "chats_projects.json", "w+") as outfile:
            json.dump(self.table, outfile)

    def is_authorized_project(self, token: str) -> bool:
        """
        Test if the token is in the configuration
        """
        res = False
        for projet in self.config["gitlab-projects"]:
            if token == projet["token"]:
                res = True
        return res
