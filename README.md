# Create a StepFunction with parallel steps and DynamoDB interaction

In this project we will build a StepFunction state machine with a sequential and parallel processing steps. 
Each step invokes a lambda function. 
The lambda functions interact with a DynamoDB table. 
One step sends a summary message to a SNS topic. 

## Scenario

The scenario is a data QC process with sequential and parallel processes. 

The data could come from entities with several data streams. Examples are vendors/products, hospitals/patients, and weather-stations/sensors. We will use generic terms "group" and "stream". 

## Solution

We will implement a StepFunction state machine to orchestrate the workflow. 
Each step in the workflow will invoke a lambda function. 
One lambda function will create a new item for a QC Summary table in DynamoDB. Other lambda functions will update this new item. 
There is also a lambda function for sending a summary message to an SNS topic. 

The implementation was based on this AWS tutorial:
https://docs.aws.amazon.com/step-functions/latest/dg/tutorial-creating-lambda-state-machine.html

## Implementation

The step function will receive as input a group-id and a stream-id which identifies the data to process. For the demo we are simply going to flag the data as passing each QC process. 

The implementation models the following steps.

1. Seed a QC summary row for the group/stream in a DynamoDB table. 
2. Get the stream data for the group (not implemented in the demo).
3. Pass the data to the 3 parallel qc processes.
4. Each QC process will mark a pass/fail attribute in the DynamoDB summary table. They could also store QC messages in a QC details table (not implemented in the demo). 
5. After the 3 parallel scripts are finished, a collector script will check if the data passes all 3 of the parallel steps. It will update a total-pass/fail attribute in the summary table. The total-pass is also sent to the summary-sender script. 
6. A sender script will send summary pass/fail results to a SNS topic. 

## Steps to build the demo

### 1. Create the state machine structure

Let's first create a basic state machine without invoking any lambdas. The structure is contained in the Version 1 template json file,

```
step-function-template-v1.json
```

Notice that each step defines it's type as pass:

```
"Type": "Pass",
```

The means that each step will simply pass through without any functionality. 

In the Step Function console, select ```Create state machine```. Leave the defaults of ```Author with code snippets``` and Type = ```Standard```. Remove the default text from the json editor box. Paste the contents of the ```step-function-template-v1.json``` file into the json editor. Click on ```Next```.

Enter a name for the state machine, such as ```QCProcess```. Leave the default of ```Create new role```. Click on ```Create state machine```.

Let's execute the state function. Click on ```Start execution```. The default input is fine for now. Success!

Next we move on to creating the resources for the demo project.

### 2. Create the DynamoDB table

The QC summary table will hold a summary item for each QC processing run. 
The primary key is the GroupID and the sort key is the processing StartTime.  

The file ```create-table-qcsummary.json``` can be used to create the table from the command line:

```
aws dynamodb create-table --cli-input-json file://create-table-qcsummary.json --region us-east-1
```

Change the ```--region``` value if you are not working in ```us-east-1```.

The new table can be viewed in the DynamoDB console. 

A QC details table could also be created in a similar manner, from the file:

```
create-table-qcdetails.json
```

This table holds the QC messages that are generated from the parallel processing step. The message storage is not yet implemented in the demo. 

### 3. Create the SNS topic

Create the SNS directly from the command line:

```
aws sns create-topic --name qc-results-group1
```

This should return the TopicArn with the format

```
{
    "TopicArn": "arn:aws:sns:MY-REGION:MY-ACCOUNT-ID:qc-results-group1"
}
```

where ```MY-REGION:MY-ACCOUNT-ID``` corresponds to your region and account id. 

Let's test out the SNS topic. First subscribe your email to the topic via the command line:

```
aws sns subscribe --topic-arn arn:aws:sns:MY-REGION:MY-ACCOUNT-ID:qc-results-group1 --protocol email --notification-endpoint MY-EMAIL
```

Go to your email and look for the AWS confirmation request email. Confirm your subscription. You can now send a test message from the command line, something like

```
aws sns publish --topic-arn arn:aws:sns:MY-REGION:MY-ACCOUNT-ID:qc-results-group1 --message "Testing my SNS topic for my StepFunction"
```
The message should appear in your email. 

We're only going to use this one topic for the demo. In production you might have a topic for each GroupID. 

### 4. Create IAM roles for the lambda functions

The lambda functions will need permission to interact with DynamoDB and to send messages to SNS. This can be granted by an IAM lambda role. 

If you do not already have a lambda role, then one can be created in the in the IAM console. After creating the role, you can go to Permissions and add the AWS Managed policies for lambda-execute (AWSLambdaExecute), DynamoDB (AmazonDynamoDBFullAccess) and SNS (AmazonSNSFullAccess).

This single role is okay for the demo. A better approach for a production implementation would be 1 role with DynamoDB access and another role with only SNS access. 

