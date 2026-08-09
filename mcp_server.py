import os
import sys
import json
from typing import Optional, List
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from mcp.server import MCPServer as FastMCP
from auth import list_accounts, get_service

# Initialize FastMCP Server
mcp = FastMCP("Google Tasks Manager")

def validate_account(account_name: str):
    """Security check to ensure account_name is a valid, configured account to prevent path traversal."""
    valid_accounts = list_accounts()
    if account_name not in valid_accounts:
        raise ValueError(f"Account '{account_name}' is not configured or authenticated. Valid accounts: {valid_accounts}")

@mcp.tool()
def get_accounts() -> str:
    """Lists all configured and authenticated Google accounts."""
    accounts = list_accounts()
    return json.dumps({"accounts": accounts})

@mcp.tool()
def list_tasks(account_name: str) -> str:
    """Lists all task lists and pending tasks for a specific account.
    
    Args:
        account_name: Name of the account (e.g. 'Personal', 'Work')
    """
    try:
        validate_account(account_name)
        service = get_service(account_name)
        if not service:
            return json.dumps({"error": f"Failed to connect to Google Tasks API for account '{account_name}'"})
            
        tasklists_res = service.tasklists().list(maxResults=20).execute()
        tasklists = tasklists_res.get('items', [])
        
        result = []
        for tl in tasklists:
            tasks_res = service.tasks().list(tasklist=tl['id'], showHidden=False, maxResults=50).execute()
            tasks = tasks_res.get('items', [])
            pending = [
                {
                    "id": t['id'],
                    "title": t.get('title', ''),
                    "notes": t.get('notes', ''),
                    "due": t.get('due', ''),
                    "recurrence": t.get('recurrence', []),
                    "parent": t.get('parent', '')
                }
                for t in tasks if t.get('status') != 'completed'
            ]
            result.append({
                "list_id": tl['id'],
                "list_title": tl['title'],
                "tasks": pending
            })
        return json.dumps({"account": account_name, "lists": result}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def create_task(account_name: str, list_id: str, title: str, notes: Optional[str] = None, due_date: Optional[str] = None, repeat_frequency: Optional[str] = None) -> str:
    """Creates a new task in Google Tasks.
    
    Args:
        account_name: Account to add task to (e.g. 'Personal')
        list_id: ID of the task list (use list_tasks to get list_ids)
        title: Title of the task
        notes: Optional notes or description for the task
        due_date: Optional due date in YYYY-MM-DD format (e.g. '2026-08-15')
        repeat_frequency: Optional repeat frequency ('Daily', 'Weekly', 'Monthly')
    """
    try:
        validate_account(account_name)
        service = get_service(account_name)
        if not service:
            return json.dumps({"error": f"Failed to get service for account '{account_name}'"})
            
        task_body = {"title": title}
        if notes:
            task_body["notes"] = notes
        if due_date:
            task_body["due"] = f"{due_date[:10]}T00:00:00.000Z"
        if repeat_frequency:
            freq_upper = repeat_frequency.upper()
            if freq_upper in ["DAILY", "WEEKLY", "MONTHLY"]:
                task_body["recurrence"] = [f"RRULE:FREQ={freq_upper}"]
                
        created = service.tasks().insert(tasklist=list_id, body=task_body).execute()
        return json.dumps({"success": True, "task_id": created.get("id"), "title": created.get("title")})
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def complete_task(account_name: str, list_id: str, task_id: str) -> str:
    """Marks a Google task as completed.
    
    Args:
        account_name: Account name
        list_id: Task list ID
        task_id: Task ID to complete
    """
    try:
        validate_account(account_name)
        service = get_service(account_name)
        if not service:
            return json.dumps({"error": f"Failed to get service for account '{account_name}'"})
            
        task = service.tasks().get(tasklist=list_id, task=task_id).execute()
        task['status'] = 'completed'
        updated = service.tasks().update(tasklist=list_id, task=task_id, body=task).execute()
        return json.dumps({"success": True, "task_id": updated.get("id"), "status": "completed"})
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def delete_task(account_name: str, list_id: str, task_id: str) -> str:
    """Deletes a Google task permanently.
    
    Args:
        account_name: Account name
        list_id: Task list ID
        task_id: Task ID to delete
    """
    try:
        validate_account(account_name)
        service = get_service(account_name)
        if not service:
            return json.dumps({"error": f"Failed to get service for account '{account_name}'"})
            
        service.tasks().delete(tasklist=list_id, task=task_id).execute()
        return json.dumps({"success": True, "deleted_task_id": task_id})
    except Exception as e:
        return json.dumps({"error": str(e)})

def main():
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
