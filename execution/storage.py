# -*- coding: utf-8 -*-
"""S3 storage service for execution artifacts.

Provides:
- Upload/download functions for large artifacts
- Threshold-based storage decision (DB for small, S3 for large)
- Presigned URL generation for secure downloads
- CloudFront CDN integration
"""
import hashlib
import logging
from io import BytesIO
from typing import Optional, Tuple
from functools import lru_cache

from django.conf import settings

logger = logging.getLogger(__name__)

# Threshold for storing content in S3 vs database (100KB)
S3_THRESHOLD_BYTES = 100 * 1024

# Max content size for direct download (10MB)
MAX_DIRECT_DOWNLOAD_BYTES = 10 * 1024 * 1024


@lru_cache(maxsize=1)
def _get_s3_client():
    """Get boto3 S3 client with lazy initialization.

    Returns:
        `boto3.client`:
            S3 client configured for the default region
    """
    import boto3

    region = getattr(settings, 'AWS_S3_REGION_NAME', 'ap-northeast-1')
    return boto3.client('s3', region_name=region)


def _get_bucket_name() -> str:
    """Get S3 bucket name from settings.

    Returns:
        `str`:
            S3 bucket name
    """
    return getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'hivecore-media')


def _get_cloudfront_domain() -> Optional[str]:
    """Get CloudFront domain from settings.

    Returns:
        `str | None`:
            CloudFront domain or None if not configured
    """
    return getattr(settings, 'AWS_CLOUDFRONT_DOMAIN', None)


def _is_s3_enabled() -> bool:
    """Check if S3 storage is enabled.

    Returns:
        `bool`:
            True if USE_AWS is enabled
    """
    return getattr(settings, 'USE_AWS', False)


def compute_content_hash(content: bytes | str) -> str:
    """Compute SHA256 hash of content.

    Args:
        content (`bytes | str`):
            Content to hash

    Returns:
        `str`:
            SHA256 hex digest
    """
    if isinstance(content, str):
        content = content.encode('utf-8')
    return hashlib.sha256(content).hexdigest()


def should_use_s3(size_bytes: int) -> bool:
    """Determine if content should be stored in S3.

    Args:
        size_bytes (`int`):
            Content size in bytes

    Returns:
        `bool`:
            True if content should be stored in S3
    """
    if not _is_s3_enabled():
        return False
    return size_bytes > S3_THRESHOLD_BYTES


def generate_s3_key(
    execution_round_id: str,
    file_path: str,
    content_hash: str,
) -> str:
    """Generate S3 key for an artifact.

    Format: artifacts/{execution_round_id}/{content_hash[:8]}/{file_path}

    Args:
        execution_round_id (`str`):
            UUID of the execution round
        file_path (`str`):
            Relative file path
        content_hash (`str`):
            SHA256 hash of content

    Returns:
        `str`:
            S3 key path
    """
    # Sanitize file path
    clean_path = file_path.lstrip('/')

    return f"artifacts/{execution_round_id}/{content_hash[:8]}/{clean_path}"


def upload_to_s3(
    content: bytes | str,
    s3_key: str,
    content_type: str = 'application/octet-stream',
) -> bool:
    """Upload content to S3.

    Args:
        content (`bytes | str`):
            Content to upload
        s3_key (`str`):
            S3 key path
        content_type (`str`, optional):
            MIME content type. Defaults to 'application/octet-stream'

    Returns:
        `bool`:
            True if upload succeeded
    """
    if not _is_s3_enabled():
        logger.warning("S3 storage not enabled, skipping upload")
        return False

    if isinstance(content, str):
        content = content.encode('utf-8')

    try:
        client = _get_s3_client()
        bucket = _get_bucket_name()

        client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=content,
            ContentType=content_type,
        )

        logger.info(f"Uploaded {len(content)} bytes to s3://{bucket}/{s3_key}")
        return True

    except Exception as e:
        logger.error(f"Failed to upload to S3: {e}")
        return False


