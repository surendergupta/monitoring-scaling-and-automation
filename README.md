# Web Application Lifecycle Management System

This project implements a system that automatically manages the lifecycle of a web application hosted on EC2 instances, monitors its health, and reacts to changes in traffic by scaling resources. Furthermore, administrators receive notifications regarding the infrastructure's health and scaling events.

## Detailed Breakdown

1. **Web Application Deployment**
    - Use `boto3` to:
        - Create an S3 bucket to store your web application's static files.
        - Launch an EC2 instance and configure it as a web server (e.g., Apache, Nginx).
        - Deploy the web application onto the EC2 instance.

2. **Load Balancing with ELB**
    - Deploy an Application Load Balancer (ALB) using `boto3`.
    - Register the EC2 instance(s) with the ALB.

3. **Auto Scaling Group (ASG) Configuration**
    - Using `boto3`, create an ASG with the deployed EC2 instance as a template.
    - Configure scaling policies to scale in/out based on metrics like CPU utilization or network traffic.

4. **Lambda-based Health Checks & Management**
    - Develop a Lambda function to periodically check the health of the web application (through the ALB).
    - If the health check fails consistently, the Lambda function should:
        - Capture a snapshot of the failing instance for debugging purposes.
        - Terminate the problematic instance, allowing the ASG to replace it.
        - Send a notification through SNS to the administrators.

5. **S3 Logging & Monitoring**
    - Configure the ALB to send access logs to the S3 bucket.
    - Create a Lambda function that triggers when a new log is added to the S3 bucket. This function can analyze the log for suspicious activities (like potential DDoS attacks) or just high traffic.
    - If any predefined criteria are met during the log analysis, the Lambda function sends a notification via SNS.

6. **SNS Notifications**
    - Set up different SNS topics for different alerts (e.g., health issues, scaling events, high traffic).
    - Integrate SNS with Lambda so that administrators receive SMS or email notifications.

7. **Infrastructure Automation**
    - Create a single script using `boto3` that:
        - Deploys the entire infrastructure.
        - Updates any component as required.
        - Tears down everything when the application is no longer needed.

## Usage

To use this project:

1. Clone the repository.
2. Install the necessary dependencies (`boto3`, etc.).
3. Run the provided script to deploy the infrastructure.
4. Follow any additional instructions provided in the code or documentation for configuring specific components or customizing the setup.
