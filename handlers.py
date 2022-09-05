"""
This file defines all the handlers needed by the server
"""

from emoji import emojize
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

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


def push_handler(data, bot, chats, project_token):
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


def tag_handler(data, bot, chats, project_token):
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


def release_handler(data, bot, chats, project_token):
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


def issue_handler(data, bot, chats, project_token):
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


def note_handler(data, bot, chats, project_token):
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


def merge_request_handler(data, bot, chats, project_token):
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


def job_event_handler(data, bot, chats, project_token):
    """
    Defines the handler for when a job event is received
    """
    if data["build_id"] in bot.context.table[project_token]["jobs"]:
        bot.context.table[project_token]["jobs"][data["build_id"]]["status"] = data[
            "build_status"
        ]
        message = f'Job event updated on project {data["repository"]["name"]}\n'
    else:
        bot.context.table[project_token]["jobs"][data["build_id"]] = {
            "status": data["build_status"]
        }
        message = f'New job event on project {data["repository"]["name"]}\n\n'
    reply_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=STATUSES[data["build_status"]],
                    url=f'{data["repository"]["homepage"]}/-/jobs/{data["build_id"]}',
                )
            ]
        ]
    )
    for chat in chats:
        if data["build_status"] == "failed":
            message += f'Failure reason : {data["build_failure_reason"]}\n'
        if chat["verbosity"] >= VV:
            message += f'Job name : {data["build_name"]}\n'
            message += f'Job stage : {data["build_stage"]}\n'
        if "message_id" in bot.context.table[project_token]["jobs"][data["build_id"]]:
            message_id = bot.context.table[project_token]["jobs"][data["build_id"]][
                "message_id"
            ]
            bot.bot.edit_message_reply_markup(
                chat_id=chat["id"], message_id=message_id, reply_markup=reply_markup
            )
        else:
            message_id = bot.send_message(
                chat_id=chat["id"], message=message, markup=reply_markup
            )
            bot.context.table[project_token]["jobs"][data["build_id"]][
                "message_id"
            ] = message_id


def wiki_event_handler(data, bot, chats, project_token):
    """
    Defines the handler for when a wiki page event is received
    """
    for chat in chats:
        message = f'New wiki page event on project {data["project"]["name"]}'
        if chat["verbosity"] >= VV:
            message += f'\nURL : {data["wiki"]["web_url"]}'
        bot.send_message(chat_id=chat["id"], message=message)


def pipeline_handler(data, bot, chats, project_token):
    """
    Defines the hander for when a pipeline event is received
    """
    for chat in chats:
        message = f'New pipeline event on project {data["project"]["name"]}'
        message += f'\nPipeline status : {data["object_attributes"]["status"]}'
        if chat["verbosity"] >= VV:
            message += f'\nURL : {data["project"]["web_url"]}/-/pipelines/{data["object_attributes"]["id"]}'
        bot.send_message(chat_id=chat["id"], message=message)
