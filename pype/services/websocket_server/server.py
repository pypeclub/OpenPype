import uuid
import copy
import json
import logging
from socketserver import TCPServer
from websocket_server import WebSocketHandler, WebsocketServer
from pypeapp import Logger

log = Logger().get_logger(__name__)


class PypeWebSocketHandler(WebSocketHandler):
    client = None
    endpoint = None

    def handshake(self):
        """Pip version of websocket server has invalid version of handshake."""
        headers = self.read_http_headers()

        try:
            assert headers['upgrade'].lower() == 'websocket'
        except AssertionError:
            self.keep_alive = False
            return

        try:
            key = headers['sec-websocket-key']
        except KeyError:
            log.warning("Client tried to connect but was missing a key")
            self.keep_alive = False
            return

        response = self.make_handshake_response(key)
        self.handshake_done = self.request.send(response.encode())
        self.valid_client = True
        self.server._new_client_(self)

    def read_http_headers(self):
        """Get information about client from headers.

        This methodwas overriden to be able get endpoint from request.
        """
        headers = {}
        # first line should be HTTP GET
        http_get = self.rfile.readline().decode().strip()
        http_parts = http_get.split(" ")
        assert not len(http_parts) != 3, (
            "Expected 3 parts of first header line."
        )
        _method, _endpoint, _protocol = http_parts

        # Store endpoint
        self.endpoint = _endpoint

        assert _method.upper().startswith("GET")
        # remaining should be headers
        while True:
            header = self.rfile.readline().decode().strip()
            if not header:
                break
            head, value = header.split(":", 1)
            headers[head.lower().strip()] = value.strip()
        return headers

    def cancel(self):
        """To stop handler's loop."""
        self.keep_alive = False
        self.server._client_left_(self)
        self.client = None


class Client:
    """Representation of client connected to server.

    Client has 2 immutable atributes `id` and `handler` and `data` which is
    dictionary where additional data to client may be stored.

    Client object behaves as dictionary, all accesses are to `data` attribute.
    Except getting `id`. It is possible to get `id` as attribute or as dict
    item.
    """

    def __init__(self, handler):
        self._handler = handler
        self._id = str(uuid.uuid4())
        self._data = {}
        handler.client = self

    def __getitem__(self, key):
        if key == "id":
            return self.id
        return self._data[key]

    def __setitem__(self, key, value):
        if key == "id":
            raise TypeError("'id' is not mutable attribute.")
        self._data[key] = value

    def __repr__(self):
        return "Client <{}> ({})".format(self.id, self.address)

    def __iter__(self):
        for item in self.items():
            yield item

    def get(self, key, default=None):
        self._data.get(key, default)

    def items(self):
        return self._data.items()

    def values(self):
        return self._data.values()

    def keys(self):
        return self._data.keys()

    def to_dict(self):
        """Converts client to pure dictionary."""
        return {
            "id": self._id,
            "handler": self._handler,
            "data": copy.deepcopy(self._data)
        }

    @property
    def handler(self):
        return self._handler

    @property
    def server(self):
        return self._handler.server

    @property
    def address(self):
        """Client's adress, should be localhost and random port."""
        return self._handler.client_address

    @property
    def endpoint(self):
        """Endpoint where client was registered."""
        return self._handler.endpoint

    @property
    def id(self):
        """Uniqu identifier of client."""
        return self._id

    @property
    def data(self):
        return self.data

    def cancel(self):
        """Stops client communication. This is not API method!"""
        self._handler.cancel()
        self._handler = None

    def send_message(self, message):
        self.handler.send_message(message)


class Namespace:
    def __init__(self, endpoint, server=None):
        endpoint_parts = [part for part in endpoint.split("/") if part]
        self.endpoint = "/{}".format("/".join(endpoint_parts))
        self.server = server
        self.clients = {}

    def on_message(self, message, client):
        pass

    def _new_client(self, client):
        self.clients[client.id] = client
        self.new_client(client)

    def new_client(self, client):
        """Possible callback when new client is added."""
        pass

    def _client_left(self, client):
        if client.id in self.clients:
            self.client_left(client)
            self.clients.pop(client.id, None)

    def client_left(self, client):
        """Possible callback when client left the server"""
        pass

    def send_message(self, client, message):
        """Send message to client, but it can be done directly via client."""
        client.send_message(message)

    def send_message_to_all(self, message, except_ids=[]):
        """Sends message to all clients."""
        for client in self.clients.values():
            if except_ids and client.id in except_ids:
                continue
            client.send_message(message)


class ExampleNamespace(Namespace):
    # Called for every client connecting (after handshake)
    def new_client(self, client):
        print("New client connected and was given id {}".format(client["id"]))
        msg = json.dumps({
            "id": client["id"],
            "action": "new_connection"
        })
        client.send_message(msg)

    # Called for every client disconnecting
    def client_left(self, client):
        print("Client({}) disconnected".format(client["id"]))

    # Called when a client sends a message
    def on_message(self, message, client):
        print("Client({}) said: {}".format(client["id"], message))


class PypeWebsocketServer(WebsocketServer):
    def __init__(
        self, port, host="127.0.0.1", handler=None, loglevel=logging.WARNING
    ):
        if handler is None:
            handler = PypeWebSocketHandler
        TCPServer.__init__(self, (host, port), handler)
        self.port = self.socket.getsockname()[1]

        self.clients = {}
        self.namespaces = {
            "/example": ExampleNamespace("/", self)
        }

    def _message_received_(self, handler, msg):
        namespace = self.namespaces.get(handler.endpoint)
        if namespace:
            namespace.on_message(msg, handler.client)

    def _new_client_(self, handler):
        client = Client(handler)
        self.clients[client.id] = client
        namespace = self.namespaces.get(handler.endpoint)
        if namespace:
            namespace._new_client(client)
            return

        client.send_message(json.dumps({
            "error": "Namespace '{}' is not registered.".format(
                handler.endpoint
            )
        }))
        client.cancel()

    def _client_left_(self, handler):
        client = handler.client
        if client is not None:
            namespace = self.namespaces.get(handler.endpoint)
            if namespace:
                namespace._client_left(client)

            self.clients.pop(client.id, None)

    def _unicast_(self, to_client, msg):
        to_client.handler.send_message(msg)

    def _multicast_(self, msg):
        for client in self.clients.values():
            self._unicast_(client, msg)

    def handler_to_client(self, handler):
        for client in self.clients.values():
            if client.handler == handler:
                return client

    def send_message(self, client, msg):
        self._unicast_(client, msg)

    def send_message_to_all(self, msg):
        self._multicast_(msg)

    def start(self):
        self.run_forever()

    def stop(self):
        self.server_close()
