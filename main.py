#!/usr/bin/env python3
"""
Automated Google Slides Update Based on JSON Mapping

New JSON structure:
{
  "slides": [
    {
      "slideNumber": 1,
      "notes": "...speaker notes text if needed...",
      "elements": {
        "TEXT": [
          {
            "objectId": "shape_1",
            "text": "New text for this shape",
            "placeholder": "{{SOME_PLACEHOLDER}}"    # optional if using replaceAllText
          }
        ],
        "IMAGE": [
          {
            "objectId": "image_1",
            "image_description": "short prompt to generate/update the image",
            "isBackground": false
          }
        ]
      }
    },
    ...
  ]
}

Note: This code does NOT yet update speaker notes. If you want to do that,
you would need additional requests for updating each slide's notes shape.
"""

import json
import os
import sys
import time

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from image_generator import generate_image  # your custom image generation function

# ----------------------- CONFIGURATION ----------------------- #
TEMPLATE_PRESENTATION_ID = "17fi6TQPb67LHBnbmsoYnYLjXI--SkVDqBW69hpiic3Y"
DRIVE_FOLDER_ID = None
CREDENTIALS_FILE = "credentials.json"
JSON_MAPPING_FILENAME = "mapping.json"
# ----------------------- END CONFIGURATION ----------------------- #

def get_credentials():
    """Obtain credentials from the service account file."""
    SCOPES = [
        "https://www.googleapis.com/auth/presentations",
        # "https://www.googleapis.com/auth/drive",
    ]
    creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return creds

def create_slides_service(creds):
    """Create a Google Slides API service."""
    return build("slides", "v1", credentials=creds)

def create_drive_service(creds):
    """Create a Google Drive API service."""
    return build("drive", "v3", credentials=creds)

def copy_presentation(drive_service, template_id, new_title):
    """Create a copy of the template presentation using the Drive API."""
    body = {"name": new_title}
    copied_file = drive_service.files().copy(fileId=template_id, body=body).execute()
    new_presentation_id = copied_file.get("id")
    print(f"Created a new presentation copy with ID: {new_presentation_id}")
    return new_presentation_id

def read_json_mapping(json_filename):
    """Read the JSON mapping file and return the mapping dictionary."""
    with open(json_filename, "r", encoding="utf-8") as f:
        mapping = json.load(f)
    return mapping

# def upload_image_to_drive(drive_service, file_path, file_name):
#     """
#     Upload the image file to Google Drive, set its permissions to public,
#     and return a URL that can be used by the Slides API.
#     """
#     file_metadata = {"name": file_name}
#     if DRIVE_FOLDER_ID:
#         file_metadata["parents"] = [DRIVE_FOLDER_ID]

#     media = MediaFileUpload(file_path, mimetype="image/png")
#     uploaded = drive_service.files().create(
#         body=file_metadata, media_body=media, fields="id"
#     ).execute()
#     file_id = uploaded.get("id")

#     # Set the file's permission so anyone can view it.
#     permission = {"type": "anyone", "role": "reader"}
#     drive_service.permissions().create(fileId=file_id, body=permission).execute()

#     image_url = f"https://drive.google.com/uc?id={file_id}"
#     print(f"Uploaded {file_name} to Drive; image URL: {image_url}")
#     return image_url

