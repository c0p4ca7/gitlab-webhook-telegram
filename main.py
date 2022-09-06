#!/usr/bin/env python3

"""
gitlab-webhook-telegram
"""

import os

from classes.app import App


def main():
    directory = os.getenv("GWT_DIR", "./configs/")
    app = App(directory)
    app.run()


if __name__ == "__main__":
    main()
