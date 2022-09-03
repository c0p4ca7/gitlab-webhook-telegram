"""
This file defines all the handlers needed by the server
"""

V = 0
VV = 1
VVV = 2
VVVV = 3


def push_handler(data, bot, chats):
    """
    Defines the handler for when a commit event is received
    """
    for chat in chats:
        verbosity = chat[1]
        for commit in data["commits"]:
            message = f'New commit on project {data["project"]["name"]}'
            message += f'\nAuthor : {commit["author"]["name"]}'
            if verbosity != VVVV:
                message += "\nMessage: " + commit["message"].partition("\n")[0]
            else:
                message += f'\nMessage: {commit["message"]}'
            if verbosity >= VV:
                message += f'\nUrl : {commit["url"]}'

            bot.send_message(chat_id=chat[0], message=message)


def tag_handler(data, bot, chats):
    """
    Defines the handler for when a tag event is received
    """
    for chat in chats:
        verbosity = chat[1]
        message = f'New tag event on project {data["project"]["name"]}'
        if verbosity >= VV:
            message += f'\nTag :{data["ref"].lstrip("refs/tags/")}'
            message += (
                f'\nURL : {data["project"]["web_url"]}/-/{data["ref"].lstrip("refs/")}'
            )
        bot.send_message(chat_id=chat[0], message=message)


def release_handler(data, bot, chats):
    """
    Defines the handler for when a release event is received
    """
    for chat in chats:
        verbosity = chat[1]
        message = f'New release event on project {data["project"]["name"]}'
        if verbosity >= VV:
            message += f'\nName : {data["name"]}'
            message += f'\nTag : {data["tag"]}'
            message += f'\nDescription : {data["description"]}'
            message += f'\nURL : {data["url"]}'
        bot.send_message(chat_id=chat[0], message=message)


def issue_handler(data, bot, chats):
    """
    Defines the handler for when an issue event is received
    """
    for chat in chats:
        verbosity = chat[1]
        oa = data["object_attributes"]
        message = ""
        if oa["confidential"]:
            message += "[confidential] "
        message += f'New issue event on project {data["project"]["name"]}'
        message += f'\nTitle : {oa["title"]}'
        if verbosity >= VVVV and oa["description"]:
            message += f'\nDescription : {oa["description"]}'
        message += f'\nState : {oa["state"]}'
        message += f'\nURL : {oa["url"]}'
        if verbosity >= VVV:
            if "assignees" in data:
                assignees = ", ".join([x["name"] for x in data["assignees"]])
                message += f"\nAssignee(s) : {assignees}"
            labels = ", ".join([x["title"] for x in data["labels"]])
            if labels:
                message += f"\nLabels : {labels}"
            due_date = oa["due_date"]
            if due_date:
                message += f"\nDue date : {due_date}"
        bot.send_message(chat_id=chat[0], message=message)


def note_handler(data, bot, chats):
    """
    Defines the handler for when a note event is received
    """
    for chat in chats:
        verbosity = chat[1]
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
        message += f'\nNote : {data["object_attributes"]["note"]}'
        if verbosity >= VV:
            message += f'\nURL : {data["object_attributes"]["url"]}'
        bot.send_message(chat_id=chat[0], message=message)


def merge_request_handler(data, bot, chats):
    """
    Defines the handler for when a merge request event is received
    """
    for chat in chats:
        verbosity = chat[1]
        oa = data["object_attributes"]
        message = f'New merge request event on project {data["project"]["name"]}'
        message += f'\nTitle : {oa["title"]}'
        message += f'\nSource branch : {oa["source_branch"]}'
        message += f'\nTarget branch : {oa["target_branch"]}'
        message += f'\nMerge status : {oa["merge_status"]}'
        message += f'\nState : {oa["state"]}'
        if verbosity >= VVV:
            labels = ", ".join([x["title"] for x in data["labels"]])
            if labels:
                message += f"\nLabels : {labels}"
            if "assignee" in data:
                message += f'\nAssignee : {data["assignee"]["username"]}'
        if verbosity >= VV:
            message += f'\nURL : {oa["url"]}'
        bot.send_message(chat_id=chat[0], message=message)


def job_event_handler(data, bot, chats):
    """
    Defines the handler for when a job event is received
    """
    for chat in chats:
        verbosity = chat[1]
        message = f'New job event on project {data["repository"]["name"]}'
        message += f'\nJob status : {data["build_status"]}'
        if data["build_status"] != "success":
            message += f'\nFailure reason : {data["build_failure_reason"]}'
        if verbosity >= VV:
            message += f'\n\nJob name : {data["build_name"]}'
            message += f'\nJob stage : {data["build_stage"]}'
            message += (
                f'\nURL : {data["repository"]["homepage"]}/-/jobs/{data["build_id"]}'
            )
        bot.send_message(chat_id=chat[0], message=message)


def wiki_event_handler(data, bot, chats):
    """
    Defines the handler for when a wiki page event is received
    """
    for chat in chats:
        verbosity = chat[1]
        message = f'New wiki page event on project {data["project"]["name"]}'
        if verbosity >= VV:
            message += f'\nURL : {data["wiki"]["web_url"]}'
        bot.send_message(chat_id=chat[0], message=message)


def pipeline_handler(data, bot, chats):
    """
    Defines the hander for when a pipeline event is received
    """
    for chat in chats:
        verbosity = chat[1]
        message = f'New pipeline event on project {data["project"]["name"]}'
        message += f'\nPipeline status : {data["object_attributes"]["status"]}'
        if verbosity >= VV:
            message += f'\nURL : {data["project"]["web_url"]}/-/pipelines/{data["object_attributes"]["id"]}'
        bot.send_message(chat_id=chat[0], message=message)
