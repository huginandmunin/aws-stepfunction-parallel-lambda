import boto3
import time
import json

TABLE_NAME = 'QCSummary'
dynamodb_resource = boto3.resource('dynamodb')
table = dynamodb_resource.Table(TABLE_NAME)

def lambda_handler(event, context):
    """ Perform QC process #3. Update flag in summary table """

    group_id = event['GroupID']
    start_time = event['StartTime']
    stream_id = event['StreamID']
    qc_pid = event['QCPID']
    key = {
        'GroupID': group_id,
        'StartTime': start_time
    }
    process_item = {
        'ProcessName': 'QCProcess3',
        'GroupID': group_id,
        'StartTime': start_time,
        'QCPID': qc_pid,
        'StreamID': stream_id
    }
    pass_fail = check_data_process3(group_id,stream_id)
    process_item['Process3Pass'] = pass_fail
    # Fake some processing time with a sleep 
    time.sleep(2)

    response = table.update_item(
        Key=key,
        UpdateExpression="set Process3Pass=:p",
        ExpressionAttributeValues={
            ':p': pass_fail
        },
        ReturnValues="UPDATED_NEW"
    )
    print(f"Response {response}")

    return process_item

    
def check_data_process3(group_id,stream_id):
    """ Process QC checks #3 for group/stream and mark as pass/fail """
    passfail = 1
    return passfail


if __name__ == '__main__':
    with open('test_payloads/qc-process-event.json', 'r') as file:
        data = file.read()
        event = json.loads(data)
    lambda_handler(event, 'context')