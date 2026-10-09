from fastapi import Request


def client_address(request: Request) -> str | None:
    """Адрес клиента: настоящий nginx передаёт в X-Real-IP, сам бэкенд видит только nginx."""
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    if request.client is not None:
        return request.client.host
    return None
