import os
import boto3
import json
import io
import shutil
from googleapiclient.http import MediaIoBaseDownload
from constants import PDF_PATH
from collections import namedtuple


def fetch_ssm_params():
    """
    Util for fetching the params stored in SSM (Parameter Store)
    """
    region = os.environ["AWS_REGION"]
    client = boto3.client("ssm", region_name=region)

    # The api key used to send data to Builder
    api_key = client.get_parameter(
        Name="/lambdas/googledrivewebhookreceiver/api_key", WithDecryption=True
    )["Parameter"]["Value"]

    # The ids of the guides and custom lists that will be updated in Builder
    guide_and_list_ids = client.get_parameter(
        Name="/lambdas/googledrivewebhookreceiver/guide_and_list_ids", WithDecryption=False
    )["Parameter"]["Value"]
    guide_and_list_ids = list(eval(guide_and_list_ids))

    # The name of the folder with custom list item documents in Google Drive
    drive_folder_name = client.get_parameter(
        Name="/lambdas/googledrivewebhookreceiver/drive_folder_name", WithDecryption=False
    )["Parameter"]["Value"]

    # The start page for a changes list request. Is set programatically by the lambda.
    start_page = client.get_parameter(
        Name="/lambdas/googledrivewebhookreceiver/start_page", WithDecryption=False
    )["Parameter"]["Value"]

    service_account_credentials = client.get_parameter(
        Name="/lambdas/googledrivewebhookreceiver/service_account_credentials", WithDecryption=True
    )["Parameter"]["Value"]
    service_account_credentials = json.loads(service_account_credentials)

    SSMParams = namedtuple('SSMParams', ['api_key', 'guide_and_list_ids', 'drive_folder_name', 'start_page', 'service_account_credentials'])
    return SSMParams(api_key, guide_and_list_ids, drive_folder_name, start_page, service_account_credentials)


def _export_file(service, file_id):
    """
    Util for exporting a file from Google Drive as a pdf
    """
    request = service.files().get_media(fileId=file_id, fields='name')
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print("Download %d%%" % int(status.progress() * 100))
    fh.seek(0)
    with open(PDF_PATH, 'wb') as f:
        shutil.copyfileobj(fh, f, length=131072)


def _alphabetize_all_items(builder_client, guide_id, customlist_id):
    """
    Pull all items from the custom list, alphabetize, and adjust ranks accordingly.
    """
    items_url = f"https://builder.guidebook.com/open-api/v1/custom-list-items?guide={guide_id}&custom_list={customlist_id}"
    response = builder_client.get(items_url)
    sorted_list = sorted(response.json()["results"], key=lambda x: x['name'])

    rank = 0
    for item in sorted_list:
        relation_url = f"https://builder.guidebook.com/open-api/v1/custom-list-item-relations/?custom_list_item={item['id']}&custom_list={customlist_id}"
        cutom_list_item_relation = builder_client.get(relation_url).json()['results'][0]
        relation_patch_url = f"https://builder.guidebook.com/open-api/v1/custom-list-item-relations/{cutom_list_item_relation['id']}/"
        builder_client.patch(relation_patch_url, data={'rank': rank})
        rank += 1
