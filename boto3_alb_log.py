import boto3
import gzip
import re
import openpyxl
from botocore.exceptions import NoCredentialsError

aws_region = 'us-east-1'
s3_client = boto3.client('s3', region_name=aws_region)
sns_client = boto3.client('sns', region_name=aws_region)
elbv2_client = boto3.client('elbv2', region_name=aws_region)

def get_alb_arn_from_xlsx_file():
    filename= 'elb_info.xlsx'
    dataframe = openpyxl.load_workbook(filename)
    dataframe1 = dataframe.active    
    value = dataframe1.cell(row=4, column=1).value
    return value

alb_arn = get_alb_arn_from_xlsx_file()
topic_name = 'AdminNotifications'
s3_bucket_name = 'suri-s3-boto-scalling'

def create_bucket_if_not_exist():
    response = s3_client.list_buckets()

    for bucket in response['Buckets']:
        if bucket['Name'] == s3_bucket_name:
            return s3_bucket_name
        
    s3_client.create_bucket(
        Bucket=s3_bucket_name,
        CreateBucketConfiguration={
            'LocationConstraint': 'us-east-1'
        }
    )

    print("S3 bucket created successfully:", s3_bucket_name)

def configure_alb_logging():
    try:
        result = create_bucket_if_not_exist()
        if result:
            print("Bucket prefix:", result)
        else:
            print("Bucket created successfully.")

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
                    'Value': 'alb-access-logs',
                },
            ],
        )
        print(f'ALB access logs configured successfully. Log files will be stored in S3 bucket: {s3_bucket_name}')

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

def is_suspicious(log_line):
    ip_address = re.search(r'(\d+\.\d+\.\d+\.\d+)', log_line).group(1)
    count = log_line.count(ip_address)
    if count > 1000:
        return True
    else:
        return False

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
                if is_suspicious(log_line):
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

if __name__ == '__main__':
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