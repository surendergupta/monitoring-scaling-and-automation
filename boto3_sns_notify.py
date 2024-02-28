import boto3
from botocore.exceptions import NoCredentialsError

aws_region = 'us-east-1'
sns_client = boto3.client('sns', region_name=aws_region)

def create_sns_topic(topic_name):
    # Create SNS topic
    try:
        response = sns_client.create_topic(Name=topic_name)
        topic_arn = response['TopicArn']
        print(f'SNS topic "{topic_name}" created successfully with ARN: {topic_arn}')

        return topic_arn
    except NoCredentialsError:
        print('Credentials not available.')

def subscribe_lambda_to_topic(topic_arn, lambda_function_arn, protocol='lambda'):
    try:
        sns_client.subscribe(
            TopicArn=topic_arn,
            Protocol=protocol,
            Endpoint=lambda_function_arn
        )

        print(f'Lambda function subscribed to SNS topic "{topic_arn}" successfully.')
    except NoCredentialsError:
        print('Credentials not available.')

# def subscribe_administrators1(topic_arn, protocol, endpoint):
#     response = sns_client.subscribe(
#         TopicArn=topic_arn,
#         Protocol=protocol,
#         Endpoint=endpoint
#     )
#     print(f"Subscribed administrators to SNS topic {topic_arn}")

def send_notification(topic_arn, subject, message):
    # Send a notification through SNS to administrators
    sns_client.publish(
        TopicArn=topic_arn,
        Subject=subject,
        Message=message,
    )
    print("Notification sent.")


if __name__ == '__main__':
    health_issues_topic_arn = create_sns_topic('health-issues')
    scaling_events_topic_arn = create_sns_topic('scaling-events')
    high_traffic_topic_arn = create_sns_topic('high-traffic')

    # subscribe_administrators1(health_issues_topic_arn, 'email', 'gupta.surender.1990@gmail.com')
    # subscribe_administrators1(scaling_events_topic_arn, 'sms', '+918010092484')
    # subscribe_administrators1(high_traffic_topic_arn, 'email', 'myinrbtc@gmail.com')
    # send_notification(health_issues_topic_arn, 'Health Alert', 'Health issue detected!')
    # send_notification(scaling_events_topic_arn, 'Scaling Alert', 'Scaling event triggered!')
    # send_notification(high_traffic_topic_arn, 'High traffic Alert', 'High traffic detected!')

    lambda_function_arn = 'your-lambda-function-arn'

    subscribe_lambda_to_topic(health_issues_topic_arn, lambda_function_arn)
    subscribe_lambda_to_topic(scaling_events_topic_arn, lambda_function_arn)
    subscribe_lambda_to_topic(high_traffic_topic_arn, lambda_function_arn)

