"""
This file defines all the handlers needed by the server
"""

import logging
from typing import List

from emoji import emojize
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from classes.bot import Bot

V = 0
VV = 1
VVV = 2
VVVV = 3

STATUSES = {
    "canceled": emojize("Canceled :x:", language="alias"),
    "created": emojize("Created :new:", language="alias"),
    "failed": emojize("Failed :x:", language="alias"),
    "manual": emojize("Manual :three_button_mouse:", language="alias"),
    "pending": emojize("Pending :hourglass:", language="alias"),
    "preparing": emojize("Preparing :writing_hand:"),
    "running": emojize("Running :person_running:", language="alias"),
    "scheduled": emojize("Scheduled :date:", language="alias"),
    "skipped": emojize("Skipped :warning:"),
    "success": emojize("Success :white_check_mark:", language="alias"),
    "waiting_for_resource": emojize("Waiting :timer_clock:"),
}


def push_handler(data: dict, bot: Bot, chats: List[int], project_token: str) -> None:
    """
    Defines the handler for when a commit event is received
    """
    for chat in chats:
        for commit in data["commits"]:
            message = f'New commit on project {data["project"]["name"]}'
            message += f'\nAuthor : {commit["author"]["name"]}'
            if chat["verbosity"] != VVVV:
                message += "\nMessage: " + emojize(
                    commit["message"].partition("\n")[0], language="alias"
                )
            else:
                message += f'\nMessage: {emojize(commit["message"], language="alias")}'
            if chat["verbosity"] >= VV:
                message += f'\nUrl : {commit["url"]}'

            bot.send_message(chat_id=chat["id"], message=message)


def tag_handler(data: dict, bot: Bot, chats: List[int], project_token: str) -> None:
    """
    Defines the handler for when a tag event is received
    """
    for chat in chats:
        message = f'New tag event on project {data["project"]["name"]}'
        if chat["verbosity"] >= VV:
            message += f'\nTag :{data["ref"].lstrip("refs/tags/")}'
            message += (
                f'\nURL : {data["project"]["web_url"]}/-/{data["ref"].lstrip("refs/")}'
            )
        bot.send_message(chat_id=chat["id"], message=message)


def release_handler(data: dict, bot: Bot, chats: List[int], project_token: str) -> None:
    """
    Defines the handler for when a release event is received
    """
    for chat in chats:
        message = f'New release event on project {data["project"]["name"]}'
        if chat["verbosity"] >= VV:
            message += f'\nName : {data["name"]}'
            message += f'\nTag : {data["tag"]}'
            message += (
                f'\nDescription : {emojize(data["description"], language="alias")}'
            )
            message += f'\nURL : {data["url"]}'
        bot.send_message(chat_id=chat["id"], message=message)


def issue_handler(data: dict, bot: Bot, chats: List[int], project_token: str) -> None:
    """
    Defines the handler for when an issue event is received
    """
    for chat in chats:
        oa = data["object_attributes"]
        message = ""
        if oa["confidential"]:
            message += "[confidential] "
        message += f'New issue event on project {data["project"]["name"]}'
        message += f'\nTitle : {oa["title"]}'
        if chat["verbosity"] >= VVVV and oa["description"]:
            message += f'\nDescription : {emojize(oa["description"], language="alias")}'
        message += f'\nState : {oa["state"]}'
        message += f'\nURL : {oa["url"]}'
        if chat["verbosity"] >= VVV:
            if "assignees" in data:
                assignees = ", ".join([x["name"] for x in data["assignees"]])
                message += f"\nAssignee(s) : {assignees}"
            labels = ", ".join([x["title"] for x in data["labels"]])
            if labels:
                message += f"\nLabels : {labels}"
            due_date = oa["due_date"]
            if due_date:
                message += f"\nDue date : {due_date}"
        bot.send_message(chat_id=chat["id"], message=message)


def note_handler(data: dict, bot: Bot, chats: List[int], project_token: str) -> None:
    """
    Defines the handler for when a note event is received
    """
    for chat in chats:
        message = "New note on "
        if "commit" in data:
            message += "commit "
            info = f'\nCommit : {data["commit"]["url"]}'
        elif "merge_request" in data:
            message += "merge request "
            info = f'\nMerge request : {data["merge_request"]["title"]}'
        elif "issue" in data:
            message += "issue "
            info = f'\nIssue : {data["issue"]["title"]}'
        else:
            message += "snippet "
            info = f'\nSnippet : {data["snippet"]["title"]}'
        message += f'on project {data["project"]["name"]}'
        message += info
        message += (
            f'\nNote : {emojize(data["object_attributes"]["note"], language="alias")}'
        )
        if chat["verbosity"] >= VV:
            message += f'\nURL : {data["object_attributes"]["url"]}'
        bot.send_message(chat_id=chat["id"], message=message)


