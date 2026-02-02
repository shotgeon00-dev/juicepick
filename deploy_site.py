import os
import json
import hashlib
import gzip
import requests
import google.auth.transport.requests
from google.oauth2 import service_account

KEY_FILE = 'key.json'
PROJECT_ID = 'juicehunter'
SITE_ID = 'juicehunter'  # Usually same as project ID for default site

def get_access_token():
    creds = service_account.Credentials.from_service_account_file(
        KEY_FILE,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token

def get_file_hash(content):
    return hashlib.sha256(content).hexdigest()

def compress_content(content):
    return gzip.compress(content)

def find_files_to_deploy():
    files = {} # path -> content (bytes)
    
    # Files to include explicitly or folders
    include_files = ['index.html', 'sw.js', 'firebase.json']
    include_dirs = ['assets']

    for f in include_files:
        if os.path.exists(f):
            with open(f, 'rb') as file:
                files['/' + f] = file.read()
    
    for d in include_dirs:
        if os.path.exists(d):
            for root, _, filenames in os.walk(d):
                for filename in filenames:
                    filepath = os.path.join(root, filename)
                    # Rel path for URL
                    rel_path = '/' + os.path.relpath(filepath, start='.').replace('\\', '/')
                    with open(filepath, 'rb') as file:
                        files[rel_path] = file.read()
    
    return files

def log(msg):
    print(msg)
    with open("deploy_log.txt", "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def deploy():
    # Clear log
    with open("deploy_log.txt", "w", encoding="utf-8") as f:
        f.write("Starting deployment...\n")

    log("🔑 Authenticating...")
    token = get_access_token()
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    log("📂 Preparing files...")
    files_data = find_files_to_deploy() # path -> raw_bytes
    file_hashes = {} # path -> sha256
    files_compressed = {} # hash -> gzipped_bytes
    
    for path, content in files_data.items():
        # Compress content (GZIP) because Firebase Hosting requires uploads to be gzipped?
        # Or at least the error "Content must be gzipped" suggests we should.
        compressed = compress_content(content)
        
        # Calculate hash of the COMPRESSED content
        file_hash = get_file_hash(compressed)
        
        file_hashes[path] = file_hash
        files_compressed[file_hash] = compressed 

    log(f"   Found {len(files_data)} files to deploy (compressed).")
    for p in files_data:
        log(f"     - {p}")

    # --- Load Hosting Config from firebase.json ---
    hosting_config = {}
    if os.path.exists("firebase.json"):
        with open("firebase.json", "r", encoding="utf-8") as f:
            fj = json.load(f)
            raw_hosting = fj.get("hosting", {})
            # Convert JSON format to REST API format (Source -> Glob, Header list -> Header Dict)
            if "headers" in raw_hosting:
                api_headers = []
                for entry in raw_hosting["headers"]:
                    h_dict = {}
                    for h_item in entry.get("headers", []):
                        h_dict[h_item["key"]] = h_item["value"]
                    
                    api_headers.append({
                        "glob": entry.get("source") or entry.get("glob"),
                        "headers": h_dict
                    })
                hosting_config["headers"] = api_headers
            
            if "rewrites" in raw_hosting:
                 # Handle rewrites if any
                 api_rewrites = []
                 for rw in raw_hosting["rewrites"]:
                     api_rw = {}
                     if "source" in rw: api_rw["glob"] = rw["source"]
                     if "destination" in rw: api_rw["path"] = rw["destination"]
                     api_rewrites.append(api_rw)
                 hosting_config["rewrites"] = api_rewrites

    # 1. Create Version
    log("🆕 Creating new version...")
    url = f"https://firebasehosting.googleapis.com/v1beta1/sites/{SITE_ID}/versions"
    # Pass the config to the version creation
    version_body = {"config": hosting_config} if hosting_config else {}
    resp = requests.post(url, headers=headers, json=version_body)
    log(f"Create Version Resp: {resp.status_code} {resp.text}")
    if resp.status_code != 200:
        raise Exception(f"Create Version Failed")
    version_name = resp.json()['name']
    log(f"   Version created: {version_name}")

    # 2. Populate Files
    log("📝 Populating file list...")
    populate_url = f"https://firebasehosting.googleapis.com/v1beta1/{version_name}:populateFiles"
    body = {"files": file_hashes}
    resp = requests.post(populate_url, headers=headers, json=body)
    log(f"Populate Resp: {resp.status_code} {resp.text}")
    if resp.status_code != 200:
        raise Exception(f"Populate Files Failed")
    
    result = resp.json()
    upload_url = result.get('uploadUrl')
    required_hashes = result.get('uploadRequiredHashes', [])
    
    log(f"   {len(required_hashes)} files need uploading.")

    # 3. Upload Required Files
    if required_hashes:
        for h in required_hashes:
            log(f"   Uploading hash: {h[:10]}...")
            content_to_upload = files_compressed[h] 
            
            u_url = f"{upload_url}/{h}"
            u_headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/octet-stream'}
            
            u_resp = requests.post(u_url, headers=u_headers, data=content_to_upload)
            if u_resp.status_code != 200:
                log(f"   Upload failed for {h}: {u_resp.status_code} {u_resp.text}")
                # Retry
                log("   Retrying...")
                u_resp = requests.post(u_url, headers=u_headers, data=content_to_upload)
                if u_resp.status_code != 200:
                    raise Exception(f"Failed to upload {h}")
            else:
                 log(f"   Upload success: {h[:10]}")

    # 4. Finalize Version
    log("🏁 Finalizing version...")
    finalize_url = f"https://firebasehosting.googleapis.com/v1beta1/{version_name}"
    # Use updateMask to be safe, but typically just patching the status in body works.
    # The error said "Field 'status' could not be found in request message", implying it expects it in message (body).
    finalize_body = {"status": "FINALIZED"}
    
    # We must add updateMask probably? Or just body is enough.
    # Let's try body only first.
    finalize_url += "?updateMask=status" 
    
    resp = requests.patch(finalize_url, headers=headers, json=finalize_body)
    log(f"Finalize Resp: {resp.status_code} {resp.text}")
    if resp.status_code != 200:
        raise Exception(f"Finalize Failed")
    
    # 5. Release
    log("🚀 Releasing...")
    release_url = f"https://firebasehosting.googleapis.com/v1beta1/sites/{SITE_ID}/releases"
    release_body = {"message": "Deployed via API script"}
    # Query param versionName is required for the release
    release_url += f"?versionName={version_name}"
    
    resp = requests.post(release_url, headers=headers, json=release_body)
    log(f"Release Resp: {resp.status_code} {resp.text}")
    if resp.status_code != 200:
        raise Exception(f"Release Failed")
    
    log("✅ Deployment Complete!")

if __name__ == "__main__":
    try:
        deploy()
    except Exception as e:
        log(f"❌ Error: {e}")
