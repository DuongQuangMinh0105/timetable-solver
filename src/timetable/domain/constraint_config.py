"""Phiên bản cấu hình ràng buộc: tập ràng buộc cứng, ràng buộc mềm và ý nghĩa trọng số.

Đổi quy tắc ràng buộc hoặc ý nghĩa trọng số thì tăng phiên bản và ghi vào `docs/constraints.md`.
Đầu vào có thể khai `constraint_config_version`; thiếu thì coi là phiên bản hiện tại.
"""

CONSTRAINT_CONFIG_VERSION = "1.0"
SUPPORTED_CONSTRAINT_CONFIG_VERSIONS = frozenset({CONSTRAINT_CONFIG_VERSION})


def unsupported_version_message(version: str) -> str:
    supported = ", ".join(sorted(SUPPORTED_CONSTRAINT_CONFIG_VERSIONS))
    return f"constraint_config_version {version!r} không được hỗ trợ (hỗ trợ: {supported})"
