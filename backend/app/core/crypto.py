from cryptography.fernet import Fernet, InvalidToken


def make_fernet(secret_key: str) -> Fernet:
    """Шифратор на ключе META_SECRET_KEY."""
    try:
        return Fernet(secret_key.encode())
    except ValueError as error:
        raise RuntimeError(
            "META_SECRET_KEY должен быть ключом Fernet: 32 байта в urlsafe base64, 44 символа"
        ) from error


def encrypt_secret(plain_text: str, secret_key: str) -> str:
    """Шифрует пароль для хранения в meta-db."""
    return make_fernet(secret_key).encrypt(plain_text.encode()).decode()


def decrypt_secret(token: str, secret_key: str) -> str:
    """Расшифровывает пароль из meta-db."""
    try:
        return make_fernet(secret_key).decrypt(token.encode()).decode()
    except InvalidToken as error:
        raise ValueError(
            "Не удалось расшифровать пароль: META_SECRET_KEY не тот, которым он шифровался"
        ) from error
