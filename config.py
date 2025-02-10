# ----------------------- CONFIGURATION ----------------------- #
# Replace with your template presentation ID.
TEMPLATE_PRESENTATION_ID = "YOUR_TEMPLATE_PRESENTATION_ID_HERE"

# Mapping of concept IDs to the image placeholder object IDs in your template.
# For example, if your template slide has an image placeholder for concept C1 with an object ID,
# then add it as follows:
IMAGE_OBJECT_IDS = {
    "C1": "IMAGE_OBJECT_ID_FOR_C1",
    "C2": "IMAGE_OBJECT_ID_FOR_C2",
    "C3": "IMAGE_OBJECT_ID_FOR_C3",
    # Add more mappings as needed.
}

# The CSV file to read. Its first row must be headers (including "Concept", "image_description", etc.)
CSV_FILENAME = "concept_data.csv"

# (Optional) If you want to upload images to a specific folder on Drive, specify its folder ID here.
DRIVE_FOLDER_ID = None

# Path to your service account credentials JSON file.
CREDENTIALS_FILE = "credentials.json"

# ----------------------- END CONFIGURATION ----------------------- #