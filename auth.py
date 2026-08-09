import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/tasks']
CONFIG_DIR = os.path.expanduser('~/.config/google-tasks-widget')
ACCOUNTS_DIR = os.path.join(CONFIG_DIR, 'accounts')
CREDS_FILE = os.path.join(CONFIG_DIR, 'credentials.json')

os.makedirs(ACCOUNTS_DIR, exist_ok=True)

def get_token_path(account_name):
    return os.path.join(ACCOUNTS_DIR, f"token_{account_name}.pickle")

def list_accounts():
    accounts = []
    if os.path.exists(ACCOUNTS_DIR):
        for f in os.listdir(ACCOUNTS_DIR):
            if f.startswith('token_') and f.endswith('.pickle'):
                name = f[6:-7]
                accounts.append(name)
    return accounts

def add_account(account_name):
    if not os.path.exists(CREDS_FILE):
        raise FileNotFoundError(f"Missing OAuth credentials at {CREDS_FILE}")
    
    flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
    creds = flow.run_local_server(port=8080, open_browser=True)
    
    token_path = get_token_path(account_name)
    with open(token_path, 'wb') as token:
        pickle.dump(creds, token)
    return True

def remove_account(account_name):
    token_path = get_token_path(account_name)
    if os.path.exists(token_path):
        os.remove(token_path)
        return True
    return False

def get_service(account_name):
    token_path = get_token_path(account_name)
    if not os.path.exists(token_path):
        return None
        
    with open(token_path, 'rb') as token:
        creds = pickle.load(token)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
            except Exception:
                return None
        else:
            return None
            
    # Check scopes
    if not set(SCOPES).issubset(set(creds.scopes)):
        return None
        
    return build('tasks', 'v1', credentials=creds)