def download_from_s3(s3_key: str) -> Optional[bytes]:
    """Download content from S3.

    Args:
        s3_key (`str`):
            S3 key path

    Returns:
        `bytes | None`:
            Content bytes or None if download failed
    """
    if not _is_s3_enabled():
        logger.warning("S3 storage not enabled, cannot download")
        return None

    try:
        client = _get_s3_client()
        bucket = _get_bucket_name()

        response = client.get_object(Bucket=bucket, Key=s3_key)
        content = response['Body'].read()

        logger.info(f"Downloaded {len(content)} bytes from s3://{bucket}/{s3_key}")
        return content

    except Exception as e:
        logger.error(f"Failed to download from S3: {e}")
        return None


def get_presigned_url(s3_key: str, expires_in: int = 3600) -> Optional[str]:
    """Generate presigned URL for S3 object.

    Args:
        s3_key (`str`):
            S3 key path
        expires_in (`int`, optional):
            URL expiration time in seconds. Defaults to 3600 (1 hour)

    Returns:
        `str | None`:
            Presigned URL or None if generation failed
    """
    if not _is_s3_enabled():
        return None

    try:
        client = _get_s3_client()
        bucket = _get_bucket_name()

        url = client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': s3_key},
            ExpiresIn=expires_in,
        )

        return url

    except Exception as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        return None


def get_cloudfront_url(s3_key: str) -> Optional[str]:
    """Get CloudFront URL for S3 object.

    Uses CloudFront CDN for faster global delivery.
    Falls back to presigned URL if CloudFront not configured.

    Args:
        s3_key (`str`):
            S3 key path

    Returns:
        `str | None`:
            CloudFront URL or presigned URL
    """
    cloudfront_domain = _get_cloudfront_domain()

    if cloudfront_domain:
        return f"https://{cloudfront_domain}/{s3_key}"

    # Fallback to presigned URL
    return get_presigned_url(s3_key)


def delete_from_s3(s3_key: str) -> bool:
    """Delete object from S3.

    Args:
        s3_key (`str`):
            S3 key path

    Returns:
        `bool`:
            True if deletion succeeded
    """
    if not _is_s3_enabled():
        return False

    try:
        client = _get_s3_client()
        bucket = _get_bucket_name()

        client.delete_object(Bucket=bucket, Key=s3_key)

        logger.info(f"Deleted s3://{bucket}/{s3_key}")
        return True

    except Exception as e:
        logger.error(f"Failed to delete from S3: {e}")
        return False


def get_artifact_url(artifact) -> Optional[str]:
    """Get download URL for an artifact.

    Returns CloudFront URL for S3-stored artifacts,
    or None for DB-stored artifacts (content available directly).

    Args:
        artifact (`ExecutionArtifact`):
            Artifact instance

    Returns:
        `str | None`:
            Download URL or None
    """
    if artifact.s3_key:
        return get_cloudfront_url(artifact.s3_key)
    return None


def store_artifact_content(
    execution_round_id: str,
    file_path: str,
    content: bytes | str,
    content_type: str = 'application/octet-stream',
) -> Tuple[str, str, int, str]:
    """Store artifact content with automatic S3/DB decision.

    Stores small files in database, large files in S3.

    Args:
        execution_round_id (`str`):
            UUID of the execution round
        file_path (`str`):
            Relative file path
        content (`bytes | str`):
            File content
        content_type (`str`, optional):
            MIME content type

    Returns:
        `tuple[str, str, int, str]`:
            Tuple of (content_for_db, content_hash, size_bytes, s3_key)
            - content_for_db: Content to store in DB (empty if S3)
            - content_hash: SHA256 hash
            - size_bytes: Content size
            - s3_key: S3 key if stored in S3, else empty string
    """
    # Convert to bytes for consistent handling
    if isinstance(content, str):
        content_bytes = content.encode('utf-8')
        content_str = content
    else:
        content_bytes = content
        try:
            content_str = content.decode('utf-8')
        except UnicodeDecodeError:
            content_str = ''  # Binary content, don't store as text

    size_bytes = len(content_bytes)
    content_hash = compute_content_hash(content_bytes)

    if should_use_s3(size_bytes):
        # Store in S3
        s3_key = generate_s3_key(execution_round_id, file_path, content_hash)

        if upload_to_s3(content_bytes, s3_key, content_type):
            # Content stored in S3, don't duplicate in DB
            return '', content_hash, size_bytes, s3_key
        else:
            # S3 upload failed, fallback to DB
            logger.warning(f"S3 upload failed, storing in DB: {file_path}")
            return content_str, content_hash, size_bytes, ''
    else:
        # Store in database
        return content_str, content_hash, size_bytes, ''


