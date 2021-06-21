# About
This project contains code for syncing Google Drive data with a Guidebook Guide.

# Setup
### What you will need
1. An [Amazon Web Services (AWS) account](https://aws.amazon.com/)
2. A Guide set up in [Builder](https://builder.guidebook.com/) with an empty CustomList
3. An API key from Builder
4. A Google Drive folder
5. A Google Cloud Platform project

## Environment Setup
1. Create a [virtualenv](https://virtualenv.pypa.io/en/stable/) and run `pip install -r requirements.txt` to get the package dependencies.

## Initial Data Load
This project uses a scheduled Google Drive lambda to add, update and remove files as CustomListItems in Builder. However, an initial data load must be performed to populate the guide with data.

**Steps to load data:**
1. Update all of the values in `settings.py` to your settings
2. Run `python data_loader.py` from within your virtualenv.

## Google Drive Setup
1. Create a Google Cloud Platform project
2. In IAM and Admin for this project, create a [service account](https://cloud.google.com/iam/docs/creating-managing-service-accounts). This will be used for authentication.
3. Under the new service account, create a private JSON key. Download the key - the contents will be used in settings and parameter store to authenticate the requests to Google Drive.
4. In APIs and Services for this project, enable the Google Drive API.
5. In Google Drive, navigate to the folder that contains the files you want uploaded to CustomListItems in Builder. Share the folder with your service account.

## Lambdas Setup
**Steps to setup lambdas:**
1. Login to your AWS account and create a new [lambdas](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html) 
2. Create a [deployment package](https://docs.aws.amazon.com/lambda/latest/dg/python-package-create.html#python-package-create-with-dependency) for your lambda and either upload the package to AWS via the console or using [lambda-uploader](https://github.com/rackerlabs/lambda-uploader)
The lambda code is contained in: `drive_webhook_receiver.py`
3. [Schedule your lambda](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/RunLambdaSchedule.html) to run every five minutes.
4. Add the following parameters to AWS Systems Manager (Parameter Store)

| Name | Type | Value |
| ----------- | ----------- | ----------- |
| `/lambdas/googledrivewebhookreceiver/api_key` | SecureString| Your Builder API key |
| `/lambdas/googledrivewebhookreceiver/guide_and_list_ids` | String | List of guide and custom list ids to update in Builder, ex: (<guide1_id>, <list1_id>), (<guide2_id>, <list2_id>)|
| `/lambdas/googledrivewebhookreceiver/service_account_credentials` | SecureString | The credentials dictionary for your service account generated for the project. |

5. Deploy the lambda.
