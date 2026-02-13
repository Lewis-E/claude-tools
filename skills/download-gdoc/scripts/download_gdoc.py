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
import re
import subprocess
import sys
from pathlib import Path

import google.auth
import google.auth.exceptions
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

_IMAGE_PATTERNS = re.compile(
    r"!\[[^\]]*\]\([^\)]+\)\n*"          # inline: ![alt](url)
    r"|!\[[^\]]*\]\[[^\]]+\]\n*"         # reference-use: ![alt][ref]
    r"|\[[^\]]+\]:\s*<[^>]+>\n*",        # reference-def: [ref]: <data:...>
)

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


def _is_auth_error(exc: Exception) -> bool:
    """Return True if the exception is an authentication/authorization failure."""
    if isinstance(exc, HttpError) and exc.resp.status in (401, 403):
        return True
    if isinstance(exc, google.auth.exceptions.GoogleAuthError):
        return True
    msg = str(exc).lower()
    return "invalid_grant" in msg or "expired" in msg


def download_doc(doc_id_or_url: str, force: bool = False) -> Path:
    """Download a Google Doc to cache, returning the path to the .md file.

    Skips the export if the cached copy is up to date (unless force=True).
    If any API call fails due to expired credentials, re-authenticates and retries.
    """
    doc_id = extract_doc_id(doc_id_or_url)
    md_path = CACHE_DIR / f"{doc_id}.md"
    meta_path = CACHE_DIR / f"{doc_id}.meta.json"

    creds = authenticate()
    service = build("drive", "v3", credentials=creds)

    def _call(fn):
        """Run an API call, re-auth once on auth failure."""
        nonlocal service
        try:
            return fn(service)
        except Exception as first_err:
            if isinstance(first_err, HttpError) and first_err.resp.status == 404:
                print(
                    f"Error: Could not find document '{doc_id}'.\n"
                    f"API response: {first_err}\n\n"
                    "This usually means:\n"
                    "  1. The doc hasn't been shared **directly** with your authenticated Google account, or\n"
                    "  2. The GCP quota project may not have access to your org's Google Workspace.\n"
                    "     (Docs shared within Datadog Workspace groups may require an authorized GCP project.)\n\n"
                    "Try:\n"
                    "  Copying the doc into your own google drive to have direct access.",
                    file=sys.stderr,
                )
                sys.exit(1)
            if not _is_auth_error(first_err):
                raise
            print(f"Auth error: {first_err}", file=sys.stderr)
            print("Re-authenticating...", file=sys.stderr)
            run_gcloud_login()
            service = build("drive", "v3", credentials=authenticate())
            return fn(service)

    # Get file metadata
    file_meta = _call(
        lambda svc: svc.files().get(fileId=doc_id, fields="name,modifiedTime").execute()
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
    content = _call(
        lambda svc: svc.files()
        .export(fileId=doc_id, mimeType="text/markdown")
        .execute()
        .decode("utf-8")
        .strip()
    )

    # Strip embedded images (large base64 data / hosted URLs not useful for LLMs)
    content = _IMAGE_PATTERNS.sub("", content).strip()

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
