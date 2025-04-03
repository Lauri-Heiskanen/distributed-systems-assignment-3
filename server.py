import socket
import threading
import json
import time

HOST = ""
PORT = 5000

HEADER_LENGTH = 16
TEXT_ENCODING = "ascii"
PING_INTERVAL = 5
DEFAULT_NICKNAME = "Anon"

SEND_LOCK = threading.Lock()

CONNECTED_CLIENTS = []
PING_NUMBER = 0


def send_to_client(socket, msg):
    length = len(msg)
    SEND_LOCK.acquire()
    socket.sendall(
        (str(length) + " " * (HEADER_LENGTH - len(str(length)))).encode(TEXT_ENCODING)
    )
    socket.sendall(msg.encode(TEXT_ENCODING))
    SEND_LOCK.release()


def handle_client(client_socket: socket.socket):
    global PING_NUMBER

    client_socket.settimeout(2 * PING_INTERVAL)

    client = {
        "socket": client_socket,
        "nickname": DEFAULT_NICKNAME,
        "is_connected": True,
    }
    CONNECTED_CLIENTS.append(client)

    while True:
        try:
            msg_len = int(str(client_socket.recv(HEADER_LENGTH), TEXT_ENCODING).strip())
            msg = client_socket.recv(msg_len).decode(TEXT_ENCODING)
            req = json.loads(msg)

            if req["action"] == "set_nickname":
                if req["target"] not in {c["nickname"] for c in CONNECTED_CLIENTS}:
                    client["nickname"] = req["target"]
                    response = json.dumps(
                        {
                            "action": "set_nickname",
                            "status": "success",
                        }
                    )
                    send_to_client(client_socket, response)
                else:
                    response = json.dumps(
                        {
                            "action": "send_message",
                            "status": "failure",
                            "reason": "Nickname was not free",
                        }
                    )
                    send_to_client(client_socket, response)

            elif req["action"] == "get_clients":
                response = json.dumps(
                    {
                        "action": "get_clients",
                        "status": "success",
                        "nicknames": [
                            c["nickname"]
                            for c in CONNECTED_CLIENTS
                            if c["is_connected"]
                        ],
                    }
                )
                send_to_client(client_socket, response)

            elif req["action"] == "send_message":
                if req["target"] != DEFAULT_NICKNAME and req["target"] in {
                    c["nickname"] for c in CONNECTED_CLIENTS if c["is_connected"]
                }:
                    target_client_socket = None
                    for c in CONNECTED_CLIENTS:
                        if c["is_connected"] and c["nickname"] == req["target"]:
                            target_client_socket = c["socket"]
                            break

                    if target_client_socket:
                        try:
                            send_to_client(
                                target_client_socket,
                                json.dumps(
                                    {
                                        "action": "receive_message",
                                        "sender": client["nickname"],
                                        "text": req["message"],
                                    }
                                ),
                            )
                            response = json.dumps(
                                {
                                    "action": "send_message",
                                    "status": "success",
                                }
                            )
                        except:
                            response = json.dumps(
                                {
                                    "action": "send_message",
                                    "status": "failure",
                                    "reason": "Sending to client failed",
                                }
                            )

                    else:
                        response = json.dumps(
                            {
                                "action": "send_message",
                                "status": "failure",
                                "reason": "Target client was not connected",
                            }
                        )
                    send_to_client(client_socket, response)
                else:
                    response = json.dumps(
                        {
                            "action": "send_message",
                            "status": "failure",
                            "reason": "Nickname was not found or it was the default name",
                        }
                    )
                    send_to_client(client_socket, response)

            elif req["action"] == "close_connection":
                break

            elif req["action"] == "ping":
                if req["number"] != PING_NUMBER:
                    client["is_connected"] = False
                    client_socket.close()
                    break
        except:
            client["is_connected"] = False
            client_socket.close()
            break


def ping_clients():
    global PING_NUMBER

    while True:
        for c in CONNECTED_CLIENTS:
            if c["is_connected"]:
                try:
                    send_to_client(
                        c["socket"],
                        json.dumps(
                            {
                                "action": "ping",
                                "number": PING_NUMBER,
                            }
                        ),
                    )
                except:
                    c["is_connected"] = False
                    c["socket"].close()
        time.sleep(PING_INTERVAL)
        PING_NUMBER += 1


def run_server():
    # from https://docs.python.org/3.9/library/socket.html#socket.create_server
    addr = (HOST, PORT)
    if socket.has_dualstack_ipv6():
        server_socket = socket.create_server(
            addr, family=socket.AF_INET6, dualstack_ipv6=True
        )
    else:
        server_socket = socket.create_server(addr)

    server_socket.listen(5)

    pinging_thread = threading.Thread(target=ping_clients)
    pinging_thread.start()

    while True:
        (client_socket, client_address) = server_socket.accept()
        print("Connected by", client_address)

        client_thread = threading.Thread(target=handle_client, args=(client_socket,))
        client_thread.start()


if __name__ == "__main__":
    run_server()
