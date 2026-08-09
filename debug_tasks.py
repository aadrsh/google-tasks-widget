from auth import get_service, list_accounts
import json

accounts = list_accounts()
if accounts:
    service = get_service(accounts[0])
    tasklists = service.tasklists().list().execute().get('items', [])
    for tl in tasklists:
        tasks = service.tasks().list(tasklist=tl['id']).execute().get('items', [])
        for t in tasks:
            print(f"Task: {t.get('title')}")
            print(f"  Due: {t.get('due')}")
            print(f"  Updated: {t.get('updated')}")
            print(f"  Notes: {t.get('notes')}")
            print(f"  All keys: {list(t.keys())}")
