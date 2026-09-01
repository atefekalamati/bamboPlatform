"""Safe local DWG storage with streaming validation and atomic finalization."""

import hashlib
import re
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from persiantools.jdatetime import JalaliDate

from app.config import get_dwg_max_bytes, get_dwg_storage_backend, get_dwg_storage_root
from app.exceptions import SecurityError

ALLOWED_DWG_MIME_TYPES = {
    "application/acad",
    "application/autocad_dwg",
    "application/dwg",
    "application/octet-stream",
    "application/x-acad",
    "application/x-autocad",
    "image/vnd.dwg",
}
DWG_SIGNATURE_PATTERN = re.compile(rb"AC10\d{2}")


@dataclass
class StagedDwg:
    path: Path
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    signature: str


@dataclass
class StoredDwg:
    absolute_path: Path
    storage_key: str
    standardized_filename: str


def _file_error(code: str, message: str, reason: str) -> SecurityError:
    return SecurityError(
        code=code,
        message=message,
        status_code=422,
        errors=[{"field": "file", "reason": reason}],
    )


def _discard_temp_path(path: Path) -> None:
    path.unlink(missing_ok=True)
    with suppress(OSError):
        path.parent.rmdir()


def discard_staged_upload(staged: StagedDwg) -> None:
    _discard_temp_path(staged.path)


async def stage_upload(upload: UploadFile) -> StagedDwg:
    get_dwg_storage_backend()
    original_filename = upload.filename or ""
    if (
        not original_filename.lower().endswith(".dwg")
        or "/" in original_filename
        or "\\" in original_filename
        or ".." in original_filename
    ):
        raise _file_error("DWG_INVALID_EXTENSION", "فقط فایل DWG مجاز است.", "invalid_extension")

    mime_type = (upload.content_type or "").lower()
    if mime_type not in ALLOWED_DWG_MIME_TYPES:
        raise _file_error("DWG_INVALID_MIME", "نوع محتوای فایل DWG معتبر نیست.", "invalid_mime")

    root = get_dwg_storage_root()
    temp_directory = root / ".tmp"
    temp_directory.mkdir(parents=True, exist_ok=True)
    file_descriptor, temp_name = tempfile.mkstemp(prefix="dwg-", suffix=".tmp", dir=temp_directory)
    temp_path = Path(temp_name)
    digest = hashlib.sha256()
    size = 0
    signature_bytes = b""
    max_bytes = get_dwg_max_bytes()
    try:
        with open(file_descriptor, "wb", closefd=True) as output:
            while chunk := await upload.read(1024 * 1024):
                if not signature_bytes:
                    signature_bytes = chunk[:6]
                size += len(chunk)
                if size > max_bytes:
                    raise _file_error(
                        "DWG_TOO_LARGE",
                        "حجم فایل DWG بیشتر از حد مجاز است.",
                        "size_limit",
                    )
                digest.update(chunk)
                output.write(chunk)
        if not DWG_SIGNATURE_PATTERN.fullmatch(signature_bytes):
            raise _file_error(
                "DWG_INVALID_SIGNATURE",
                "محتوای فایل با ساختار DWG مطابقت ندارد.",
                "invalid_signature",
            )
        return StagedDwg(
            path=temp_path,
            original_filename=original_filename,
            mime_type=mime_type,
            size_bytes=size,
            sha256=digest.hexdigest(),
            signature=signature_bytes.decode("ascii"),
        )
    except Exception:
        _discard_temp_path(temp_path)
        raise
    finally:
        await upload.close()


def finalize_upload(
    staged: StagedDwg,
    *,
    pilot_code: str,
    floor_code: str,
    version: int,
) -> StoredDwg:
    root = get_dwg_storage_root()
    try:
        target_directory = (root / pilot_code / floor_code).resolve()
        if not target_directory.is_relative_to(root):
            raise _file_error(
                "DWG_STORAGE_ERROR",
                "مسیر ذخیره فایل معتبر نیست.",
                "unsafe_path",
            )
        target_directory.mkdir(parents=True, exist_ok=True)
        jalali_date = JalaliDate.today().strftime("%Y-%m-%d")
        standardized_filename = (
            f"{pilot_code}_{floor_code}_V{version:02d}_{jalali_date}.dwg"
        )
        # The physical key is unique so concurrent uploads cannot overwrite each
        # other before the database uniqueness constraints choose the winner.
        storage_filename = f"{uuid4().hex}_{standardized_filename}"
        target_path = target_directory / storage_filename
        staged.path.replace(target_path)
    except Exception:
        discard_staged_upload(staged)
        raise
    with suppress(OSError):
        staged.path.parent.rmdir()
    return StoredDwg(
        absolute_path=target_path,
        storage_key=target_path.relative_to(root).as_posix(),
        standardized_filename=standardized_filename,
    )


def finalize_shared_upload(staged: StagedDwg, *, pilot_code: str) -> StoredDwg:
    """Store one drawing that several floors will reference.

    The per-floor path in :func:`finalize_upload` encodes a single owner, so a
    shared file lives under the pilot instead. The bytes land once; each floor
    gets its own ``DwgVersion`` row pointing at this one key.
    """
    root = get_dwg_storage_root()
    try:
        target_directory = (root / pilot_code / "shared").resolve()
        if not target_directory.is_relative_to(root):
            raise _file_error(
                "DWG_STORAGE_ERROR",
                "مسیر ذخیره فایل معتبر نیست.",
                "unsafe_path",
            )
        target_directory.mkdir(parents=True, exist_ok=True)
        jalali_date = JalaliDate.today().strftime("%Y-%m-%d")
        standardized_filename = f"{pilot_code}_SHARED_{staged.sha256[:12]}_{jalali_date}.dwg"
        storage_filename = f"{uuid4().hex}_{standardized_filename}"
        target_path = target_directory / storage_filename
        staged.path.replace(target_path)
    except Exception:
        discard_staged_upload(staged)
        raise
    with suppress(OSError):
        staged.path.parent.rmdir()
    return StoredDwg(
        absolute_path=target_path,
        storage_key=target_path.relative_to(root).as_posix(),
        standardized_filename=standardized_filename,
    )


def resolve_storage_key(storage_key: str) -> Path:
    root = get_dwg_storage_root()
    resolved = (root / storage_key).resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise SecurityError("DWG_NOT_FOUND", "فایل DWG پیدا نشد.", 404, [])
    return resolved


def delete_storage_key(storage_key: str) -> None:
    root = get_dwg_storage_root()
    resolved = (root / storage_key).resolve()
    if resolved.is_relative_to(root):
        resolved.unlink(missing_ok=True)
