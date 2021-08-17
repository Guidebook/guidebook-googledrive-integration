import settings
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account
from utils import _export_file, _alphabetize_all_items
from builder_client import BuilderClient
from constants import PDF_PATH, SCOPES


def load_file_data():
    """
    This script will bootstrap a guide in Builder with all files in given folder in Google Drive.
    Be sure all of the settings in settings.py are up to date before running this.
    """
    builder_client = BuilderClient(settings.builder_api_key)

    # Connect to google drive with credentials
    creds = service_account.Credentials.from_service_account_info(settings.service_account_credentials, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)

    # Get all files in the specified folder
    folder_id_search = service.files().list(q=f"mimeType='application/vnd.google-apps.folder' and name='{settings.drive_folder_name}'", pageSize=10, fields="nextPageToken, files(id, name)").execute()
    folder_id = folder_id_search.get('files', [])[0].get('id')
    results = service.files().list(q=f"'{folder_id}' in parents", pageSize=50, fields="nextPageToken, files(id, name)").execute()

    items = results.get('files', [])
    # Download each file and add it to a custom list item in Builder
    for guide_id, customlist_id in settings.guide_and_list_ids:
        for item in items:
            _export_file(service, item['id'])

            # Create the custom list item
            custom_list_item_post_url = "https://builder.guidebook.com/open-api/v1/custom-list-items/"
            custom_list_item_post_data = {
                "import_id": item["id"],
                "guide": guide_id,
                "name": item['name'],
                "description_html": f"A custom list item with a link to {item['name']}"
            }
            custom_list_item_response = builder_client.post(custom_list_item_post_url, custom_list_item_post_data)

            # Attach the custom list item to the custom list
            item_relation_post_url = 'https://builder.guidebook.com/open-api/v1/custom-list-item-relations/'
            item_relation_data = {
               "custom_list": customlist_id,
               "custom_list_item": custom_list_item_response.json()["id"],
            }
            builder_client.post(item_relation_post_url, item_relation_data)

            # Create the pdf
            pdf_post_url = 'https://builder.guidebook.com/open-api/v1/pdfs/'
            pdf_post_data = {
                "pdf_view_type": "pdf",
                "guide": guide_id,
                "include": True
            }
            with open(PDF_PATH, 'rb') as f:
                pdf_response = builder_client.post(pdf_post_url, pdf_post_data, {'pdf_file': f})

            # Create the link from the custom list item to the pdf
            link_post_url = 'https://builder.guidebook.com/open-api/v1/links/'
            link_post_data = {
                "guide": guide_id,
                "source_object_id": custom_list_item_response.json()["id"],
                "source_content_type": "custom_list.customlistitem",
                "target_object_id": pdf_response.json()["id"],
                "target_content_type": "uri_resource.pdffile",
                "_title": item['name']
            }
            response = builder_client.post(link_post_url, link_post_data)

        _alphabetize_all_items(builder_client, guide_id, customlist_id)

if __name__ == "__main__":
    load_file_data()
