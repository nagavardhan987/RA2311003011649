from fastapi import FastAPI, HTTPException
import requests
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from logging_middleware.logger import Log
except ImportError:
    def Log(stack, level, package, message):
        print(f"[{level}] {message}")

app = FastAPI(title="Vehicle Maintenance Scheduler API")

def get_token():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("ACCESS_TOKEN="):
                    return line.strip().split("=")[1]
    return None

@app.get("/schedule")
def get_schedule():
    """
    Solves the 0/1 Knapsack problem for each depot.
    Capacity = MechanicHours
    Weight = Task Duration
    Value = Task Impact
    """
    token = get_token()
    if not token:
        Log("backend", "error", "handler", "Authorization token missing")
        raise HTTPException(status_code=401, detail="Missing auth token")

    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Fetch Depots
    try:
        depots_resp = requests.get("http://20.207.122.201/evaluation-service/depots", headers=headers)
        depots_resp.raise_for_status()
        depots = depots_resp.json().get("depots", [])
        Log("backend", "info", "handler", f"Fetched {len(depots)} depots successfully")
    except Exception as e:
        Log("backend", "error", "handler", f"Failed to fetch depots: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch depots")

    # 2. Fetch Vehicles (Tasks)
    try:
        vehicles_resp = requests.get("http://20.207.122.201/evaluation-service/vehicles", headers=headers)
        vehicles_resp.raise_for_status()
        vehicles = vehicles_resp.json().get("vehicles", [])
        Log("backend", "info", "handler", f"Fetched {len(vehicles)} vehicles successfully")
    except Exception as e:
        Log("backend", "error", "handler", f"Failed to fetch vehicles: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch vehicles")

    # 3. Algorithm: 0/1 Knapsack for each Depot
    results = {}
    
    # Map items to a simpler tuple: (weight, value, id)
    items = [(v.get("Duration", 0), v.get("Impact", 0), v.get("TaskID")) for v in vehicles]
    
    for depot in depots:
        depot_id = depot.get("ID")
        capacity = depot.get("MechanicHours", 0)
        
        n = len(items)
       
        dp = [[0 for _ in range(capacity + 1)] for _ in range(n + 1)]
        
        for i in range(1, n + 1):
            w, v, _ = items[i-1]
            for c in range(1, capacity + 1):
                if w <= c:
                    dp[i][c] = max(dp[i-1][c], dp[i-1][c-w] + v)
                else:
                    dp[i][c] = dp[i-1][c]
                    
        # Backtrack to find which tasks were selected
        selected_tasks = []
        total_duration = 0
        c = capacity
        for i in range(n, 0, -1):
            if dp[i][c] != dp[i-1][c]:
                w, v, tid = items[i-1]
                selected_tasks.append(tid)
                total_duration += w
                c -= w
                
        results[f"Depot_{depot_id}"] = {
            "BudgetHours": capacity,
            "TotalDurationUsed": total_duration,
            "TotalImpactAchieved": dp[n][capacity],
            "SelectedTaskIDs": selected_tasks
        }
        
    Log("backend", "info", "handler", "Successfully calculated optimal schedules for all depots")
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
