import boto3
import openpyxl
from botocore.exceptions import NoCredentialsError


aws_region = 'us-east-1'
ec2_client = boto3.client('ec2', region_name=aws_region)
sns_client = boto3.client('sns', region_name=aws_region)
elbv2_client = boto3.client('elbv2', region_name=aws_region)
asg_client = boto3.client('autoscaling', region_name=aws_region)

def get_alb_arn_from_xlsx_file():
    filename= 'elb_info.xlsx'
    dataframe = openpyxl.load_workbook(filename)
    dataframe1 = dataframe.active    
    value = dataframe1.cell(row=4, column=2).value
    return value
    
# ALB and ASG configuration
alb_target_group_arn = get_alb_arn_from_xlsx_file()
asg_name = 'suri-tm-asg'
snapshot_description = 'WebAppFailureSnapshot'
topic_name = 'AdminNotifications'
def createSNSToptic():
    response = sns_client.create_topic(Name=topic_name)
    topic_arn = response['TopicArn']
    print("SNS topic ARN:", topic_arn)

    sns_client.set_topic_attributes(
        TopicArn=topic_arn,
        AttributeName='DisplayName',
        AttributeValue='Admin Notifications'
    )

    response = sns_client.subscribe(
        TopicArn=topic_arn,
        Protocol='email',
        Endpoint='gupta.surender.1990@gmail.com'
    )

    print("Subscription ARN:", response['SubscriptionArn'])

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

def capture_instance_snapshot(instance_id):
    # Create snapshot with a descriptive name
    snapshot_description = f"Snapshot for troubleshooting instance {instance_id}"
    snapshot = ec2_client.create_snapshot(VolumeId=instance_id, Description=snapshot_description)
    snapshot_id = snapshot['SnapshotId']
    print(f"Snapshot created: {snapshot_id}")
    return snapshot_id

def terminate_instance(instance_id):
    # Terminate instance
    ec2_client.terminate_instances(InstanceIds=[instance_id])
    print(f"Instance terminated: {instance_id}")

def send_notification(instance_id, snapshot_id):
    # GET SNS topic ARN
    topic_arn = getTopicArn()
    # Send a notification through SNS to administrators
    sns_client.publish(
        TopicArn=topic_arn,
        Subject='Web Application Health Check Alert',
        Message=f'Web application health check failed for instance {instance_id}. Instance terminated. Snapshot ID: {snapshot_id}',
    )


def lambda_handler(event, context):
    try:
        # Describe target health for the ALB
        response = elbv2_client.describe_target_health(TargetGroupArn=alb_target_group_arn)
        
        for target in response['TargetHealthDescriptions']:
            target_id = target['Target']['Id']
            target_health = target['TargetHealth']['State']            
            
            ec2_response = ec2_client.describe_instances(InstanceIds=[target_id])
            volume_id = ec2_response['Reservations'][0]['Instances'][0]['BlockDeviceMappings'][0]['Ebs']['VolumeId']
            print("Volume ID:", volume_id)

            if target_health == 'unhealthy':
                print(f'Instance {target_id} is unhealthy. Taking corrective actions...')
                
                # Capture snapshot
                snapshot_id = capture_instance_snapshot(volume_id)

                # Terminate instance
                terminate_instance(target_id)
                
                # Terminate the problematic instance                
                # Send notification
                send_notification(target_id, snapshot_id)                
                
                print('Notification sent to administrators.')
            else:
                print('All Instance is Healthy no need to send notification to administrators.')
    except NoCredentialsError:
        print('Catch error in lambda function.')
if __name__ == '__main__':
    # Test the Lambda function locally
    #createSNSToptic()
    lambda_handler({}, {})