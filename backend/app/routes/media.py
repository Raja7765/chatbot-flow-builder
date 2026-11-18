"""
API routes for Media Assets management.
Handles secure upload, retrieval, metadata inspection, and safe deletion of media files
(images, PDFs, videos) backed by PostgreSQL and local filesystem storage.
"""

import hashlib
from pathlib import Path
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db, get_utc_now
from app.media_storage import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    UPLOAD_DIRS,
    delete_stored_file,
    ensure_upload_dirs,
    resolve_storage_path,
    sniff_magic_bytes,
)
from app.models import AnswerBlock, MediaAsset, format_utc_iso
from app.schemas import MediaAssetDeleteResponse, MediaAssetResponse

router = APIRouter(prefix="/media", tags=["Media Assets"])


def _parse_media_uuid(media_id: str) -> uuid.UUID:
    """Validate and parse a media_id string as a UUID, raising HTTP 404 on failure."""
    try:
        return uuid.UUID(str(media_id).strip())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media asset with id '{media_id}' not found.",
        )


@router.post(
    "/upload",
    response_model=MediaAssetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_media(
    file: UploadFile = File(..., description="Multipart media file to upload (image, PDF, or video)"),
    media_type: Optional[str] = Form(None, description="Optional media type override"),
    description: Optional[str] = Form(None, description="Optional description of the media asset"),
    db: Session = Depends(get_db),
) -> MediaAssetResponse:
    """
    Upload a media file with validation:
    - Accepts image, PDF, and video formats up to 20 MB.
    - Sniffs file header magic bytes to verify genuine MIME type.
    - Generates a UUID and unique stored filename (never trusts client filename for disk storage).
    - Computes SHA-256 checksum during streaming.
    - Cleans up partially written files if writing or database operations fail.
    - Saves metadata into the PostgreSQL media_assets table.
    """
    ensure_upload_dirs()

    original_filename = Path(file.filename or "unnamed_file").name
    ext = Path(original_filename).suffix.lower()

    if not ext or ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unsupported file extension: '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS.keys()))}.",
        )

    # Read initial chunk to inspect magic bytes
    initial_chunk = await file.read(1024)
    if not initial_chunk:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Uploaded file is empty.",
        )

    detected_mime, detected_category = sniff_magic_bytes(initial_chunk)
    if not detected_mime or not detected_category:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="File content does not match any supported image, PDF, or video format.",
        )

    # Verify extension matches detected format
    expected_mime, expected_cat = ALLOWED_EXTENSIONS[ext]
    if detected_mime != expected_mime:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"File extension '{ext}' does not match detected content format '{detected_mime}'.",
        )

    # Target directory based on detected category
    target_dir = UPLOAD_DIRS.get(detected_category, UPLOAD_DIRS["document"])
    media_id = uuid.uuid4()
    stored_name = f"{media_id.hex}{ext}"
    target_path = target_dir / stored_name

    # Storage key relative to backend directory (e.g. uploads/images/<stored_name>)
    relative_category_folder = target_dir.name
    storage_key = f"uploads/{relative_category_folder}/{stored_name}"

    # Stream chunks, compute SHA-256 and validate total size
    sha256 = hashlib.sha256()
    sha256.update(initial_chunk)
    total_bytes = len(initial_chunk)

    try:
        with open(target_path, "wb") as out_fp:
            out_fp.write(initial_chunk)
            while chunk := await file.read(64 * 1024):
                total_bytes += len(chunk)
                if total_bytes > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=f"File size exceeds maximum permitted limit of {MAX_FILE_SIZE // (1024 * 1024)} MB.",
                    )
                sha256.update(chunk)
                out_fp.write(chunk)
    except Exception:
        if target_path.is_file():
            target_path.unlink()
        raise

    checksum_digest = sha256.hexdigest()
    now = get_utc_now()
    final_media_type = media_type.strip() if media_type and media_type.strip() else detected_category

    media_asset = MediaAsset(
        id=media_id,
        file_name=original_filename,
        stored_name=stored_name,
        mime_type=detected_mime,
        media_type=final_media_type,
        storage_key=storage_key,
        file_size=total_bytes,
        checksum=checksum_digest,
        created_at=now,
    )

    try:
        db.add(media_asset)
        db.commit()
        db.refresh(media_asset)
    except Exception:
        db.rollback()
        if target_path.is_file():
            target_path.unlink()
        raise

    return MediaAssetResponse(
        id=str(media_asset.id),
        file_name=media_asset.file_name,
        stored_name=media_asset.stored_name,
        mime_type=media_asset.mime_type,
        media_type=media_asset.media_type,
        storage_key=media_asset.storage_key,
        file_size=int(media_asset.file_size),
        checksum=media_asset.checksum,
        created_at=format_utc_iso(media_asset.created_at),
    )


