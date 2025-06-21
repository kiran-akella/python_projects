import os
import json
import secrets
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

def load_credentials():
    try:
        with open('config/creds.json', 'r') as f:
            data = json.load(f)
            return data.get('users', [])
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return []

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    users = load_credentials()
    
    for user in users:
        if secrets.compare_digest(credentials.username, user["username"]) and \
           secrets.compare_digest(credentials.password, user["password"]):
            return credentials.username
            
    raise HTTPException(
        status_code=401,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Basic"},
    )
