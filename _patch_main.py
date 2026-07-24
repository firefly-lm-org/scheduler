import io

p = r"D:\firefly-client\firefly-client\app\main.py"
s = open(p, encoding="utf-8").read()

old_register = (
    'def register(\n'
    '    username: str = typer.Option(..., "--username", "-u", prompt=True),\n'
    '    password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True),\n'
    '    server: str = typer.Option(None, "--server", "-s", help="\u8c03\u5ea6\u4e2d\u5fc3\u5730\u5740"),\n'
    '):'
)
new_register = (
    'def register(\n'
    '    username: str = typer.Option(..., "--username", prompt="\u7528\u6237\u540d"),\n'
    '    password: str = typer.Option(..., "--password", prompt="\u5bc6\u7801", hide_input=True),\n'
    '    server: str = typer.Option(None, "--server", help="\u8c03\u5ea6\u4e2d\u5fc3\u5730\u5740"),\n'
    '):'
)
assert old_register in s, "register block not found"
s = s.replace(old_register, new_register)

old_login = (
    'def login(\n'
    '    username: str = typer.Option(..., "--username", "-u", prompt=True),\n'
    '    password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True),\n'
    '):'
)
new_login = (
    'def login(\n'
    '    username: str = typer.Option(..., "--username", prompt="\u7528\u6237\u540d"),\n'
    '    password: str = typer.Option(..., "--password", prompt="\u5bc6\u7801", hide_input=True),\n'
    '):'
)
assert old_login in s, "login block not found"
s = s.replace(old_login, new_login)

open(p, "w", encoding="utf-8").write(s)
print("patched register/login options successfully")
