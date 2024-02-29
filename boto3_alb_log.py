import boto3
import gzip
import re
import json
import openpyxl
from botocore.exceptions import NoCredentialsError

aws_region = 'us-east-1'
s3_client = boto3.client('s3')
sns_client = boto3.client('sns', region_name=aws_region)
elbv2_client = boto3.client('elbv2', region_name=aws_region)
iam_client = boto3.client('iam', region_name=aws_region)

def get_alb_arn_from_xlsx_file():
    filename= 'elb_info.xlsx'
    dataframe = openpyxl.load_workbook(filename)
    dataframe1 = dataframe.active    
    value = dataframe1.cell(row=2, column=1).value
    return value

alb_arn = get_alb_arn_from_xlsx_file()
topic_name = 'AdminNotifications'
s3_bucket_name = 'suri-lambda-bucket'

def create_s3_bucket():
    try:
        s3_client.create_bucket(Bucket=s3_bucket_name, CreateBucketConfiguration={'LocationConstraint': aws_region})
        print(f'S3 bucket "{s3_bucket_name}" created successfully.')
    except NoCredentialsError:
        print('Credentials not available.')


def attach_s3_policy_to_role(role_name):
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "elasticloadbalancing:ModifyLoadBalancerAttributes",
                "Resource": "arn:aws:elasticloadbalancing:us-east-1:060095847722:loadbalancer/app/suri-tm-lb/a0b625daa05bd7e2"            
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetBucketLogging",
                    "s3:PutBucketLogging",
                    "s3:GetBucketAcl",
                    "s3:PutBucketAcl",
                    "s3:CreateBucket",
                    "s3:ListBucket",
                    "s3:PutObject"
                ],
                "Resource": [
                    f"arn:aws:s3:::{s3_bucket_name}",
                    f"arn:aws:s3:::{s3_bucket_name}/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject"
                ],
                "Resource": [
                    f"arn:aws:s3:::{s3_bucket_name}/*"
                ]
            }
        ]
    }

    try:
        response = iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='S3AccessPolicy',
            PolicyDocument=json.dumps(policy_document)
        )
        print(response)
        print("IAM policy attached successfully.")
    except NoCredentialsError:
        print("Credentials not available.")

def configure_alb_logging():
    try:
        attach_s3_policy_to_role('roleS3Access')

        elbv2_client.modify_load_balancer_attributes(
            LoadBalancerArn=alb_arn,
            Attributes=[
                {
                    'Key': 'access_logs.s3.enabled',
                    'Value': 'true',
                },
                {
                    'Key': 'access_logs.s3.bucket',
                    'Value': s3_bucket_name,
                },
                {
                    'Key': 'access_logs.s3.prefix',
                    'Value': 'logs',
                },
            ],
        )
        print(f'ALB access logs are configured to be stored in the specified S3 bucket. Log files will be stored in S3 bucket: {s3_bucket_name}')

    except NoCredentialsError:
        print('Credentials not available.')
    
def getTopicArn():
    response = sns_client.list_topics()
    topic_arn = None
    for topic in response['Topics']:
        # Check if the topic name matches the desired topic name        
        topic_attributes = sns_client.get_topic_attributes(TopicArn=topic['TopicArn'])
        topic_name = topic_attributes['Attributes'].get('DisplayName', topic['TopicArn'])    
        if topic_name == topic_name:
            topic_arn = topic['TopicArn']
            break
    if topic_arn is not None:
        print("ARN of the topic:", topic_arn)
        return topic_arn        
    else:
        print("Topic not found.")
        return topic_arn

def send_notification(subject, message):
    # GET SNS topic ARN
    topic_arn = getTopicArn()
    # Send a notification through SNS to administrators
    sns_client.publish(
        TopicArn=topic_arn,
        Subject=subject,
        Message=message,
    )
    print("Notification sent.")

def lambda_handler(event, context):
    for record in event['Records']:
        bucket_name = record['s3']['bucket']['name']
        object_key = record['s3']['object']['key']

        # Download the log file from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        log_data = response['Body'].read().decode('utf-8')

        if object_key.endswith('.gz'):
            log_data = gzip.decompress(log_data)

            log_lines = log_data.decode('utf-8').split('\n')
            for log_line in log_lines:
                # Analyze log line for suspicious activities or high traffic
                if is_health_issue(log_data):
                    subject = 'Web Application Health Issue detected Alert'
                    message = f"Health issue detected in log file: {object_key}"
                    send_notification(subject, message)
                    
                elif is_scaling_event(log_data):
                    subject = 'Web Application Scaling detected Alert'
                    message = f"Scaling event detected in log file: {object_key}"
                    send_notification(subject, message)
                    
                elif is_high_traffic(log_data):
                    subject = 'Web Application High Traffic detected Alert'
                    message = f'High traffic detected in ALB access log: {object_key}'
                    send_notification(subject, message)
                    
                elif is_suspicious(log_line):
                    # Send notification via SNS
                    subject = 'Web Application DDoS attack detected Alert'
                    message = 'Web application Potential DDoS attack detected.'
                    send_notification(subject, message)
        else:
            # Perform log analysis (example: check for high traffic)
            if 'HighTrafficKeyword' in log_data:
                # Send a notification via SNS
                subject = 'High Traffic Alert'
                message = f'High traffic detected in ALB access log: {object_key}'
                send_notification(subject, message)                

def is_health_issue(log_data):
    if "500 Internal Server Error" in log_data:
        return True
    
    if "CRITICAL" in log_data:
        return True
    return False

def is_scaling_event(log_data):
    if "Scaling event" in log_data:
        return True
    
    if "Increased traffic" in log_data:
        return True
    
    return False

def is_high_traffic(log_data):
    log_lines = log_data.split('\n')
    request_count = sum(1 for line in log_lines if 'GET' in line or 'POST' in line)
    traffic_threshold = 1000
    
    if request_count > traffic_threshold:
        return True
    
    ip_request_count = {}
    for line in log_lines:
        if 'GET' in line or 'POST' in line:
            ip = line.split()[0]  # Assuming IP address is the first part of the log entry
            ip_request_count[ip] = ip_request_count.get(ip, 0) + 1
    high_traffic_threshold = 100

    for ip, count in ip_request_count.items():
        if count > high_traffic_threshold:
            return True
        
    return False

def is_suspicious(log_line):
    ip_address = re.search(r'(\d+\.\d+\.\d+\.\d+)', log_line).group(1)
    count = log_line.count(ip_address)
    if count > 1000:
        return True
    else:
        return False
    
if __name__ == '__main__':

    # create bucket S3
    create_s3_bucket()

    # Configure ALB logging
    configure_alb_logging()

    # Test the Lambda function locally (dummy event)
    sample_event = {
        'Records': [
            {
                's3': {
                    'bucket': {
                        'name': s3_bucket_name,
                    },
                    'object': {
                        'key': 'sample-alb-access-log.log',
                    },
                },
            },
        ],
    }
    
    lambda_handler(sample_event, {})


#err: botocore.errorfactory.InvalidConfigurationRequestException: An error occurred (InvalidConfigurationRequest) when calling the ModifyLoadBalancerAttributes operation: Access Denied for bucket: suri-s3-boto-scalling. Please check S3bucket permission