@router.get(
    "/{media_id}",
    response_class=FileResponse,
    status_code=status.HTTP_200_OK,
)
def get_media_file(
    media_id: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    """
    Retrieve the actual binary media file for downloading or inline rendering.
    Returns HTTP 404 if the database record or physical file on disk is missing.
    """
    media_uuid = _parse_media_uuid(media_id)
    media_asset = db.get(MediaAsset, media_uuid)
    if media_asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media asset with id '{media_id}' not found.",
        )

    try:
        physical_path = resolve_storage_path(media_asset.storage_key)
        if not physical_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Physical media file not found on server for id '{media_id}'.",
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid media storage key.",
        )

    return FileResponse(
        path=str(physical_path),
        media_type=media_asset.mime_type,
        filename=media_asset.file_name,
    )


@router.get(
    "/{media_id}/metadata",
    response_model=MediaAssetResponse,
    status_code=status.HTTP_200_OK,
)
def get_media_metadata(
    media_id: str,
    db: Session = Depends(get_db),
) -> MediaAssetResponse:
    """
    Retrieve metadata for a specific media asset from PostgreSQL.
    """
    media_uuid = _parse_media_uuid(media_id)
    media_asset = db.get(MediaAsset, media_uuid)
    if media_asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media asset with id '{media_id}' not found.",
        )

    return MediaAssetResponse(
        id=str(media_asset.id),
        file_name=media_asset.file_name,
        stored_name=media_asset.stored_name,
        mime_type=media_asset.mime_type,
        media_type=media_asset.media_type,
        storage_key=media_asset.storage_key,
        file_size=int(media_asset.file_size),
        checksum=media_asset.checksum,
        created_at=format_utc_iso(media_asset.created_at),
    )


@router.delete(
    "/{media_id}",
    response_model=MediaAssetDeleteResponse,
    status_code=status.HTTP_200_OK,
)
def delete_media_asset(
    media_id: str,
    db: Session = Depends(get_db),
) -> MediaAssetDeleteResponse:
    """
    Safely delete a media asset:
    - Verifies the asset exists.
    - Prevents deletion if referenced by any answer_blocks (HTTP 409 Conflict).
    - Unlinks the physical file from storage.
    - Deletes the database record.
    """
    media_uuid = _parse_media_uuid(media_id)
    media_asset = db.get(MediaAsset, media_uuid)
    if media_asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media asset with id '{media_id}' not found.",
        )

    # Reference check: Ensure no answer_blocks reference this media asset
    ref_count = (
        db.query(AnswerBlock)
        .filter(AnswerBlock.media_id == media_uuid)
        .count()
    )
    if ref_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete media asset '{media_id}': it is referenced by {ref_count} answer block(s).",
        )

    file_name = media_asset.file_name
    storage_key = media_asset.storage_key

    # Delete physical file from storage
    delete_stored_file(storage_key)

    # Delete database record
    db.delete(media_asset)
    db.commit()

    return MediaAssetDeleteResponse(
        message=f"Media asset '{file_name}' successfully deleted.",
        id=str(media_uuid),
        file_name=file_name,
    )
