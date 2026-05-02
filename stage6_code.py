import requests
import os
from datetime import datetime
from auth_helper import get_auth_token

def fetch_and_sort_notifications():
    # 1. Get Token from .env or fetch it fresh
    token = None
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("ACCESS_TOKEN="):
                    token = line.strip().split("=")[1]
                    break
    
    if not token:
        print("Fetching new token...")
        token = get_auth_token()
        if not token:
            print("Failed to get token. Exiting.")
            return

    # 2. Fetch Notifications from API
    url = "http://20.207.122.201/evaluation-service/notifications"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    print("Fetching notifications from server...\n")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        notifications = data.get("notifications", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching notifications: {e}")
        return

    # 3. Sort Notifications based on Priority Logic
    
    weight_map = {
        "Placement": 3,
        "Result": 2,
        "Event": 1
    }
    
    def sort_key(notification):
        
        weight = weight_map.get(notification.get("Type"), 0)
        
        
        timestamp_str = notification.get("Timestamp", "")
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            
            timestamp = datetime.min
            
        return (weight, timestamp)
    
    
    sorted_notifications = sorted(notifications, key=sort_key, reverse=True)
    
    # 4. Display Top 10 for the screenshot
    print(f"--- PRIORITY INBOX (TOP {min(10, len(sorted_notifications))}) ---")
    print(f"{'Type':<12} | {'Timestamp':<20} | Message")
    print("-" * 70)
    for notif in sorted_notifications[:10]:
        print(f"{notif.get('Type', ''):<12} | {notif.get('Timestamp', ''):<20} | {notif.get('Message', '')}")

if __name__ == "__main__":
    fetch_and_sort_notifications()
