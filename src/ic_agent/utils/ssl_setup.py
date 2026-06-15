"""Make ``ssl``/``httpx`` trust the OS certificate store.

Corporate networks often terminate TLS through a proxy whose root CA is
trusted by Windows but not by Python's bundled ``certifi`` store. ``httpx``
(used by the OpenAI SDK) then fails with
``SSL: CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate``
even though the same host is reachable from PowerShell/curl. ``truststore``
patches ``ssl.SSLContext`` to defer to the native OS trust store instead.
"""

import truststore

_injected = False


def ensure_system_truststore() -> None:
    global _injected
    if not _injected:
        truststore.inject_into_ssl()
        _injected = True
