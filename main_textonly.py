#!/usr/bin/env python3
"""
Minimal script to update text in an existing Google Slides presentation
by object ID, ignoring images (no Drive API access needed).

Requires:
  - A service account JSON with Slides API scope.
  - google-api-python-client, google-auth, google-auth-oauthlib installed.

JSON input example (mapping.json):
{
  "slides": [
    {
      "slideNumber": 1,
      "elements": {
        "TEXT": [
          {
            "objectId": "myShapeId1",
            "text": "New content here"
          },
          {
            "objectId": "myShapeId2",
            "text": "Another text"
          }
        ],
        "IMAGE": []
      }
    },
    {
      "slideNumber": 2,
      "elements": {
        "TEXT": [
          {
            "objectId": "myShapeId3",
            "text": "Slide 2 text"
          }
        ]
      }
    }
  ]
}
"""

import json
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ----------------------- CONFIGURATION ----------------------- #
PRESENTATION_ID = "1nu-2gCkkKkn9TburRVi7q7djTlsegntVCW6a6oo8Zcs"
CREDENTIALS_FILE = "credentials.json"  # service account JSON
JSON_MAPPING_FILENAME = "example_input.json"
# ------------------------------------------------------------ #

def get_slides_service(credentials_file):
    """
    Create a Google Slides API service using only the presentations scope.
    """
    SCOPES = ["https://www.googleapis.com/auth/presentations"]
    creds = service_account.Credentials.from_service_account_file(
        credentials_file, scopes=SCOPES
    )
    return build("slides", "v1", credentials=creds)

def read_json_mapping(json_filename):
    """Read the JSON mapping file and return the dictionary."""
    with open(json_filename, "r", encoding="utf-8") as f:
        return json.load(f)

def build_text_update_requests(mapping):
    """
    Based on JSON with "slides" -> "elements" -> "TEXT",
    create update requests that:
      1) delete all existing text in the shape, then
      2) insert the new text at index 0.

    (Ignores IMAGE entries.)
    """
    requests = []
    slides = mapping.get("slides", [])
    for slide in slides:
        elements = slide.get("elements", {})
        text_elems = elements.get("TEXT", [])

        for t_elem in text_elems:
            object_id = t_elem.get("objectId")
            new_text  = t_elem.get("text", "")

            if not object_id or new_text is None:
                continue

            # 1) Delete existing text
            requests.append({
                "deleteText": {
                    "objectId": object_id,
                    "textRange": {
                        "type": "ALL"
                    }
                }
            })

            # 2) Insert new text at index 0
            requests.append({
                "insertText": {
                    "objectId": object_id,
                    "insertionIndex": 0,
                    "text": new_text
                }
            })

    return requests

def main():
    """
    Usage: python update_text_by_objectid.py [<json_mapping_file>]

    Loads a JSON file (default: mapping.json),
    then updates shape text by object ID in the existing Slides presentation
    identified by PRESENTATION_ID.
    """
    json_file = sys.argv[1] if len(sys.argv) > 1 else JSON_MAPPING_FILENAME

    # 1) Read JSON mapping
    mapping_data = read_json_mapping(json_file)
    if not mapping_data:
        print("No mapping data found in JSON.")
        sys.exit(1)

    # 2) Create the Slides service
    slides_service = get_slides_service(CREDENTIALS_FILE)

    # 3) Build text-update requests
    requests = build_text_update_requests(mapping_data)
    if not requests:
        print("No text update requests were built. Exiting.")
        sys.exit(0)

    # 4) Execute the batchUpdate
    body = {"requests": requests}
    response = slides_service.presentations().batchUpdate(
        presentationId=PRESENTATION_ID, body=body
    ).execute()

    print("Text update response:")
    print(response)
    print(f"Presentation updated: https://docs.google.com/presentation/d/{PRESENTATION_ID}/edit")

if __name__ == "__main__":
    main()
