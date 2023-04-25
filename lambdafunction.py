import boto3
import os
import time
import json


ec2 = boto3.client('ec2')
ssm = boto3.client('ssm')
ses = boto3.client('ses')


AMI_ID = 'ami-0c768662cc797cd75'
INSTANCE_TYPE = 't2.micro'
KEY_NAME = 'firstkey'
SECURITY_GROUP_IDS = ['sg-0952cfb107706af85']
USER_DATA = '''
#!/bin/bash
sudo yum update -y
sudo amazon-linux-extras install nginx -y
'''

def lambda_handler(event, context):
    instance_id = None
    try:
        instance_id = os.environ['INSTANCE_ID']
    except KeyError:
        pass
    
    if instance_id:
        
        response = ec2.describe_instances(InstanceIds=[instance_id])
        state = response['Reservations'][0]['Instances'][0]['State']['Name']
        
        if state != 'running':
            instance_id = None
    
    if not instance_id:
        
        response = ec2.run_instances(
            ImageId=AMI_ID,
            InstanceType=INSTANCE_TYPE,
            KeyName=KEY_NAME,
            SecurityGroupIds=SECURITY_GROUP_IDS,
            UserData=USER_DATA,
            MinCount=1,
            MaxCount=1
        )
        instance_id = response['Instances'][0]['InstanceId']
    
    ec2.get_waiter('instance_running').wait(InstanceIds=[instance_id])
    
    time.sleep(230)
    ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName='AWS-RunShellScript',
        Parameters={'commands': ['sudo yum install -y nginx', 'sudo systemctl start nginx']}
    )
    
    email_subject = 'Instance Shutdown '
    email_body = 'The software installation is complete and the instance is now shutting down.'
    recipient_email = 'sanjuaws786@gmail.com'
    sender_email = 'sanjuaws786@gmail.com'
    
    ec2.stop_instances(InstanceIds=[instance_id])
    
    ses.send_email(
        Source=sender_email,
        Destination={'ToAddresses': [recipient_email]},
        Message={
            'Subject': {'Data': email_subject},  
            'Body': {'Text': {'Data': email_body}}
        }
    )
    
    return {
        'statusCode': 200,
        'body': 'Instance has been stopped and email has been sent'
    }