def get_artifact_content(artifact) -> Optional[str | bytes]:
    """Get artifact content from DB or S3.

    Args:
        artifact (`ExecutionArtifact`):
            Artifact instance

    Returns:
        `str | bytes | None`:
            Content or None if not available
    """
    # Check DB first
    if artifact.content:
        return artifact.content

    # Try S3
    if artifact.s3_key:
        content = download_from_s3(artifact.s3_key)
        if content:
            try:
                return content.decode('utf-8')
            except UnicodeDecodeError:
                return content

    return None


def migrate_artifact_to_s3(artifact) -> bool:
    """Migrate an artifact from DB to S3.

    Useful for batch migration of large artifacts.

    Args:
        artifact (`ExecutionArtifact`):
            Artifact with content in DB

    Returns:
        `bool`:
            True if migration succeeded
    """
    if not artifact.content:
        return False

    if artifact.s3_key:
        # Already in S3
        return True

    content_bytes = artifact.content.encode('utf-8')

    # Generate S3 key
    s3_key = generate_s3_key(
        str(artifact.execution_round_id),
        artifact.file_path,
        artifact.content_hash or compute_content_hash(content_bytes),
    )

    # Upload to S3
    if upload_to_s3(content_bytes, s3_key):
        # Update artifact
        artifact.s3_key = s3_key
        artifact.content = ''  # Clear DB content
        artifact.save(update_fields=['s3_key', 'content', 'updated_at'])

        logger.info(f"Migrated artifact {artifact.id} to S3: {s3_key}")
        return True

    return False


def list_s3_artifacts(execution_round_id: str) -> list[dict]:
    """List all S3 artifacts for an execution round.

    Args:
        execution_round_id (`str`):
            UUID of the execution round

    Returns:
        `list[dict]`:
            List of S3 object metadata
    """
    if not _is_s3_enabled():
        return []

    try:
        client = _get_s3_client()
        bucket = _get_bucket_name()
        prefix = f"artifacts/{execution_round_id}/"

        response = client.list_objects_v2(Bucket=bucket, Prefix=prefix)

        artifacts = []
        for obj in response.get('Contents', []):
            artifacts.append({
                'key': obj['Key'],
                'size': obj['Size'],
                'last_modified': obj['LastModified'].isoformat(),
            })

        return artifacts

    except Exception as e:
        logger.error(f"Failed to list S3 artifacts: {e}")
        return []


def cleanup_execution_artifacts(execution_round_id: str) -> int:
    """Delete all S3 artifacts for an execution round.

    Args:
        execution_round_id (`str`):
            UUID of the execution round

    Returns:
        `int`:
            Number of objects deleted
    """
    if not _is_s3_enabled():
        return 0

    try:
        client = _get_s3_client()
        bucket = _get_bucket_name()
        prefix = f"artifacts/{execution_round_id}/"

        # List and delete objects
        response = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        objects = response.get('Contents', [])

        if not objects:
            return 0

        delete_keys = [{'Key': obj['Key']} for obj in objects]

        client.delete_objects(
            Bucket=bucket,
            Delete={'Objects': delete_keys},
        )

        logger.info(f"Deleted {len(delete_keys)} artifacts for execution {execution_round_id}")
        return len(delete_keys)

    except Exception as e:
        logger.error(f"Failed to cleanup S3 artifacts: {e}")
        return 0
