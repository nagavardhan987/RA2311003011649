import requests
import os

def Log(stack: str, level: str, package: str, message: str):
    """
    Reusable logging middleware function.
    Valid stacks: "backend", "frontend"
    Valid levels: "debug", "info", "warn", "error", "fatal"
    Valid packages (backend): "cache", "controller", "cron_job", "db", "handler", "repository", "route", "service", "auth", "config", "middleware", "utils"
    """
    url = "http://20.207.122.201/evaluation-service/logs"
    
    
    token = None
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("ACCESS_TOKEN="):
                    token = line.strip().split("=")[1]
                    break
                    
    if not token:
        print(f"[{level.upper()}] {package}: {message} (WARNING: Token missing, could not send to server)")
        return
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "stack": stack.lower(),
        "level": level.lower(),
        "package": package.lower(),
        "message": message
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        # Successfully logged to server
    except requests.exceptions.RequestException as e:
        print(f"Failed to send log to server: {e}")
        
    
    print(f"[{level.upper()}] [{stack}/{package}] {message}")