def merge_request_handler(
    data: dict, bot: Bot, chats: List[int], project_token: str
) -> None:
    """
    Defines the handler for when a merge request event is received
    """
    for chat in chats:
        oa = data["object_attributes"]
        message = f'New merge request event on project {data["project"]["name"]}'
        message += f'\nTitle : {oa["title"]}'
        message += f'\nSource branch : {oa["source_branch"]}'
        message += f'\nTarget branch : {oa["target_branch"]}'
        message += f'\nMerge status : {oa["merge_status"]}'
        message += f'\nState : {oa["state"]}'
        if chat["verbosity"] >= VVV:
            labels = ", ".join([x["title"] for x in data["labels"]])
            if labels:
                message += f"\nLabels : {labels}"
            if "assignee" in data:
                message += f'\nAssignee : {data["assignee"]["username"]}'
        if chat["verbosity"] >= VV:
            message += f'\nURL : {oa["url"]}'
        bot.send_message(chat_id=chat["id"], message=message)


def job_event_handler(
    data: dict, bot: Bot, chats: List[int], project_token: str
) -> None:
    """
    Defines the handler for when a job event is received
    """
    ctx = bot.context.table[project_token]["jobs"]
    status = data["build_status"]
    status_changed = True
    job_id = data["build_id"]
    if job_id in ctx:
        if "status" in ctx[job_id] and ctx[job_id]["status"] == status:
            status_changed = False
        if status_changed:
            ctx[job_id]["status"] = status
    else:
        ctx[job_id] = {"status": status}
    message = f'<b>Project</b> {data["repository"]["name"]}\n'
    message += f"<b>Job ID</b> {job_id}\n\n"
    url = f'{data["repository"]["homepage"]}/-/jobs/{job_id}'
    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text=STATUSES[status], url=url)]]
    )
    for chat in chats:
        if chat["verbosity"] >= VV:
            message += f'<b>Job name</b> : {data["build_name"]}\n'
            message += f'<b>Job stage</b> : {data["build_stage"]}'
        if status == "failed":
            message += f'\n\n<b>Failure reason</b> : {data["build_failure_reason"]}\n'
        if "message_id" in ctx[job_id]:
            message_id = ctx[job_id]["message_id"]
            if status_changed:
                bot.bot.edit_message_reply_markup(
                    chat_id=chat["id"], message_id=message_id, reply_markup=reply_markup
                )
            else:
                logging.info(f"WebHook received for Job {job_id} with unchanged status")
        else:
            message_id = bot.send_message(
                chat_id=chat["id"], message=message, markup=reply_markup
            )
            ctx[job_id]["message_id"] = message_id


def wiki_event_handler(
    data: dict, bot: Bot, chats: List[int], project_token: str
) -> None:
    """
    Defines the handler for when a wiki page event is received
    """
    for chat in chats:
        message = f'New wiki page event on project {data["project"]["name"]}'
        if chat["verbosity"] >= VV:
            message += f'\nURL : {data["wiki"]["web_url"]}'
        bot.send_message(chat_id=chat["id"], message=message)


def pipeline_handler(
    data: dict, bot: Bot, chats: List[int], project_token: str
) -> None:
    """
    Defines the hander for when a pipeline event is received
    """
    ctx = bot.context.table[project_token]["pipelines"]
    status = data["object_attributes"]["status"]
    status_changed = True
    pipeline_id = data["object_attributes"]["id"]
    if pipeline_id in ctx:
        if "status" in ctx[pipeline_id] and ctx[pipeline_id]["status"] == status:
            status_changed = False
        if status_changed:
            ctx[pipeline_id]["status"] = data["object_attributes"]["status"]
    else:
        ctx[pipeline_id] = {"status": status}
    message = f'<b>Project</b> {data["project"]["name"]}\n'
    message += f"<b>Pipeline ID</b> {pipeline_id}\n\n"
    message += f'<b>Commit title</b> {data["commit"]["title"]}\n'
    url = f'{data["project"]["web_url"]}/-/pipelines/{pipeline_id}'
    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text=STATUSES[status], url=url)]]
    )
    for chat in chats:
        if "message_id" in ctx[pipeline_id]:
            message_id = ctx[pipeline_id]["message_id"]
            if status_changed:
                bot.bot.edit_message_reply_markup(
                    chat_id=chat["id"], message_id=message_id, reply_markup=reply_markup
                )
            else:
                logging.info(
                    "WebHook received for Pipeline"
                    f" {pipeline_id} with unchanged status"
                )
        else:
            message_id = bot.send_message(
                chat_id=chat["id"], message=message, markup=reply_markup
            )
            ctx[pipeline_id]["message_id"] = message_id
