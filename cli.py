import argparse
import sys
from auth import add_account, remove_account, list_accounts

def main():
    parser = argparse.ArgumentParser(description="Manage Google Tasks Widget accounts")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    parser_add = subparsers.add_parser("add-account", help="Add a new Google account")
    parser_add.add_argument("name", help="Name to identify this account (e.g., 'Work', 'Personal')")
    
    parser_remove = subparsers.add_parser("remove-account", help="Remove an existing account")
    parser_remove.add_argument("name", help="Name of the account to remove")
    
    parser_list = subparsers.add_parser("list-accounts", help="List all configured accounts")
    
    args = parser.parse_args()
    
    if args.command == "add-account":
        print(f"Adding account: {args.name}")
        try:
            add_account(args.name)
            print("Successfully authenticated and saved account!")
        except Exception as e:
            print(f"Error adding account: {e}")
            sys.exit(1)
            
    elif args.command == "remove-account":
        if remove_account(args.name):
            print(f"Removed account: {args.name}")
        else:
            print(f"Account '{args.name}' not found.")
            sys.exit(1)
            
    elif args.command == "list-accounts":
        accounts = list_accounts()
        if not accounts:
            print("No accounts configured.")
        else:
            print("Configured accounts:")
            for acc in accounts:
                print(f" - {acc}")

if __name__ == "__main__":
    main()
