# MT5 Agent Credential Storage

Never store MT5 login/password in plaintext in agent files. Use one of these methods:

## Windows: DPAPI (Recommended for XM Global)

```python
import dpapi_core

encrypted = dpapi_core.encrypt(plain_password.encode())
# Store encrypted bytes to file

# Later, decrypt when needed
password = dpapi_core.decrypt(encrypted).decode()
```

- Only decrypts on the same machine + same Windows user account
- Password never appears in files or logs

## Environment Variables

```python
import os
login = os.environ.get("MT5_LOGIN")
password = os.environ.get("MT5_PASSWORD")
server = os.environ.get("MT5_SERVER", "XMGlobal-MT5 9")
```

- Set once per session: `export MT5_LOGIN=336883354`
- Not persisted across reboots (Windows) or terminal sessions (Linux)

## Config File (If DPAPI Unavailable)

```python
# config.py - NEVER commit to version control
MT5_CONFIG = {
    "login": os.environ.get("MT5_LOGIN", "336883354"),
    "password": os.environ.get("MT5_PASSWORD"),
    "server": "XMGlobal-MT5 9"
}
```

- Add to `.gitignore` immediately
- Only acceptable when DPAPI is not available (e.g., Linux without Wine)

## Verification

Test that credentials work before running live:

```python
import MetaTrader5 as mt5
if mt5.initialize(login=login, password=password, server=server):
    acc = mt5.account_info()
    print(f"Connected: {acc.login} / {acc.server}")
    mt5.shutdown()
else:
    print(f"Failed: {mt5.last_error()}")
```
