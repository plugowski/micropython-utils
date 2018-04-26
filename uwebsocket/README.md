# Simple Usage

```python
from uwebsocket import *


class AppServer(WebSocketServer):

    def _make_client(self, conn):
        return AppClient(conn)


class AppClient(WebSocketClient):

    def __init__(self, conn):
        super().__init__(conn)

    def process(self):
        try:

            msg = self.connection.read()
            if msg:
                msg = msg.decode("utf-8")
                self.connection.write('RESPONSE:' + msg)

        except ClientClosedError:
            self.connection.close()
```