import requests
import os


CREDENTIALS = {
    "email": "nn7326@srmist.edu.in",
    "name": "Neerumalla Krishna Nagavardhan",
    "rollNo": "RA2311003011649",
    "accessCode": "QkbpxH",
    "clientID": "e35d171a-815c-4507-9b04-0c031abf8dc3",
    "clientSecret": "JQjgYPtPfJZcqZMa"
}

def get_auth_token():
    url = "http://20.207.122.201/evaluation-service/auth"
    try:
        response = requests.post(url, json=CREDENTIALS)
        response.raise_for_status()
        data = response.json()
        print("Successfully authenticated!")
        return data.get("access_token")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching auth token: {e}")
        if response and response.text:
            print(f"Response: {response.text}")
        return None

if __name__ == "__main__":
    token = get_auth_token()
    if token:
        print(f"Your Bearer Token: {token}")
        
        with open(".env", "w") as f:
            f.write(f"ACCESS_TOKEN={token}\n")
        print("Token saved to .env file.")
