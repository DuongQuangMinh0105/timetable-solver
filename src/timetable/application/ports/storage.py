from typing import Protocol


class StoragePort(Protocol):
    """Lưu và đọc file (input JSON/Excel, kết quả). Hiện thực: local, Blob/S3/GCS."""
