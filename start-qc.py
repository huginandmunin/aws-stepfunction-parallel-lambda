import boto3
import json
import datetime
import uuid

TABLE_NAME = 'QCSummary'
dynamodb_resource = boto3.resource('dynamodb')
table = dynamodb_resource.Table(TABLE_NAME)

def lambda_handler(event, context):
    """ Start the QC process by creating a new row in the QC summary table """

    # TODO
    # check that GroupID and StreamID are present in input

    print(f"Received event {event}")

    group_id = event['GroupID']
    stream_id = event['StreamID']
    qc_pid = str(uuid.uuid1())
    start_time = datetime.datetime.now().isoformat()
    # create summary_item for new table row
    summary_item = {
        'GroupID': group_id,
        'StartTime': start_time,
        'QCPID': qc_pid,
        'StreamID': stream_id
    }

    response = table.put_item(Item=summary_item)
    summary_item['StatusCode'] = response['ResponseMetadata']['HTTPStatusCode']

    return summary_item


if __name__ == '__main__':
    with open('test_payloads/start-qc-event.json', 'r') as file:
        data = file.read()
        event = json.loads(data)
    lambda_handler(event, 'context')