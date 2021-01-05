import boto3
from dotenv import load_dotenv
import os
from boto3.dynamodb.conditions import Key, Attr
import time
from datetime import datetime, timezone

load_dotenv()

dynamo_client = boto3.client('dynamodb')
dynamo_db = boto3.resource('dynamodb')

req_table_name = ""

for tableName in dynamo_client.list_tables()['TableNames']:
  if(tableName.split('-')[0] == "Requisition"):
    req_table_name = tableName

req_table = dynamo_db.Table(req_table_name)

res = req_table.query(
  KeyConditionExpression=Key('device_id').eq(os.environ.get('DEVICE_ID'))
)['Items']

# time.strftime("%m/%d/%Y, %I:%M:%S %p", time.localtime(1609838590638 / 1000 + 19800))
# res = req_table.put_item(
#   Item={
#     'device_id': os.environ.get('DEVICE_ID'),
#     'requisition_id': '3',
#     'calibration_id': '1_2',
#     '_version': 1,
#     '_lastChangedAt': int(time.time() * 1000),
#     'createdAt': datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
#     'updatedAt': datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
#   }
# )

print(res)