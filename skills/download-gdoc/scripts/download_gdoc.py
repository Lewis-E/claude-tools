#!/usr/bin/env python3
"""Download content from a Google Doc as Markdown using Google's official API.

Downloads are cached to ~/.claude/gdocs/ keyed by doc ID. On re-download,
checks the doc's modifiedTime and skips export if unchanged.

Prerequisites:
    pip install google-auth google-api-python-client

Auth is handled automatically via gcloud Application Default Credentials.
If no credentials are found (or they've expired), the script runs
gcloud auth application-default login to open a browser for authentication.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import google.auth
import google.auth.exceptions
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
GCLOUD_SCOPES = ",".join(SCOPES + ["https://www.googleapis.com/auth/cloud-platform"])
CACHE_DIR = Path.home() / ".claude" / "gdocs"


def run_gcloud_login():
    """Run gcloud auth application-default login to get fresh credentials."""
    print("Authenticating with Google (this will open a browser)...", file=sys.stderr)
    result = subprocess.run(
        ["gcloud", "auth", "application-default", "login", f"--scopes={GCLOUD_SCOPES}"],
    )
    if result.returncode != 0:
        print("Error: gcloud authentication failed.", file=sys.stderr)
        sys.exit(1)


def authenticate():
    """Authenticate using ADC, running gcloud login if needed."""
    try:
        creds, _ = google.auth.default(scopes=SCOPES)
        return creds
    except google.auth.exceptions.DefaultCredentialsError:
        run_gcloud_login()
        creds, _ = google.auth.default(scopes=SCOPES)
        return creds


def extract_doc_id(doc_id_or_url: str) -> str:
    """Extract the document ID from a URL or return as-is if already an ID."""
    if "docs.google.com" in doc_id_or_url:
        parts = doc_id_or_url.split("/d/")
        if len(parts) > 1:
            return parts[1].split("/")[0]
    return doc_id_or_url


def get_cached_modified_time(doc_id: str) -> str | None:
    """Return the cached modifiedTime for a doc, or None if not cached."""
    meta_path = CACHE_DIR / f"{doc_id}.meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        return meta.get("modifiedTime")
    return None


def download_doc(doc_id_or_url: str, force: bool = False) -> Path:
    """Download a Google Doc to cache, returning the path to the .md file.

    Skips the export if the cached copy is up to date (unless force=True).
    If the API call fails due to expired credentials, re-authenticates and retries.
    """
    creds = authenticate()
    service = build("drive", "v3", credentials=creds)

    doc_id = extract_doc_id(doc_id_or_url)
    md_path = CACHE_DIR / f"{doc_id}.md"
    meta_path = CACHE_DIR / f"{doc_id}.meta.json"

    # Get file metadata (cheap API call), re-auth on failure
    try:
        file_meta = (
            service.files()
            .get(fileId=doc_id, fields="name,modifiedTime")
            .execute()
        )
    except google.auth.exceptions.RefreshError:
        run_gcloud_login()
        creds = authenticate()
        service = build("drive", "v3", credentials=creds)
        file_meta = (
            service.files()
            .get(fileId=doc_id, fields="name,modifiedTime")
            .execute()
        )

    remote_modified = file_meta["modifiedTime"]
    title = file_meta["name"]

    # Check cache
    if not force and md_path.exists():
        cached_modified = get_cached_modified_time(doc_id)
        if cached_modified == remote_modified:
            print(f"Cached (unchanged): {title}", file=sys.stderr)
            return md_path

    # Export as markdown
    content = (
        service.files()
        .export(fileId=doc_id, mimeType="text/markdown")
        .execute()
        .decode("utf-8")
        .strip()
    )

    # Write cache
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    md_path.write_text(content)
    meta_path.write_text(
        json.dumps(
            {
                "title": title,
                "modifiedTime": remote_modified,
                "url": f"https://docs.google.com/document/d/{doc_id}/edit",
            },
            indent=2,
        )
    )

    print(f"Downloaded: {title}", file=sys.stderr)
    return md_path


def main():
    parser = argparse.ArgumentParser(
        description="Download a Google Doc as Markdown (cached to ~/.claude/gdocs/)"
    )
    parser.add_argument("doc", help="Google Doc ID or full URL")
    parser.add_argument(
        "--force", action="store_true", help="Re-download even if cached"
    )
    parser.add_argument(
        "--path-only",
        action="store_true",
        help="Print the cached file path instead of content",
    )
    args = parser.parse_args()

    md_path = download_doc(args.doc, force=args.force)

    if args.path_only:
        print(md_path)
    else:
        print(md_path.read_text())


if __name__ == "__main__":
    main()
