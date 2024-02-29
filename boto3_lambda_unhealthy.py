import boto3
import zipfile

aws_region = 'us-east-1'
lambda_client = boto3.client('lambda', region_name=aws_region)
events_client = boto3.client('events', region_name=aws_region)

function_code_file = 'lambda_function.py'
zip_file = 'lambda_function.zip'

with zipfile.ZipFile(zip_file, 'w') as z:
    z.write(function_code_file)

with open(zip_file, 'rb') as file:
    lambda_code = file.read()

function_name = 'boto3LambdaFuntion'
role_arn = 'arn:aws:iam::060095847722:role/lambda-role-boto3'  # Replace with your existing IAM role ARN

response = lambda_client.create_function(
    FunctionName=function_name,
    Runtime='python3.10',
    Role=role_arn,
    Handler='lambda_function.lambda_handler',  # Replace 'backup' with your script's filename (without the extension)
    Code={
        'ZipFile': lambda_code,
    }
)

response1 = lambda_client.get_function(FunctionName=function_name)

lambda_arn = response1['Configuration']['FunctionArn']

print(f"The ARN of the Lambda function '{function_name}' is: {lambda_arn}")

response = events_client.put_rule(
    Name='TriggerLambdaEvery10Minutes',
    ScheduleExpression='rate(10 minutes)',
    State='ENABLED'
)

rule_arn = response['RuleArn']

print(f'The ARN of the created rule is: {rule_arn}')

response1 = lambda_client.add_permission(
    FunctionName=function_name,
    StatementId='AllowCloudWatchToInvokeLambda',
    Action='lambda:InvokeFunction',
    Principal='events.amazonaws.com',
    SourceArn=response['RuleArn']
)

response = events_client.put_targets(
    Rule='TriggerLambdaEvery10Minutes',
    Targets=[
        {
            'Id': '1',
            'Arn': lambda_arn,  # Use the variable containing the rule ARN
            'Input': '{}'
        }
    ]
)