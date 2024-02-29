import boto3
from datetime import datetime

aws_region = 'us-east-1'
elbv2_client = boto3.client('elbv2', region_name=aws_region)
ec2_client = boto3.client('ec2', region_name=aws_region)
sns_client = boto3.client('sns', region_name=aws_region)

elb_name = 'arn:aws:elasticloadbalancing:us-east-1:060095847722:loadbalancer/app/suri-tm-lb/a0b625daa05bd7e2'
admin_notification_topic_arn = 'arn:aws:sns:us-east-1:060095847722:AdminNotifications'
health_issues_topic_arn = 'arn:aws:sns:us-east-1:060095847722:health-issues'
scaling_events_topic_arn = 'arn:aws:sns:us-east-1:060095847722:high-traffic'
high_traffic_topic_arn = 'arn:aws:sns:us-east-1:060095847722:scaling-events'
def lambda_handler(event, context):
    
    response = elbv2_client.describe_target_health(TargetGroupArn=elb_name)

    unhealthy_instances = [instance for instance in response['TargetHealthDescriptions'] if instance['TargetHealth']['State'] != 'healthy']
    if unhealthy_instances:
        for instance in unhealthy_instances:
            instance_id = instance['Target']['Id']

            # Retrieve information about the instance
            response = ec2_client.describe_instances(InstanceIds=[instance_id])

            # Extract the EBS volume ID attached to the instance
            volume_ids = [block_device['Ebs']['VolumeId'] for reservation in response['Reservations'] for instance in reservation['Instances'] for block_device in instance['BlockDeviceMappings']]

            if volume_ids:
                # Create snapshots for the retrieved volume IDs
                for volume_id in volume_ids:
                    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                    snapshot_name = f"FEDebug_snapshot_{volume_id}_{timestamp}"
                    snapshot = ec2_client.create_snapshot(VolumeId=volume_id, Description=f"{snapshot_name}")

                    # Build a detailed message about unhealthy instances and snapshots
                    message = f"Instance ID: {instance_id} is unhealthy.\n"
                    message += f"Snapshot ID: {snapshot['SnapshotId']} with name '{snapshot_name}' has been created for volume {volume_id}.\n"

                    # Terminate the unhealthy instance
                    ec2_client.terminate_instances(InstanceIds=[instance_id])

                    # Publish the message to the SNS topic
                    sns_client.publish(
                        TopicArn=health_issues_topic_arn,
                        Message=message,
                        Subject="ELB Unhealthy Instances Alert"
                    )
    return {
        'statusCode': 200,
        'body': 'Hello from Lambda!'
    }