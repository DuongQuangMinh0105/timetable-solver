from typing import Protocol


class JobDispatcherPort(Protocol):
    """Đẩy job giải vào hàng đợi. Hiện thực: local, Service Bus/Pub-Sub/SQS."""