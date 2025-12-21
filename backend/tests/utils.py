# ruff: noqa: S311

import random
import string


def random_lower_string(length: int = 10) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))


def random_email() -> str:
    return f"{random_lower_string()}@{random_lower_string()}.com"


def random_username() -> str:
    return random_lower_string(8)


def strong_password() -> str:
    # Needs 12 chars, upper, lower, digit, special
    # Let's guarantee one of each and then fill the rest
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    pwd = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice("!@#$%^&*"),
    ]
    pwd += random.choices(chars, k=10)  # 4 + 10 = 14 chars
    random.shuffle(pwd)
    return "".join(pwd)
