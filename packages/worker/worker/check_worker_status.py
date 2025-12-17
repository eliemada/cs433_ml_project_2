#!/usr/bin/env python3
"""
Check the status of distributed workers and S3 uploads.

This script helps diagnose:
- Are workers still running?
- When was the last upload?
- How many PDFs are processed?
- What's the processing rate?
"""

import os
import sys
from datetime import datetime, timedelta
import boto3
from collections import defaultdict

def check_s3_status():
    """Check S3 upload status and statistics."""

    print("=" * 70)
    print("S3 Upload Status Check")
    print("=" * 70)

    # Initialize S3 client
    s3 = boto3.client('s3')
    bucket = os.getenv('S3_OUTPUT_BUCKET', 'cs433-rag-project2')
    prefix = os.getenv('S3_OUTPUT_PREFIX', 'processed/')

    print(f"\nBucket: s3://{bucket}/{prefix}")
    print()

    # Count processed PDFs
    print("📊 Counting processed PDFs...")
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter='/')

    processed_pdfs = []
    for page in pages:
        if 'CommonPrefixes' in page:
            for prefix_obj in page['CommonPrefixes']:
                pdf_folder = prefix_obj['Prefix'].split('/')[-2]
                processed_pdfs.append(pdf_folder)

    total_processed = len(processed_pdfs)
    print(f"✅ Total processed PDFs: {total_processed}")

    # Check total available PDFs
    print("\n📊 Checking total available PDFs...")
    raw_prefix = os.getenv('S3_INPUT_PREFIX', 'raw_pdfs/')
    raw_pages = paginator.paginate(Bucket=bucket, Prefix=raw_prefix)

    total_pdfs = 0
    for page in raw_pages:
        if 'Contents' in page:
            total_pdfs += len([obj for obj in page['Contents'] if obj['Key'].endswith('.pdf')])

    print(f"📚 Total PDFs to process: {total_pdfs}")
    print(f"🎯 Progress: {total_processed}/{total_pdfs} ({total_processed*100//total_pdfs}%)")
    print(f"⏳ Remaining: {total_pdfs - total_processed} PDFs")

    # Check last upload time
    print("\n⏰ Checking last upload time...")

    all_files = []
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

    for page in pages:
        if 'Contents' in page:
            all_files.extend(page['Contents'])

    if all_files:
        # Sort by last modified
        all_files.sort(key=lambda x: x['LastModified'], reverse=True)

        last_upload = all_files[0]
        last_time = last_upload['LastModified']
        time_ago = datetime.now(last_time.tzinfo) - last_time

        print(f"📤 Last upload: {last_upload['Key']}")
        print(f"🕐 Timestamp: {last_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"⏱️  Time ago: {format_timedelta(time_ago)}")

        # Warning if no uploads in last hour
        if time_ago > timedelta(hours=1):
            print(f"\n⚠️  WARNING: No uploads in the last {format_timedelta(time_ago)}")
            print("   Workers may have stopped or encountered issues!")
        else:
            print(f"\n✅ Workers appear to be active (recent upload)")
    else:
        print("❌ No files found in processed folder!")

    # Check uploads by time
    print("\n📈 Upload activity (last 24 hours):")

    now = datetime.now(last_time.tzinfo if all_files else None)
    last_24h = now - timedelta(hours=24)

    uploads_by_hour = defaultdict(int)

    for file_obj in all_files:
        file_time = file_obj['LastModified']
        if file_time > last_24h:
            hour_key = file_time.strftime('%Y-%m-%d %H:00')
            uploads_by_hour[hour_key] += 1

    # Show last 12 hours
    hours = sorted(uploads_by_hour.keys(), reverse=True)[:12]
    for hour in hours:
        count = uploads_by_hour[hour]
        bar = '█' * (count // 10)
        print(f"  {hour}: {count:4d} files {bar}")

    # Estimate completion
    if len(hours) >= 2:
        recent_hours = hours[:3]
        recent_uploads = sum(uploads_by_hour[h] for h in recent_hours)
        files_per_hour = recent_uploads / len(recent_hours)

        # Estimate PDFs per hour (assuming ~35 files per PDF)
        pdfs_per_hour = files_per_hour / 35

        remaining_pdfs = total_pdfs - total_processed
        hours_remaining = remaining_pdfs / pdfs_per_hour if pdfs_per_hour > 0 else float('inf')

        print(f"\n⏱️  Estimated completion:")
        print(f"   Processing rate: ~{pdfs_per_hour:.1f} PDFs/hour")
        print(f"   Hours remaining: ~{hours_remaining:.1f} hours")
        print(f"   Estimated completion: {(now + timedelta(hours=hours_remaining)).strftime('%Y-%m-%d %H:%M')}")

    # Check for failure reports
    print("\n🔍 Checking for failure reports...")
    try:
        failure_pages = paginator.paginate(Bucket=bucket, Prefix='failures/')
        failure_files = []
        for page in failure_pages:
            if 'Contents' in page:
                failure_files.extend(page['Contents'])

        if failure_files:
            print(f"⚠️  Found {len(failure_files)} failure report(s):")
            for failure in failure_files:
                print(f"   - {failure['Key']}")
            print(f"\n   Download with: aws s3 cp s3://{bucket}/{failure_files[0]['Key']} -")
        else:
            print("✅ No failure reports found")
    except:
        print("✅ No failure reports found")

def format_timedelta(td):
    """Format timedelta in human-readable form."""
    seconds = int(td.total_seconds())

    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minutes"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} hours {minutes} minutes"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days} days {hours} hours"

def check_worker_recommendations():
    """Provide recommendations based on status."""
    print("\n" + "=" * 70)
    print("💡 Recommendations")
    print("=" * 70)
    print()

    print("To check if workers are running:")
    print("  1. SSH into your EC2 instances")
    print("  2. Run: docker ps")
    print("  3. Check logs: docker logs <container-id> | tail -50")
    print()

    print("To restart workers if they stopped:")
    print("  1. Check MANUAL_DEPLOYMENT.md for instructions")
    print("  2. Run docker command with correct WORKER_ID")
    print()

    print("To monitor in real-time:")
    print("  Run: watch -n 60 'aws s3 ls s3://cs433-rag-project2/processed/ | wc -l'")
    print()

def main():
    """Main entry point."""
    try:
        check_s3_status()
        check_worker_recommendations()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure AWS credentials are set:")
        print("  export AWS_ACCESS_KEY_ID=...")
        print("  export AWS_SECRET_ACCESS_KEY=...")
        sys.exit(1)

if __name__ == '__main__':
    main()
