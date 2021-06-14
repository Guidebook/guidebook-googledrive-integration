import traceback
from googleapiclient.discovery import build
from google.oauth2 import service_account
from utils import fetch_ssm_params, _export_file
from builder_client import BuilderClient
from constants import PDF_PATH, SCOPES


def handle_google_drive_changes(event, context):
    """
    A lambda that checks recent changes in google drive and updates related files in Builder.
    """
    try:
        # Fetch the Builder API key, the guide and custom list IDs that we want to update, 
        # the service account credentials, and the name of the folder in Google Drive
        api_key, guide_and_list_ids, drive_folder_name, service_account_credentials = fetch_ssm_params()

        builder_client = BuilderClient(api_key)

        # Connect to google drive with credentials
        creds = service_account.Credentials.from_service_account_info(service_account_credentials, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)

        # Get the ID of the folder we are watching in google drive
        folder_id_search = service.files().list(q=f"mimeType='application/vnd.google-apps.folder' and name='{drive_folder_name}'", pageSize=1, fields="nextPageToken, files(id, name)").execute()
        folder_id = folder_id_search.get('files', [])[0].get('id')

        # Check for recent changes
        start_page = int(service.changes().getStartPageToken().execute()['startPageToken'])
        changes_response = service.changes().list(pageToken=start_page).execute()
        if changes_response['changes'] == []:
            changes_response = service.changes().list(pageToken=(start_page - 1)).execute()

        for guide_id, customlist_id in guide_and_list_ids:
            for change in changes_response['changes']:
                # Get the file associated to the change in Google Drive
                changed_file_id = change['fileId'] if change.get('fileId', None) else change['id']
                changed_file = service.files().get(fileId=changed_file_id, fields='name, trashed, parents').execute()

                # We can skip a change if it is not in the folder we are watching, or it is not a change of type `drive#change`
                if change['kind'] == 'drive#file' or folder_id not in changed_file['parents']:
                    continue

                # Fetch the existing CustomListItem from Builder if it exists by filtering on the import_id field.
                # This is needed to obtain the CustomListItem.id, which is required in the PATCH request
                url = f"https://beta.guidebook.com/open-api/v1/custom-list-items?guide={guide_id}&custom_lists={customlist_id}&import_id={changed_file_id}"
                response = builder_client.get(url)
                custom_list_item = response.json()['results'][0] if len(response.json()['results']) > 0 else None

                # If there is no existing custom list item, create a new one
                if not custom_list_item:
                    _export_file(service, changed_file_id)

                    # Create the custom list item
                    custom_list_item_post_url = "https://beta.guidebook.com/open-api/v1/custom-list-items/"
                    custom_list_item_post_data = {
                        "import_id": changed_file_id,
                        "guide": guide_id,
                        "name": changed_file['name'],
                        "description_html": "A custom list item with a link to {}".format(changed_file['name'])
                    }
                    custom_list_item_response = builder_client.post(custom_list_item_post_url, custom_list_item_post_data)

                    # Attach the custom list item to the custom list
                    item_relation_post_url = 'https://beta.guidebook.com/open-api/v1/custom-list-item-relations/'
                    item_relation_data = {
                       "custom_list": customlist_id,
                       "custom_list_item": custom_list_item_response.json()["id"],
                    }
                    builder_client.post(item_relation_post_url, item_relation_data)

                    # Create the pdf
                    pdf_post_url = 'https://beta.guidebook.com/open-api/v1/pdfs/'
                    pdf_post_data = {
                        "pdf_view_type": "pdf",
                        "guide": guide_id,
                        "include": True
                    }
                    with open(PDF_PATH, 'rb') as f:
                        pdf_response = builder_client.post(pdf_post_url, pdf_post_data, {'pdf_file': f})

                    # Create the link from the custom list item to the pdf
                    link_post_url = 'https://beta.guidebook.com/open-api/v1/links/'
                    link_post_data = {
                        "guide": guide_id,
                        "source_object_id": custom_list_item_response.json()["id"],
                        "source_content_type": "custom_list.customlistitem",
                        "target_object_id": pdf_response.json()["id"],
                        "target_content_type": "uri_resource.pdffile"
                    }
                    response = builder_client.post(link_post_url, link_post_data)

                # If there is an existing custom list item and the google drive item is not trashed, update the item
                # with the changes in Builder
                elif custom_list_item and changed_file['trashed'] == False:
                    _export_file(service, changed_file_id)

                    # Find the link associated to the custom list item and pdf
                    link_url = f"https://beta.guidebook.com/open-api/v1/links?guide={guide_id}&source_content_type=custom_list.customlistitem&source_object_id={custom_list_item['id']}&target_content_type=uri_resource.pdffile"
                    response = builder_client.get(link_url)
                    link = response.json()["results"][0]

                    # Update the pdf file
                    pdf_patch_url = "https://beta.guidebook.com/open-api/v1/pdfs/{}/".format(link['target_object_id'])
                    with open(PDF_PATH, 'rb') as f:
                        pdf_response = builder_client.patch(pdf_patch_url, files={'pdf_file': f})

                # If there is an existing custom list item and the google drive item is trashed, remove the item from Builder
                elif custom_list_item and changed_file['trashed'] == True:
                    url = "https://beta.guidebook.com/open-api/v1/custom-list-items/{}/".format(custom_list_item['id'])
                    builder_client.delete(url)

    except Exception as e:
        print(e)
        traceback.print_exc()
        return {"statusCode": 500}

    return {"statusCode": 200}
