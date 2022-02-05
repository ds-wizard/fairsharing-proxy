import base64


def base64credentials(username: str, password: str) -> str:
    userpass = f'{username}:{password}'
    encoded = base64.b64encode(userpass.encode('utf-8')).decode('utf-8')
    return encoded


if __name__ == '__main__':
    username = input('Login: ')
    password = input('Password: ')
    token = base64credentials(
        username=username,
        password=password,
    )
    print(token)
