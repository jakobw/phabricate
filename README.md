# phabricate

Create a batch of Phabricator subtasks from a markdown bullet list.

## Setup

Create an API token at `https://phabricator.wikimedia.org/settings/user/<you>/page/apitokens/` and save it to `.conduit-token` next to the script.

## Usage

```sh
./phabricate.py --project 1234 --parent-task T12345 [--emoji 🔧]
```

| Flag | | Meaning |
|---|---|---|
| `-P` | `--project` | Project id, from its workboard URL `/project/view/1234/`. |
| `-p` | `--parent-task` | The task the new tasks become subtasks of. |
| `-e` | `--emoji` | Optional single character to prefix every task title with. |

The task list is pasted at the prompt and terminated with Ctrl-D. After this, the script shows a preview of the tasks to be created and asks for confirmation.

## Input format

Every line starting with `* ` at column 0 is a task title. Everything below it until the next such line is that task's description. This works well when using the "copy from markdown" function in a google doc.
