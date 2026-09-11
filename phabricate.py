#!/usr/bin/env python3

import argparse
import json
import os
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request

HOST = "https://phabricator.wikimedia.org"
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".conduit-token")
# Wikimedia's CDN 403s if the UA isn't compliant with the UA policy
USER_AGENT = "phabricate/1.0 (https://github.com/jakobw/phabricate)"


def die(message):
    sys.exit(f"error: {message}")


def conduit(method, params):
    """calls a method on the phabricator API, called conduit"""
    params = dict(params, __conduit__={"token": TOKEN})
    body = urllib.parse.urlencode({"params": json.dumps(params)}).encode()
    request = urllib.request.Request(
        f"{HOST}/api/{method}", body, {"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            payload = json.load(resp)
    except urllib.error.URLError as exc:
        die(f"{method}: {exc}")
    if payload.get("error_code"):
        die(f"{method}: {payload['error_code']}: {payload.get('error_info', '')}")
    return payload["result"]


def parse_tasks(text):
    """[(title, description), ...] from markdown list."""
    tasks = []
    for line in text.splitlines():
        if line.startswith("* "):
            tasks.append([line[2:].strip(), []])
        elif tasks:
            tasks[-1][1].append(line)
    return [(title, textwrap.dedent("\n".join(body)).strip("\n")) for title, body in tasks]


def main():
    global TOKEN
    parser = argparse.ArgumentParser(
        description="Create Phabricator subtasks from a markdown bullet list.")
    parser.add_argument(
        "-P", "--project", required=True, type=int, metavar="1234",
        help=f"project id, from {HOST}/project/view/1234/")
    parser.add_argument(
        "-p", "--parent-task", required=True, metavar="T12345",
        help="task the new tasks become subtasks of")
    parser.add_argument(
        "-e", "--emoji", metavar="🔧",
        help="single character to prefix every task title with")
    args = parser.parse_args()
    project_id, parent_id = args.project, args.parent_task

    try:
        TOKEN = open(TOKEN_FILE).read().strip()
    except OSError:
        die(f"no API token in {TOKEN_FILE}")

    print("Paste the task list ('* ' per task), then press Ctrl-D:")
    tasks = parse_tasks(sys.stdin.read())
    if args.emoji:
        tasks = [(f"{args.emoji} {title}", body) for title, body in tasks]
    if not tasks:
        die("no tasks found")
    for title, _ in tasks:
        if not title:
            die("a task has an empty title")

    parent = conduit("phid.lookup", {"names": [parent_id.upper()]}).get(parent_id.upper())
    if not parent or parent["type"] != "TASK":
        die(f"parent task {parent_id} not found")

    found = conduit("project.search", {"constraints": {"ids": [project_id]}})["data"]
    if not found:
        die(f"no project with id {project_id} ({HOST}/project/view/{project_id}/)")
    fields = found[0]["fields"]
    # milestones and subprojects show as "Parent (Name)"
    name = (
        f"{fields['parent']['name']} ({fields['name']})"
        if fields.get("parent") else fields["name"])

    print(f"\nParent : {parent['fullName']}")
    print(f"Project: {name}  ({HOST}/project/view/{project_id}/)")
    print(f"Creating {len(tasks)} task(s) on {HOST}")
    print("=" * 70)
    for i, (title, description) in enumerate(tasks, 1):
        print(f"\n[{i}] {title}")
        for line in (description or "(no description)").splitlines():
            print(f"    | {line}")
    print("\n" + "=" * 70)

    if input(f"Create {len(tasks)} task(s)? [y/N] ").strip().lower() != "y":
        sys.exit("aborted; nothing was created")

    for i, (title, description) in enumerate(tasks, 1):
        transactions = [
            {"type": "title", "value": title},
            {"type": "parent", "value": parent["phid"]},
            {"type": "projects.add", "value": [found[0]["phid"]]},
        ]
        if description:
            transactions.append({"type": "description", "value": description})
        result = conduit("maniphest.edit", {"transactions": transactions})
        print(f"[{i}/{len(tasks)}] {HOST}/T{result['object']['id']}  {title}")


if __name__ == "__main__":
    main()
