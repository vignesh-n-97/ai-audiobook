"""
Storage service abstraction for the AI Audiobook platform.

Primary backend: Backblaze B2 (S3-compatible API).
Alternative backends selected via `storage_backend` config key:
  - minio      : air-gapped / offline deployments (AGPL — internal only)
  - seaweedfs  : self-hosted OSI-licensed alternative
  - localstack : local dev / CI only
  - filesystem : earliest experiment runs before B2 is configured

See TASKS.md §AUD-002 for detailed backend comparison.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import IO, Union

import boto3
from botocore.config import Config as BotoConfig

from app.shared.config import Config

# Files larger than this threshold are uploaded via multipart (5 MB chunks)
_MULTIPART_THRESHOLD = 10 * 1024 * 1024  # 10 MB
_CHUNK_SIZE = 5 * 1024 * 1024            # 5 MB — S3 multipart minimum per part


def get_b2_client(cfg: Config):
    """Return a boto3 S3 client configured for Backblaze B2.

    The B2 S3-compatible endpoint encodes the region in the hostname:
        s3.<region>.backblazeb2.com

    Read region from cfg.b2_region — never hardcode it.
    """
    return boto3.client(
        "s3",
        endpoint_url=f"https://s3.{cfg.b2_region}.backblazeb2.com",
        aws_access_key_id=cfg.b2_application_key_id,
        aws_secret_access_key=cfg.b2_application_key,
        config=BotoConfig(signature_version="s3v4"),
        region_name=cfg.b2_region,
    )


class StorageService:
    """Thin wrapper around an S3-compatible storage backend.

    Instantiated by the API/Worker via dependency injection. The underlying
    client is swapped by changing `storage_backend` in config — no business
    logic changes required.
    """

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._client = self._build_client(cfg)
        self._bucket = cfg.b2_bucket_name

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upload(
        self,
        key: str,
        data: Union[bytes, IO[bytes]],
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload *data* to *key* in the configured bucket.

        Files > 10 MB are uploaded via multipart to avoid OOM on the
        primary 16 GB CPU-only device.

        Returns the public URL string.
        """
        raw: bytes = data if isinstance(data, bytes) else data.read()

        if len(raw) > _MULTIPART_THRESHOLD:
            self._multipart_upload(key, io.BytesIO(raw), content_type)
        else:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=raw,
                ContentType=content_type,
            )

        return self._public_url(key)

    def upload_fileobj(
        self,
        key: str,
        fileobj: IO[bytes],
        content_type: str = "application/octet-stream",
        size: int | None = None,
    ) -> tuple[str, int]:
        """Upload a file-like object without loading it entirely into memory.

        When *size* is known and ≤ 10 MB the file is read once and sent as a
        single PUT.  For larger files (or when size is unknown) the upload is
        split into 5 MB parts via S3 multipart so peak memory stays at one
        chunk regardless of total file size.

        Returns ``(public_url, total_bytes_uploaded)``.
        """
        if size is not None and size <= _MULTIPART_THRESHOLD:
            data = fileobj.read()
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            return self._public_url(key), len(data)

        # Unknown size or confirmed large: stream via multipart
        total = self._multipart_upload(key, fileobj, content_type)
        return self._public_url(key), total

    def download(self, key: str) -> bytes:
        """Download object at *key* and return its raw bytes."""
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()

    def delete(self, key: str) -> None:
        """Delete object at *key*."""
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned GET URL valid for *expires_in* seconds."""
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def presigned_download_url(
        self,
        key: str,
        filename: str | None = None,
        expires_in: int = 3600,
    ) -> str:
        """Generate a presigned GET URL with Content-Disposition for browser download.

        The ``ResponseContentDisposition`` parameter is embedded in the signed
        URL so the browser treats the response as a file download rather than
        attempting to render it inline.
        """
        params: dict = {"Bucket": self._bucket, "Key": key}
        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
        return self._client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expires_in,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _public_url(self, key: str) -> str:
        cfg = self._cfg
        return f"https://s3.{cfg.b2_region}.backblazeb2.com/{self._bucket}/{key}"

    def _multipart_upload(self, key: str, body: IO[bytes], content_type: str) -> int:
        """Upload *body* in 5 MB chunks via S3 multipart. Returns total bytes."""
        mpu = self._client.create_multipart_upload(
            Bucket=self._bucket, Key=key, ContentType=content_type
        )
        upload_id = mpu["UploadId"]
        parts: list[dict] = []
        part_number = 1
        total = 0

        try:
            while True:
                chunk = body.read(_CHUNK_SIZE)
                if not chunk:
                    break
                response = self._client.upload_part(
                    Bucket=self._bucket,
                    Key=key,
                    UploadId=upload_id,
                    PartNumber=part_number,
                    Body=chunk,
                )
                parts.append({"PartNumber": part_number, "ETag": response["ETag"]})
                total += len(chunk)
                part_number += 1

            self._client.complete_multipart_upload(
                Bucket=self._bucket,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
        except Exception:
            self._client.abort_multipart_upload(
                Bucket=self._bucket, Key=key, UploadId=upload_id
            )
            raise

        return total

    @staticmethod
    def _build_client(cfg: Config):
        """Select backend client based on storage_backend config key."""
        backend = cfg.storage_backend

        if backend in ("b2", "r2"):
            return get_b2_client(cfg)

        if backend == "filesystem":
            # Filesystem backend is handled by FilesystemStorageService
            raise ValueError(
                "Use FilesystemStorageService for filesystem backend — "
                "StorageService requires an S3-compatible endpoint."
            )

        # minio / seaweedfs / localstack — all S3-compatible
        return get_b2_client(cfg)


class FilesystemStorageService:
    """Local filesystem storage for early experiment runs before B2 is configured.

    WARNING: Not suitable for production. Artifacts are not durable.
    """

    def __init__(self, base_dir: str = "./runs") -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def upload(self, key: str, data: Union[bytes, IO[bytes]], **_: object) -> str:
        dest = self._base / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        raw = data if isinstance(data, bytes) else data.read()
        dest.write_bytes(raw)
        return str(dest.resolve())

    def download(self, key: str) -> bytes:
        return (self._base / key).read_bytes()

    def delete(self, key: str) -> None:
        (self._base / key).unlink(missing_ok=True)