### 5. Create the lambda functions

The code for the lambda functions are in the python scripts in the demo project. 

The only script that needs updating is the ```send-qc-summary.py```. You should update the value of the TOPIC_ARN to use the ARN of the SNS topic that you created,

```
TOPIC_ARN = 'arn:aws:sns:MY-REGION:MY-ACCOUNT-ID:qc-results-group1'
```
updating MY-REGION and MY-ACCOUNT-ID as needed. 

You might want to test the functions locally from the command line before deploying. Let's start with the ```start-qc.py``` script,

```
python start-qc.py
```

This will read a GroupID and StreamID from the test payload and put an item in the QCSummary table. The item will have a StartTime for the QC process. You can view the newly created item and StartTime from the DynamoDB console. 

The rest of the lambda functions will use this StartTime as a sort key for reading and updating the table. For additional local testing, you should update the StartTime in the test payloads in the ```test_payloads``` directory. The StartTime should match the StartTime for the item that you just created in the QC Summary table. 

As you test the scripts in succession you should see updates to the item in the QCSummary table.

The testing order should match the order that the functions are called from the StepFunction:

1. start-qc
2. qc-process1
3. qc-process2
4. qc-process3
5. end-qc
6. send-qc-summary

Lets deploy these functions via the lambda console. You should be in the same region as your DynamoDB table and the StepFunction. For each script, create a new function. Select a python run time, such as 3.7. Paste in the python code into the code text editor. For the IAM role, select the lambda role that you created earlier. The functions for the parallel steps (```qc-process1```, ```qc-process2```, ```qc-process3```) should have the timeout adjusted to 1 minute. Each function can be tested in the console using input from the json files in the test_payloads directory (ie, the same inputs that you used to test locally). 

The testing verifies that the lambda functions interact successfully with DynamoDB and SNS. Don't forget to check your email for those QC summary messages!

The later functions, ```end-qc``` and ```send-qc-summary```, have options of reading information from the DynamoDB table or from previous steps in the StepFunction. Choosing the StepFunction option results in fewer calls to the database table. 

### 6. Invoke lambda functions from the state machine

Okay, if the lambda functions test out successfully then we are ready to invoke the lambda resources from the StepFunction. 

We will use the production version of the state machine template, ```step-function-template.json``` (the one without "```-v1```" in the file name).

In this version, the type ```Pass``` has been replaced with ```Task```. We also specify a lambda ARN in each step, like this:

```
"Type": "Task",
"Resource": "arn:aws:lambda:MY-REGION:MY-ACCOUNT-ID:function:start-qc",
```

You should edit this production version of the template to put in your region and account id. With this edit we are specifying the ARN for each lambda function that was created in the lambda console. Notice that each step is invoking a different lambda function.

We can now edit the state machine template in the StepFunction console. Select your state machine in the console and select ```Edit```. Paste in the production version into the json editor. Save the new version. The console should give you an option for creating a new IAM role for the StepFunction. Select ```Create new role```. This should create a new role with invoke permission on the lambdas that have been added to the template. 

If you get any permission errors on invoking lambda then review the policy for the IAM role for the state machine. In addition to X-ray permissions, it should have permissions to invoke each lambda, as shown in the file ```step-function-invoke-lambda-policy.json```.

Time for the real test: let's try and execute the StepFunction! For the input you will need some json with a value for a GroupID and StreamID. You could use the test payload for the start-qc code:

```
{
    "GroupID": "group1",
    "StreamID": "streamA"
}
```

Maybe change the values of the GroupID and StreamID to distinguish them from the earlier test runs in your DynamoDB table. 

The StepFunction console should display the completion of the various steps. The parallel step ```qc-process2``` should take longer than the other parallel processes. (It has a larger value in the sleep function.) You will see that all 3 parallel processes have to finish before starting the following step, ```end-qc```.  

The QC Summary table should be showing a new item for every time that the state machine is executed. Don't forget to check your email for those QC summary messages that are now triggered from the step function!

## Payload pass through

This demo utilizes StepFunction input and output as a means of passing information to the lambda functions. The output of each lambda is passed on to the following lambda. 

The initial input is the GroupID and StreamID. The first function adds the StartTime and QC process id. The parallel steps add a pass/fail flag for each parallel process. The ```end-qc``` functions received a list of the outputs of the 3 parallel steps. It then adds a total pass/fail flag to the payload for the summary sending function. 

For the demo we also utilize a DynamoDB table for storing the summary information of the QC processing run. The DynamoDB table isn't totally required for the project - it is an example of how the processing history can be archived. 

## Future work

1. Handle errors in the StepFunction input (eg, missing GroupID and StreamID)
2. Create an API gateway for the StepFunction
3. Create a CloudFormation template for the demo project.
4. Develop unit tests for the lambda functions. 
