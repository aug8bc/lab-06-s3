#!/usr/bin/env python3
import logging
import time
import os
import sys
import boto3
import json
import requests
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

s3 = boto3.client("s3", region_name="us-east-1")

def parse_args():
	"""Read the book list path, index page path, and bucket name from the command line."""
	if len(sys.argv) < 4:
		log.error("Incorrect input, looking for 3 arguments")
		sys.exit(1)
	list_file = sys.argv[1]
	index_path = sys.argv[2]
	bucket = sys.argv[3]
	return list_file, index_path, bucket
def download_books(list_file, dest_dir):
	"""Returns a list of the local paths of the books"""
	os.makedirs(dest_dir, exist_ok=True)
	with open(list_file) as f:
		urls = [line.strip() for line in f if line.strip()]
	log.info(f"Found {len(urls)} book URLs in {list_file}")
	paths = []
	for url in urls:
		filename = url.split("/")[-1]
		path = os.path.join(dest_dir, filename)
		if os.path.exists(path):
			log.info(f"{path} already exists, skipping download")
			paths.append(path)
			continue
		try:
			response = requests.get(url, timeout=30)
			response.raise_for_status()
			with open(path, "wb") as f:
				f.write(response.content)
			log.info(f"Downloaded {url} to {path}")
			paths.append(path)
		except requests.RequestException as e:
			log.error(f"Error downloading {url}: {e}")
		time.sleep(1)
	return paths

def create_bucket(bucket):
	"""Checks if a bucket exists and if it doesn't, creates it"""
	try:
		s3.head_bucket(Bucket=bucket)
		log.info(f"Bucket {bucket} already exists")
		return True
	except ClientError:
		log.info(f"Bucket {bucket} not found, creating it")
	try:
		s3.create_bucket(Bucket=bucket)
		log.info(f"Created bucket: {bucket}")
		return True
	except ClientError as e:
		log.error(f"Error creating bucket {bucket}: {e}")
		return False

def make_public(bucket):
	"""Turn off Block Public Access and attach a public-read policy"""
	policy = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": "*",
		"Action": "s3:GetObject", "Resource": f"arn:aws:s3:::{bucket}/*",}],}
	try:
		s3.put_public_access_block(Bucket=bucket,PublicAccessBlockConfiguration={
		"BlockPublicAcls": False,
		"IgnorePublicAcls": False,
		"BlockPublicPolicy": False,
		"RestrictPublicBuckets": False,
		},
	)
		log.info(f"Turned off Block Public Access for {bucket}")
		s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
		log.info(f"Attached public-read policy to {bucket}")
		return True
	except ClientError as e:
		log.error(f"Error making bucket {bucket} public: {e}")
		return False
def upload_files(bucket, file_paths):
	"""Upload each local file to the top level of the bucket."""
	uploaded = 0
	for path in file_paths:
		key = os.path.basename(path)
		try:
			with open(path, "rb") as f:
				s3.put_object(Bucket=bucket,Key=key,Body=f,ContentType="text/plain; charset=utf-8",)
			log.info(f"Uploaded {path} to s3://{bucket}/{key}")
			uploaded += 1
		except FileNotFoundError:
			log.error(f"Local file not found: {path}")
		except ClientError as e:
			log.error(f"Error uploading {path}: {e}")
	log.info(f"Uploaded {uploaded} of {len(file_paths)} files to {bucket}")
	return uploaded
def upload_index(bucket, index_path):
	"""Upload the index page to the bucket"""
	try:
		with open(index_path, "rb") as f:
			s3.put_object(Bucket=bucket,Key="index.html",Body=f,ContentType="text/html",)
		log.info(f"Uploaded {index_path} to s3://{bucket}/index.html")
		return True
	except FileNotFoundError:
		log.error(f"Local file not found: {index_path}")
		return False
	except ClientError as e:
		log.error(f"Error uploading {index_path}: {e}")
		return False
def main():
	"""Run everything"""
	list_file, index_path, bucket = parse_args()
	paths = download_books(list_file, "books")
	if not paths:
		log.error("No books were downloaded")
		sys.exit(1)
	if not create_bucket(bucket):
		log.error(f"Could not create bucket {bucket}")
		sys.exit(1)
	if not make_public(bucket):
		log.error(f"Could not make bucket {bucket} public")
		sys.exit(1)
	count = upload_files(bucket, paths)
	index_ok = upload_index(bucket, index_path)
	if count == len(paths) and index_ok:
		log.info(f"Success: uploaded {count} books and the index page")
	else:
		log.error(f"Finished with errors: uploaded {count} of {len(paths)} books")
	log.info(f"Public URL: https://{bucket}.s3.amazonaws.com/index.html")

if __name__ == "__main__":
	main()
