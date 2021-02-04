import boto3
import json


TABLE_NAME = 'QCSummary'
dynamodb_resource = boto3.resource('dynamodb')
table = dynamodb_resource.Table(TABLE_NAME)

def lambda_handler(event, context):
    """ Review the processing summary data for the group/stream and assign total pass/fail. 
        Two options are presented:
          1. Read the summary item from the db table (a conventional approach).
          2. Read the outputs of the previous steps, using StepFunction input/output.
    """

    # This can show that this step receives a list of outputs from the 3 parallel steps
    print(f"Received event {event}")

    # Option #1. Read the summary row in the db table
    end_item_db = read_summary_from_db(event)
    # Option 2: Read the step function output from the previous processing steps
    end_item_input = read_summary_from_input(event)

    status_code = set_total_pass_flag(end_item_input)
    end_item_db['StatusCode'] = status_code
    end_item_input['StatusCode'] = status_code
    return end_item_input

def read_summary_from_db(event):
    """ Read the summary item from the table and assign total pass/fail """
    process_flags =  ['Process1Pass', 'Process2Pass', 'Process3Pass']
    end_item = get_end_item_from_input(event, process_flags)

    key = get_key_from_item(end_item)
    response = table.get_item(Key=key)
    status_code = response['ResponseMetadata']['HTTPStatusCode']
    if response['Item'] is not None:
        summary_item = response['Item']
        for flag in ['Process1Pass', 'Process2Pass', 'Process3Pass']:
            if (flag in summary_item.keys()):
                end_item[flag] = summary_item[flag]

    if end_item['Process1Pass'] == 1 and end_item['Process2Pass'] == 1 and end_item['Process3Pass'] ==1 :
        end_item['TotalPass'] = 1
    
    end_item['StatusCode'] = status_code
    print(f"Response code: {status_code}")
    return end_item

   
def read_summary_from_input(event):
    """ Read the parallel step outputs and assign total pass/fail """
    process_flags =  ['Process1Pass', 'Process2Pass', 'Process3Pass']

    end_item = get_end_item_from_input(event, process_flags)

    for process_item in event:
        for flag in ['Process1Pass', 'Process2Pass', 'Process3Pass']:
            if (flag in process_item.keys()):
                end_item[flag] = process_item[flag]

    if end_item['Process1Pass'] == 1 and end_item['Process2Pass'] == 1 and end_item['Process3Pass'] ==1 :
        end_item['TotalPass'] = 1
            
    return end_item


def set_total_pass_flag(end_item):
    """ Update the total pass flag for the summary item in the db """
    key = get_key_from_item(end_item)
    response = table.update_item(
        Key=key,
        UpdateExpression="set TotalPass=:p",
        ExpressionAttributeValues={
            ':p': end_item['TotalPass']
        },
        ReturnValues="UPDATED_NEW"
    )
    status_code = response['ResponseMetadata']['HTTPStatusCode']
    return status_code


def get_end_item_from_input(event, process_flags):
    """ Parse the input event to create the end_item """
    end_item = {
        'GroupID':event[0]['GroupID'],
        'StreamID': event[0]['StreamID'],
        'StartTime': event[0]['StartTime'],
        'QCPID': event[0]['QCPID'],
        'TotalPass': 0
    }
    for flag in process_flags:
        end_item[flag] = 0

    return end_item

def get_key_from_item(item):
    key = {
        'GroupID': item['GroupID'],
        'StartTime': item['StartTime']
    }
    return key


if __name__ == '__main__':
    with open('test_payloads/end-qc-event.json', 'r') as file:
        data = file.read()
        event = json.loads(data)
    lambda_handler(event, 'context')