#!/usr/bin/env python3
"""
Launch distributed PDF processing workers on AWS EC2 Spot instances.

This script launches multiple g4dn.xlarge Spot instances, each running
the distributed worker Docker container to process PDFs in parallel.
"""

import argparse
import base64
import os
import sys
import time
from pathlib import Path
from typing import List, Dict
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class EC2WorkerLauncher:
    """Launch and manage distributed PDF processing workers on EC2."""

    def __init__(
        self,
        num_workers: int = 5,
        instance_type: str = "g4dn.xlarge",
        max_spot_price: str = "0.60",
        region: str = "eu-north-1",
        docker_image: str = "ravinala/pdf-parser:v2-distributed",
    ):
        """
        Initialize launcher.

        Args:
            num_workers: Number of parallel workers to launch
            instance_type: EC2 instance type (must have GPU)
            max_spot_price: Maximum Spot price per hour
            region: AWS region
            docker_image: Docker image to run
        """
        self.num_workers = num_workers
        self.instance_type = instance_type
        self.max_spot_price = max_spot_price
        self.region = region
        self.docker_image = docker_image

        # Initialize AWS clients
        self.ec2 = boto3.client('ec2', region_name=region)
        self.ec2_resource = boto3.resource('ec2', region_name=region)

        # Configuration from environment
        self.s3_input_bucket = os.getenv('S3_INPUT_BUCKET', 'cs433-rag-project2')
        self.s3_input_prefix = os.getenv('S3_INPUT_PREFIX', 'raw_pdfs/')
        self.s3_output_bucket = os.getenv('S3_OUTPUT_BUCKET', 'cs433-rag-project2')
        self.s3_output_prefix = os.getenv('S3_OUTPUT_PREFIX', 'processed/')
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')

    def validate_prerequisites(self) -> bool:
        """Validate that all prerequisites are met."""
        print("Validating prerequisites...")

        # Check AWS credentials
        if not self.aws_access_key or not self.aws_secret_key:
            print("❌ AWS credentials not found in environment")
            print("   Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
            return False
        print("✓ AWS credentials found")

        # Check IAM role exists
        iam = boto3.client('iam')
        role_name = 'pdf-processing-user'
        try:
            iam.get_role(RoleName=role_name)
            print(f"✓ IAM role '{role_name}' exists")
        except ClientError:
            print(f"❌ IAM role '{role_name}' not found")
            print(f"   Create it with: python scripts/setup_aws_infrastructure.py")
            return False

        # Check Deep Learning AMI
        try:
            response = self.ec2.describe_images(
                Filters=[
                    {'Name': 'name', 'Values': ['Deep Learning AMI GPU PyTorch *']},
                    {'Name': 'state', 'Values': ['available']},
                ],
                Owners=['amazon'],
                MaxResults=1
            )
            if response['Images']:
                print(f"✓ Deep Learning AMI found: {response['Images'][0]['ImageId']}")
            else:
                print("❌ No Deep Learning AMI found")
                return False
        except ClientError as e:
            print(f"❌ Error checking AMI: {e}")
            return False

        print("✓ All prerequisites validated\n")
        return True

    def get_latest_deep_learning_ami(self) -> str:
        """Get the latest Deep Learning AMI ID."""
        response = self.ec2.describe_images(
            Filters=[
                {'Name': 'name', 'Values': ['Deep Learning AMI GPU PyTorch * (Ubuntu 22.04)*']},
                {'Name': 'state', 'Values': ['available']},
            ],
            Owners=['amazon']
        )

        # Sort by creation date and get latest
        images = sorted(response['Images'], key=lambda x: x['CreationDate'], reverse=True)
        return images[0]['ImageId'] if images else None

    def create_user_data_script(self, worker_id: int) -> str:
        """
        Create User Data script for EC2 instance.

        Args:
            worker_id: Unique worker ID (0-indexed)

        Returns:
            User Data script as string
        """
        script = f"""#!/bin/bash
set -e

# Log everything
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "=========================================="
echo "PDF Worker {worker_id} - Starting Setup"
echo "=========================================="

# Pull Docker image
echo "Pulling Docker image..."
docker pull {self.docker_image}

# Run worker container
echo "Starting worker container..."
docker run --gpus all --rm \\
  -e WORKER_ID={worker_id} \\
  -e TOTAL_WORKERS={self.num_workers} \\
  -e S3_INPUT_BUCKET={self.s3_input_bucket} \\
  -e S3_INPUT_PREFIX={self.s3_input_prefix} \\
  -e S3_OUTPUT_BUCKET={self.s3_output_bucket} \\
  -e S3_OUTPUT_PREFIX={self.s3_output_prefix} \\
  -e AWS_ACCESS_KEY_ID={self.aws_access_key} \\
  -e AWS_SECRET_ACCESS_KEY={self.aws_secret_key} \\
  -e AWS_DEFAULT_REGION={self.region} \\
  {self.docker_image}

# Worker completed - shut down instance
echo "Worker {worker_id} completed successfully"
echo "Shutting down instance..."
shutdown -h now
"""
        return script

    def launch_workers(self, dry_run: bool = False) -> List[str]:
        """
        Launch EC2 Spot instances for all workers.

        Args:
            dry_run: If True, don't actually launch instances

        Returns:
            List of instance IDs
        """
        if dry_run:
            print("🔍 DRY RUN MODE - No instances will be launched\n")

        # Get latest AMI
        ami_id = self.get_latest_deep_learning_ami()
        print(f"Using AMI: {ami_id}\n")

        instance_ids = []

        for worker_id in range(self.num_workers):
            print(f"Launching worker {worker_id}/{self.num_workers - 1}...")

            user_data = self.create_user_data_script(worker_id)
            user_data_b64 = base64.b64encode(user_data.encode()).decode()

            if dry_run:
                print(f"  Would launch instance for worker {worker_id}")
                print(f"  User Data (preview):\n{user_data[:200]}...\n")
                continue

            try:
                # Launch Spot instance
                response = self.ec2.request_spot_instances(
                    InstanceCount=1,
                    Type='one-time',
                    SpotPrice=self.max_spot_price,
                    LaunchSpecification={
                        'ImageId': ami_id,
                        'InstanceType': self.instance_type,
                        'KeyName': os.getenv('AWS_KEY_PAIR'),  # Optional
                        'IamInstanceProfile': {
                            'Name': 'pdf-processing-user'
                        },
                        'SecurityGroups': ['default'],
                        'UserData': user_data_b64,
                        'BlockDeviceMappings': [
                            {
                                'DeviceName': '/dev/sda1',
                                'Ebs': {
                                    'VolumeSize': 125,
                                    'VolumeType': 'gp3',
                                    'DeleteOnTermination': True
                                }
                            }
                        ],
                        'TagSpecifications': [
                            {
                                'ResourceType': 'instance',
                                'Tags': [
                                    {'Key': 'Name', 'Value': f'pdf-worker-{worker_id}'},
                                    {'Key': 'Project', 'Value': 'pdf-processing'},
                                    {'Key': 'WorkerID', 'Value': str(worker_id)},
                                ]
                            }
                        ]
                    }
                )

                spot_request_id = response['SpotInstanceRequests'][0]['SpotInstanceRequestId']
                print(f"  ✓ Spot request created: {spot_request_id}")

                # Wait a bit for request to be fulfilled
                time.sleep(2)

            except ClientError as e:
                print(f"  ❌ Error launching worker {worker_id}: {e}")
                continue

        if not dry_run:
            print(f"\n✅ Launched {len(instance_ids)} workers")
            self.print_monitoring_commands()

        return instance_ids

    def print_monitoring_commands(self):
        """Print commands to monitor workers."""
        print("\n" + "="*60)
        print("MONITORING COMMANDS")
        print("="*60)
        print("\n# Check Spot requests:")
        print(f"aws ec2 describe-spot-instance-requests --region {self.region} \\")
        print("  --filters Name=tag:Project,Values=pdf-processing")
        print("\n# Check running instances:")
        print(f"aws ec2 describe-instances --region {self.region} \\")
        print("  --filters Name=tag:Project,Values=pdf-processing Name=instance-state-name,Values=running")
        print("\n# Monitor progress in S3:")
        print(f"aws s3 ls s3://{self.s3_output_bucket}/{self.s3_output_prefix} | wc -l")
        print("\n# View logs (replace INSTANCE_ID):")
        print("aws ssm start-session --target INSTANCE_ID")
        print("sudo tail -f /var/log/user-data.log")
        print("\n" + "="*60 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Launch distributed PDF processing workers on AWS EC2'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=5,
        help='Number of workers to launch (default: 5)'
    )
    parser.add_argument(
        '--instance-type',
        default='g4dn.xlarge',
        help='EC2 instance type (default: g4dn.xlarge)'
    )
    parser.add_argument(
        '--max-price',
        default='0.30',
        help='Maximum Spot price per hour (default: $0.30)'
    )
    parser.add_argument(
        '--region',
        default='eu-north-1',
        help='AWS region (default: eu-north-1)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode - do not actually launch instances'
    )

    args = parser.parse_args()

    # Create launcher
    launcher = EC2WorkerLauncher(
        num_workers=args.workers,
        instance_type=args.instance_type,
        max_spot_price=args.max_price,
        region=args.region
    )

    # Validate prerequisites
    if not launcher.validate_prerequisites():
        print("\n❌ Prerequisites not met. Please fix the issues above.")
        sys.exit(1)

    # Confirm launch
    if not args.dry_run:
        print(f"\n⚠️  About to launch {args.workers} Spot instances:")
        print(f"   Instance type: {args.instance_type}")
        print(f"   Max price: ${args.max_price}/hour")
        print(f"   Region: {args.region}")
        print(f"   Estimated cost: ~${float(args.max_price) * args.workers * 40:.2f} for 40 hours")
        print()
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)

    # Launch workers
    launcher.launch_workers(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
