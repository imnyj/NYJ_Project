"""secrets_tool — encrypt/decrypt API keys in .env.

CLI entry points:
    python -m secrets_tool init               # create .env.salt
    python -m secrets_tool encrypt KEY        # prompt for value, store ENC: in .env
    python -m secrets_tool decrypt KEY        # print plaintext (use cautiously)
    python -m secrets_tool list               # show which keys are encrypted
    python -m secrets_tool change-password    # re-encrypt all ENC: keys with new pw
"""
__all__: list[str] = []
