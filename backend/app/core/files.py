"""Files of the site: customer attachments (private) and media of the catalog (2D structures, photos, documents).

The local disk by default — the `files` volume the API and the worker share. With S3_BUCKET set the files go to
S3-compatible storage (Yandex Object Storage, Selectel, VK Cloud; TZ 12.1); the bucket stays private either way.
Media are served from the site's own address /api/v1/media/<key> whatever the storage, so the CSP, the image
optimizer of the storefront and the links in cards never change when the storage does.

Keys: ``attachments/…`` (private, read only by the worker for the CRM) and ``media/…`` (served publicly).
"""

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

from app.core.config import settings

KEY = re.compile(r'^[a-z0-9][a-z0-9_.-]*(?:/[a-z0-9][a-z0-9_.-]*){0,6}$')


class FileMissing(Exception):
    pass


class StorageUnavailable(Exception):
    pass


def check_key(key: str) -> str:
    if len(key) > 300 or not KEY.match(key) or '..' in key:
        raise FileMissing(key)
    return key


class Storage(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...

    def get(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...

    def delete(self, key: str) -> None: ...


class LocalStorage:
    """Files readable by the service user only, written once and synced to disk."""

    def __init__(self, root: Path):
        self.root = root

    def path(self, key: str) -> Path:
        root = self.root.resolve()
        target = (root / check_key(key)).resolve()
        if not target.is_relative_to(root) or target == root:
            raise FileMissing(key)
        return target

    def put(self, key: str, data: bytes, content_type: str) -> None:
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = target.with_name(f'.{target.name}.{os.getpid()}.tmp')
        with temporary.open('wb') as stream:
            os.chmod(temporary, 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(target)

    def get(self, key: str) -> bytes:
        try:
            return self.path(key).read_bytes()
        except FileNotFoundError:
            raise FileMissing(key) from None
        except OSError as exc:
            raise StorageUnavailable(str(exc)) from None

    def exists(self, key: str) -> bool:
        return self.path(key).is_file()

    def delete(self, key: str) -> None:
        self.path(key).unlink(missing_ok=True)


class S3Storage:
    def __init__(self, client: Any, bucket: str, prefix: str = ''):
        self.client = client
        self.bucket = bucket
        self.prefix = prefix.strip('/') + '/' if prefix.strip('/') else ''

    def name(self, key: str) -> str:
        return self.prefix + check_key(key)

    def call(self, method: str, **kwargs: Any) -> Any:
        from botocore.exceptions import BotoCoreError, ClientError

        try:
            return getattr(self.client, method)(Bucket=self.bucket, **kwargs)
        except ClientError as exc:
            code = str(exc.response.get('Error', {}).get('Code', ''))
            if code in ('NoSuchKey', '404', 'NotFound'):
                raise FileMissing(kwargs.get('Key', '')) from None
            raise StorageUnavailable(code or str(exc)) from None
        except BotoCoreError as exc:
            raise StorageUnavailable(str(exc)) from None

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.call('put_object', Key=self.name(key), Body=data, ContentType=content_type)

    def get(self, key: str) -> bytes:
        body = self.call('get_object', Key=self.name(key))['Body']
        try:
            return bytes(body.read())
        finally:
            body.close()

    def exists(self, key: str) -> bool:
        try:
            self.call('head_object', Key=self.name(key))
        except FileMissing:
            return False
        return True

    def delete(self, key: str) -> None:
        self.call('delete_object', Key=self.name(key))


def s3_client() -> Any:
    import boto3
    from botocore.config import Config

    return boto3.client(
        's3', endpoint_url=settings.s3_endpoint_url or None, region_name=settings.s3_region or None,
        aws_access_key_id=settings.s3_access_key or None, aws_secret_access_key=settings.s3_secret_key or None,
        config=Config(signature_version='s3v4', connect_timeout=5, read_timeout=20,
                      retries={'max_attempts': 3, 'mode': 'standard'}))


@lru_cache(maxsize=1)
def _configured(bucket: str, root: str) -> Storage:
    return S3Storage(s3_client(), bucket, settings.s3_prefix) if bucket else LocalStorage(Path(root))


def storage() -> Storage:
    return _configured(settings.s3_bucket, str(settings.storage_dir))


def media_url(key: str) -> str:
    """The public address of a ``media/…`` key, relative to the site."""
    return '/api/v1/' + check_key(key)