def build_update_requests_from_json(mapping, drive_service):
    """
    Build a list of update requests for the Slides API based on the new JSON format:

    {
      "slides": [
         {
            "slideNumber": 1,
            "notes": "Speaker notes here if needed",
            "elements": {
              "TEXT": [
                {
                  "objectId": "shape_1",
                  "text": "New text content",
                  "placeholder": "{{SOME_TEXT}}"
                }
              ],
              "IMAGE": [
                {
                  "objectId": "image_1",
                  "image_description": "Prompt for new image",
                  "isBackground": false
                }
              ]
            }
         },
         ...
      ]
    }

    This function:
      - Loops over each slide
      - For each TEXT element:
          If "placeholder" exists, uses replaceAllText to replace that placeholder
          with new content. Otherwise, you might do an update on the shape text by
          objectId (not demonstrated here).
      - For each IMAGE element:
          If "image_description" is present and non-empty, generate a new image
          and upload it to Drive, then create a replaceImage request.
    """
    requests = []
    slides = mapping.get("slides", [])
    for slide in slides:
        # (Optional) "notes" is here in the JSON, but we are not updating speaker notes.
        # If you want to do that, you'd need to create an update request using
        # the slide's pageObjectId and the shape ID of the notes shape.

        elements = slide.get("elements", {})
        text_elements = elements.get("TEXT", [])
        image_elements = elements.get("IMAGE", [])

        # ---------- Handle TEXT elements -----------
        for text_elem in text_elements:
            object_id = text_elem.get("objectId")
            new_text = text_elem.get("text", "").strip()
            placeholder = text_elem.get("placeholder", "").strip()

            # If you have placeholders in your template, you can replace them:
            if placeholder and new_text:
                requests.append({
                    "replaceAllText": {
                        "containsText": {
                            "text": placeholder,
                            "matchCase": True
                        },
                        "replaceText": new_text
                    }
                })
                print(f"Added text replacement: '{placeholder}' -> '{new_text}'.")

            # If you want to directly set text by object ID (instead of placeholders),
            # you'd do something like an "insertText" or "updateParagraphStyle" request.
            # That would require retrieving existing text, clearing it, etc.
            # The placeholder approach is simpler for a template.

        # ---------- Handle IMAGE elements -----------
        for img_elem in image_elements:
            object_id = img_elem.get("objectId")
            image_desc = img_elem.get("image_description", "").strip()

            if image_desc:
                # Generate the image locally
                output_filename = f"{object_id}_generated.png"
                generate_image(image_desc, output_filename)

                # Upload to Drive
                # image_url = upload_image_to_drive(drive_service, output_filename, output_filename)

                # Build a replaceImage request
                requests.append({
                    "replaceImage": {
                        "imageObjectId": object_id,
                        "uri": image_url,
                        "replaceMethod": "CENTER_CROP"
                    }
                })
                print(f"Added image replacement for object ID {object_id} with new image.")

                # Clean up temporary file
                try:
                    os.remove(output_filename)
                except Exception as e:
                    print(f"Warning: Could not remove temp file '{output_filename}': {e}")

    return requests

def main():
    # if len(sys.argv) < 2:
    #     print(f"Usage: {sys.argv[0]} <new_presentation_title> [json_mapping_file]")
    #     sys.exit(1)

    # new_presentation_title = sys.argv[1]
    # json_file = sys.argv[2] if len(sys.argv) > 2 else JSON_MAPPING_FILENAME
    new_presentation_title = "uncle_toby_test"
    json_file = "example_input.json"
    # Read JSON mapping data
    mapping = read_json_mapping(json_file)
    if not mapping:
        print("No mapping data found in JSON.")
        sys.exit(1)

    print("Mapping data loaded successfully.")

    # Initialize API services
    creds = get_credentials()
    slides_service = create_slides_service(creds)
    drive_service = create_drive_service(creds)

    # Create a new presentation copy from the template
    new_presentation_id = copy_presentation(drive_service, TEMPLATE_PRESENTATION_ID, new_presentation_title)

    # Allow a short delay for the new file to exist on Drive
    time.sleep(2)

    # Build update requests
    requests = build_update_requests_from_json(mapping, drive_service)
    if not requests:
        print("No update requests were built. Exiting.")
        sys.exit(1)

    # Execute the batch update
    body = {"requests": requests}
    response = slides_service.presentations().batchUpdate(
        presentationId=new_presentation_id, body=body
    ).execute()

    print("Update response:")
    print(response)
    print(f"Presentation updated: https://docs.google.com/presentation/d/{new_presentation_id}/edit")

if __name__ == "__main__":
    main()
