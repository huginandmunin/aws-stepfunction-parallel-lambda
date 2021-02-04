import boto3
import json

TOPIC_ARN = 'arn:aws:sns:MY-REGION:MY-ACCOUNT-ID:qc-results-group1'
sns = boto3.client('sns')

def lambda_handler(event, context):
    """ Send a pass/fail summary to the SNS topic for this group """

    # For the demo we just use a single topic for all messages. In prod you might use a topic for each group id. 
    topic_arn = TOPIC_ARN
    # Nothing fancy for the message for the demo: the output from the end-qc lambda
    message = json.dumps(event)

    response = sns.publish(
        TopicArn=topic_arn,
        Message=message
    )
    status_code = response['ResponseMetadata']['HTTPStatusCode']
    return status_code


if __name__ == '__main__':
    with open('test_payloads/send-qc-summary-event.json', 'r') as file:
        data = file.read()
        event = json.loads(data)
    lambda_handler(event, 'context')