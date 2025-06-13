# -*- coding: utf-8 -*-
import oss2
from oss2.credentials import EnvironmentVariableCredentialsProvider
from itertools import islice
import os
import logging
import time
import random
import configparser

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 读取配置文件
config = configparser.ConfigParser()
config.read('config/config.ini')

# 从配置文件中获取访问凭证
access_key_id = config.get('oss', 'access_key_id')
access_key_secret = config.get('oss', 'access_key_secret')
auth = oss2.Auth(access_key_id, access_key_secret)

# 从配置文件中获取Endpoint和Region
endpoint = config.get('oss', 'endpoint')
region = config.get('oss', 'region')

def generate_unique_bucket_name():
    # 获取当前时间戳
    timestamp = int(time.time())
    # 生成0到9999之间的随机数
    random_number = random.randint(0, 9999)
    # 构建唯一的Bucket名称
    bucket_name = f"demo-{timestamp}-{random_number}"
    return bucket_name

# 生成唯一的Bucket名称
# bucket_name = generate_unique_bucket_name()
bucket_name = 'mojie-image'
bucket = oss2.Bucket(auth, endpoint, bucket_name, region=region)

def create_bucket(bucket):
    try:
        bucket.create_bucket(oss2.models.BUCKET_ACL_PRIVATE)
        logging.info("Bucket created successfully")
    except oss2.exceptions.OssError as e:
        logging.error(f"Failed to create bucket: {e}")

def upload_file(bucket, object_name, data):
    try:
        result = bucket.put_object(object_name, data)
        logging.info(f"File uploaded successfully, status code: {result.status}")
        # 构建公网地址
        public_url = f"https://{bucket.bucket_name}.{endpoint.replace('https://', '')}/{object_name}"
        return public_url
    except oss2.exceptions.OssError as e:
        logging.error(f"Failed to upload file: {e}")
        return None

def download_file(bucket, object_name):
    try:
        file_obj = bucket.get_object(object_name)
        content = file_obj.read().decode('utf-8')
        logging.info("File content:")
        logging.info(content)
        return content
    except oss2.exceptions.OssError as e:
        logging.error(f"Failed to download file: {e}")

def list_objects(bucket):
    try:
        objects = list(islice(oss2.ObjectIterator(bucket), 10))
        for obj in objects:
            logging.info(obj.key)
    except oss2.exceptions.OssError as e:
        logging.error(f"Failed to list objects: {e}")

def delete_objects(bucket):
    try:
        objects = list(islice(oss2.ObjectIterator(bucket), 100))
        if objects:
            for obj in objects:
                bucket.delete_object(obj.key)
                logging.info(f"Deleted object: {obj.key}")
        else:
            logging.info("No objects to delete")
    except oss2.exceptions.OssError as e:
        logging.error(f"Failed to delete objects: {e}")

def delete_bucket(bucket):
    try:
        bucket.delete_bucket()
        logging.info("Bucket deleted successfully")
    except oss2.exceptions.OssError as e:
        logging.error(f"Failed to delete bucket: {e}")

# 主流程
if __name__ == '__main__':
    # 1. 创建Bucket
    create_bucket(bucket)
    # 2. 上传文件
    upload_file(bucket, 'test-string-file', b'Hello OSS, this is a test string.')
    # 3. 下载文件
    download_file(bucket, 'test-string-file')
    # 4. 列出Bucket中的对象
    list_objects(bucket)
    # 5. 删除Bucket中的对象
    delete_objects(bucket)
    # 6. 删除Bucket
    delete_bucket(bucket)