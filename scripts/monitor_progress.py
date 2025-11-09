#!/usr/bin/env python3
"""
Monitor progress of distributed PDF processing.

Shows real-time progress of workers and S3 output.
"""

import time
import os
import boto3
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def count_s3_folders(bucket: str, prefix: str) -> int:
    """Count folders in S3 (each folder = one processed PDF)."""
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2')

    folders = set()
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter='/'):
        if 'CommonPrefixes' in page:
            for prefix_info in page['CommonPrefixes']:
                folders.add(prefix_info['Prefix'])

    return len(folders)


def get_running_workers(region: str = 'eu-north-1') -> list:
    """Get list of running worker instances."""
    ec2 = boto3.client('ec2', region_name=region)

    response = ec2.describe_instances(
        Filters=[
            {'Name': 'tag:Project', 'Values': ['pdf-processing']},
            {'Name': 'instance-state-name', 'Values': ['pending', 'running']}
        ]
    )

    instances = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            worker_id = None
            for tag in instance.get('Tags', []):
                if tag['Key'] == 'WorkerID':
                    worker_id = tag['Value']
                    break

            instances.append({
                'id': instance['InstanceId'],
                'worker_id': worker_id,
                'state': instance['State']['Name'],
                'type': instance['InstanceType'],
                'launch_time': instance['LaunchTime']
            })

    return sorted(instances, key=lambda x: x.get('worker_id', ''))


def monitor(interval: int = 60):
    """
    Monitor progress continuously.

    Args:
        interval: Seconds between updates
    """
    bucket = os.getenv('S3_OUTPUT_BUCKET', 'cs433-rag-project2')
    prefix = os.getenv('S3_OUTPUT_PREFIX', 'processed/')
    total_pdfs = 4921  # Update this if you have a different count

    print(f"Monitoring PDF processing")
    print(f"S3 Bucket: s3://{bucket}/{prefix}")
    print(f"Total PDFs: {total_pdfs}")
    print(f"Update interval: {interval}s")
    print("="*80)
    print()

    try:
        while True:
            # Get worker status
            workers = get_running_workers()

            # Count processed PDFs
            processed = count_s3_folders(bucket, prefix)
            progress_pct = (processed / total_pdfs) * 100

            # Display
            print(f"\r[{datetime.now().strftime('%H:%M:%S')}] ", end='')
            print(f"Workers: {len(workers)} | ", end='')
            print(f"Processed: {processed}/{total_pdfs} ({progress_pct:.1f}%) | ", end='')

            if processed > 0:
                rate = processed / ((time.time() - start_time) / 3600)  # PDFs per hour
                remaining = total_pdfs - processed
                eta_hours = remaining / rate if rate > 0 else 0
                print(f"Rate: {rate:.1f} PDF/hr | ETA: {eta_hours:.1f}h", end='')

            print(" " * 20, end='')  # Clear rest of line
            print(end='\r')

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
        print(f"Final count: {processed}/{total_pdfs} PDFs processed ({progress_pct:.1f}%)")


def status_once():
    """Show status once and exit."""
    bucket = os.getenv('S3_OUTPUT_BUCKET', 'cs433-rag-project2')
    prefix = os.getenv('S3_OUTPUT_PREFIX', 'processed/')
    total_pdfs = 4921

    print("PDF Processing Status")
    print("="*80)

    # Workers
    workers = get_running_workers()
    print(f"\n📊 Workers: {len(workers)} running")
    for w in workers:
        uptime = (datetime.now(w['launch_time'].tzinfo) - w['launch_time']).seconds // 60
        print(f"  Worker {w['worker_id']}: {w['state']} ({w['type']}) - {uptime}min")

    # S3 Progress
    processed = count_s3_folders(bucket, prefix)
    progress_pct = (processed / total_pdfs) * 100
    print(f"\n📁 S3 Output: {processed}/{total_pdfs} PDFs ({progress_pct:.1f}%)")
    print(f"   Location: s3://{bucket}/{prefix}")

    # Progress bar
    bar_length = 50
    filled = int(bar_length * processed / total_pdfs)
    bar = '█' * filled + '░' * (bar_length - filled)
    print(f"   [{bar}]")

    print("\n" + "="*80)


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        status_once()
    else:
        start_time = time.time()
        monitor()
