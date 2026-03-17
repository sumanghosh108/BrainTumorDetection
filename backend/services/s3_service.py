"""AWS S3 operations for MRI scan storage."""

from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING

import aioboto3

from backend.utils.logger import get_logger

if TYPE_CHECKING:
    from fastapi import UploadFile

logger = get_logger(__name__)

S3_BUCKET = os.getenv("S3_BUCKET", "brain-tumor-scans")
S3_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_PRESIGN_EXPIRY = int(os.getenv("S3_PRESIGN_EXPIRY", "3600"))

_session = aioboto3.Session()


def _build_key(scan_id: uuid.UUID, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "dcm"
    return f"scans/{scan_id}/{scan_id}.{ext}"


async def upload_mri(file: UploadFile, scan_id: uuid.UUID) -> str:
    """Upload an MRI file to S3 and return the object URL.

    Returns:
        The public S3 URL for the uploaded object.
    """
    key = _build_key(scan_id, file.filename or "scan.dcm")
    content = await file.read()

    async with _session.client("s3", region_name=S3_REGION) as s3:
        await s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=content,
            ContentType=file.content_type or "application/octet-stream",
            ServerSideEncryption="AES256",
        )

    s3_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{key}"
    logger.info("s3_upload_complete", scan_id=str(scan_id), key=key, size=len(content))
    return s3_url


async def get_presigned_url(s3_key: str) -> str:
    """Generate a pre-signed GET URL for a stored scan."""
    async with _session.client("s3", region_name=S3_REGION) as s3:
        url: str = await s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": s3_key},
            ExpiresIn=S3_PRESIGN_EXPIRY,
        )
    return url


async def delete_scan(s3_key: str) -> None:
    """Delete a scan object from S3."""
    async with _session.client("s3", region_name=S3_REGION) as s3:
        await s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)
    logger.info("s3_delete_complete", key=s3_key)


async def download_scan_bytes(s3_key: str) -> bytes:
    """Download a scan from S3 and return raw bytes."""
    async with _session.client("s3", region_name=S3_REGION) as s3:
        response = await s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
        data: bytes = await response["Body"].read()
    logger.info("s3_download_complete", key=s3_key, size=len(data))
    return data


async def upload_gradcam(png_bytes: bytes, scan_id: uuid.UUID) -> str:
    """Upload a Grad-CAM overlay PNG to S3 and return the URL."""
    key = f"gradcam/{scan_id}/overlay.png"
    async with _session.client("s3", region_name=S3_REGION) as s3:
        await s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=png_bytes,
            ContentType="image/png",
            ServerSideEncryption="AES256",
        )
    url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{key}"
    logger.info("gradcam_upload_complete", scan_id=str(scan_id), key=key)
    return url


async def warmup() -> None:
    """Verify S3 bucket is accessible at startup."""
    async with _session.client("s3", region_name=S3_REGION) as s3:
        await s3.head_bucket(Bucket=S3_BUCKET)
    logger.info("s3_warmup_ok", bucket=S3_BUCKET)
