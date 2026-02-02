import os
import json
import requests
import google.auth.transport.requests
from google.oauth2 import service_account

KEY_FILE = 'key.json'
PROJECT_ID = 'juicehunter'

def get_access_token():
    creds = service_account.Credentials.from_service_account_file(
        KEY_FILE,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token

def list_sites(token):
    url = f"https://firebasehosting.googleapis.com/v1beta1/projects/{PROJECT_ID}/sites"
    headers = {'Authorization': f'Bearer {token}'}
    resp = requests.get(url, headers=headers)
    print(f"Status: {resp.status_code}")
    print(resp.json())

if __name__ == "__main__":
    try:
        print("Getting token...")
        token = get_access_token()
        print("Token acquired. Listing sites...")
        list_sites(token)
    except Exception as e:
        print(f"Error: {e}")
