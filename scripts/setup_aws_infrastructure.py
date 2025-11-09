#!/usr/bin/env python3
"""
Set up AWS infrastructure for distributed PDF processing.

Creates necessary IAM roles and security groups.
"""

import boto3
import json
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def create_iam_role():
    """Create IAM role for EC2 instances to access S3."""
    iam = boto3.client('iam')
    role_name = 'pdf-processing-user'

    # Trust policy for EC2
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }

    # S3 access policy
    s3_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket",
                    "s3:HeadObject"
                ],
                "Resource": [
                    "arn:aws:s3:::cs433-rag-project2/*",
                    "arn:aws:s3:::cs433-rag-project2"
                ]
            }
        ]
    }

    try:
        # Create role
        print(f"Creating IAM role: {role_name}")
        iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for EC2 instances to access S3 for PDF processing'
        )
        print(f"✓ Created role: {role_name}")

        # Attach inline policy
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName='S3Access',
            PolicyDocument=json.dumps(s3_policy)
        )
        print(f"✓ Attached S3 policy")

        # Create instance profile
        iam.create_instance_profile(
            InstanceProfileName=role_name
        )
        print(f"✓ Created instance profile")

        # Add role to instance profile
        iam.add_role_to_instance_profile(
            InstanceProfileName=role_name,
            RoleName=role_name
        )
        print(f"✓ Added role to instance profile")

    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print(f"ℹ️  Role {role_name} already exists")
        else:
            print(f"❌ Error creating role: {e}")
            raise


def main():
    """Set up AWS infrastructure."""
    print("Setting up AWS infrastructure for PDF processing\n")
    print("="*60)

    # Create IAM role
    create_iam_role()

    print("\n" + "="*60)
    print("✅ AWS infrastructure setup complete!")
    print("\nNext steps:")
    print("1. Run: python scripts/launch_distributed_workers.py --dry-run")
    print("2. If dry-run looks good:")
    print("   python scripts/launch_distributed_workers.py")


if __name__ == '__main__':
    main()
