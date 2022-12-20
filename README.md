# Gitlab-webhook-telegram

> Original project from [BapRx/gitlab-webhook-telegram](https://github.com/BapRx/gitlab-webhook-telegram)

## What can GWT do for you ?

Gwt is a simple python server triggered by gitlab webhooks which trigger messages on telegram via a bot.

Some functionnalities :

- bind multiple projects to multiple chats
- display messages for every type of gitlab webhook
- choose message length with verbosity per chat and per project
- configure nearly all the bot by interaging with it on telegram (optional)
- run the app in a docker container

## Installation

### 1) Get a telegram bot

First things first, you need a telegram bot. To get one, you need to interact with @BotFather on telegram. Please refer to https://core.telegram.org/bots for the explicit procedure. You should et a token (like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`) and we will refer with `<token>` for the following.

### 2) Clone the repository

You can clone the git repository with

```bash
git clone https://github.com/c0p4ca7/gitlab-webhook-telegram.git
cd gitlab-webhook-telegram
```

Then you need to install the requirements.

#### Install the dependencies

```bash
python -m pip install -U -r requirements.txt
```

### 3) Configure the app

First copy example configuration files where the app is installed

```bash
cp config.json.example configs/config.json
```

> Note : if you want to have the configuration files elsewhere (in `/etc/gwt/` for example), expose the `GWT_DIR` variable, example:

```bash
export GWT_DIR=/etc/gwt/
```

See the configuration options:

| Parameter         | Type       | Default value    | Description                                                                            |
| ----------------- | ---------- | ---------------- | -------------------------------------------------------------------------------------- |
| `port`            | integer    | 8080             | The device port on which the web server should run.                                    |
| `telegram-token`  | string     | `""`             | The value of the telegram bot token.                                                   |
| `passphrase`      | string     | `"Here we go !"` | An optional passphrase to verify chats when. Set it to `null` to disable verification. |
| `gitlab-projects` | list(dict) | `[]`             | An array of preconfigured projects. See below.                                         |
| `log-level`       | string     | `"WARNING"`      | The log level.                                                                         |

The array of `gitlab-projects` should contain name and token for each project :

| Parameter  | Type         | Description                                                                                                                             |
| ---------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------|
| `name`     | string       | Pretty name of project.                                                                                                                 |
| `token`    | string       | Token of project. It sould be the same as on the gitlab webhook page. Cannot be more than 64 character.                                 |
| `user-ids` | list(string) | List of telegram user IDs (wildcard symbol * to allow any telegram user IDs for the project) allowed to list the preconfigured projects.|

The log level should be picked among :

- INFO
- DEBUG
- WARNING
- ERROR
- CRITICAL

More information on the log levels : https://docs.python.org/fr/3/howto/logging.html

A working `config.json` example :

```json
{
  "port": 8080,
  "telegram-token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
  "passphrase": "BCX2ipcGv5wCorPUWhTi9SXfWK6gz7",
  "gitlab-projects": [
    {
      "name": "Project 1",
      "token": "this is a secret token",
      "user-ids": ["000000007"]
    },
    {
      "name": "Project 2",
      "token": "G4oJnAm9ljWksgfjGTnUcUguv6WvkF",
      "user-ids": ["000000001", "000000002"]
    },
    {
      "name": "Wildcard access project",
      "token": "G4oJnAm9ljWksgfjGTnUcUguv6WvkF",
      "user-ids": ["*"]
    }
  ],
  "log-level": "INFO"
}
```

### 4) Run the app

You can start the server for testing with the following command:

```bash
python main.py
```

When you're ready, you can build and start the docker container with the following command:

```bash
docker compose up -d --build
```

## How to use the bot

| Command            | Usage                                                                                                                                                                     |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/start`           | Begin point of the bot. In this case, it displays the chat id and propose to verify chat by sending the passphrase.                                                       |
| `/help`            | Will display the list of available commands and the version of the bot.                                                                                                   |
| `/listProjects`    | Will display the configured projects for this chat and the verbosity of each, reprensented by an integer (from 0 to 3). The higher the integer, the verbosier the bot is. |
| `/addProject`      | Will display an interactive keyboard to choose a non-configured project to add to the current chat. The project will be added with the maximal verbosity (3).             |
| `/removeProject`   | Will display an interactive keyboard to choose a configured project and delete it from the table.                                                                         |
| `/changeVerbosity` | Will display an interactive keyboard to choose a configured project and change its verbosity.                                                                             |

## Under the hood

How does the app works.

When receiving a post request from Gitlab, it will retrieve the token and verify that the token is in the `config.json` file. If it is not, it will log an error and if it is it will retrieve the type of the hook in the following list :

- PUSH
- TAG
- RELEASE
- ISSUE
- CONFIDENTIAL_ISSUE
- NOTE
- CONFIDENTIAL_NOTE
- MR
- JOB
- WIKI
- PIPELINE

Then it will call the appropriate handler with the POST parameters. Each handler will then print message accordinglyot the chat verbosity and send it.

The bot also listen for messages and commands (messages with `/`) and react accordingly to write configuration files.

## FAQ

### Verbosities ?

There are 4 levels of verbosity, described below :

| Level | Description                                                                                                                        |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------- |
| 0     | Print all except issues descriptions, assignees, due dates, labels, commit messages and URLs and reduce commit messages to 1 line. |
| 1     | Print all except issues descriptions, assignees, due dates and labels and reduce commit messages to 1 line.                        |
| 2     | Print all but issues descriptions and reduce commit messages to 1 line.                                                            |
| 3     | Print all.                                                                                                                         |
