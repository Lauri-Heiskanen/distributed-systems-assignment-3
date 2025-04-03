import socket
import threading
import json
import time
import os

HOST = "localhost"
PORT = 5000

HEADER_LENGTH = 16
TEXT_ENCODING = "ascii"
PING_INTERVAL = 5

PRINT_LOCK = threading.Lock()
SEND_LOCK = threading.Lock()

RECEIVED_MESSAGES = []


def receive(socket):
    while True:
        try:
            data_len = int(socket.recv(HEADER_LENGTH).decode(TEXT_ENCODING).strip())
            data = socket.recv(data_len).decode(TEXT_ENCODING)
            res = json.loads(data)
            if res["action"] == "receive_message":
                PRINT_LOCK.acquire()
                print(f'\n{res["sender"]}: {res["text"]}\n')
                PRINT_LOCK.release()
            elif res["action"] == "ping":
                send_to_server(socket, data)
            else:
                RECEIVED_MESSAGES.append(res)
        except:
            print("Exiting")
            os._exit(0)


def read_from_server():
    while len(RECEIVED_MESSAGES) == 0:
        time.sleep(0.1)
    return RECEIVED_MESSAGES.pop(0)


def send_to_server(socket, msg):
    length = len(msg)
    SEND_LOCK.acquire()
    socket.sendall(
        (str(length) + " " * (HEADER_LENGTH - len(str(length)))).encode(TEXT_ENCODING)
    )
    socket.sendall(msg.encode(TEXT_ENCODING))
    SEND_LOCK.release()


if __name__ == "__main__":
    # from https://docs.python.org/3.9/library/socket.html#socket.create_server
    if socket.has_dualstack_ipv6():
        client_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    else:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    client_socket.settimeout(2 * PING_INTERVAL)

    try:
        client_socket.connect((HOST, PORT))
        print("Connected to server")
    except:
        print("Failed connecting to server")
        exit(0)

    reading_thread = threading.Thread(target=receive, args=(client_socket,))
    reading_thread.start()

    try:
        while True:

            PRINT_LOCK.acquire()
            print(
                "\nWhat would you like to do?\n1: set nickname\n2: Send text to other connected clients\n3: Disconnect from server and quit\n"
            )
            PRINT_LOCK.release()
            action_choice = input().strip()

            if action_choice == "1":
                PRINT_LOCK.acquire()
                request = json.dumps(
                    {
                        "action": "set_nickname",
                        "target": input("Enter nickname: "),
                    }
                )
                PRINT_LOCK.release()
                try:
                    send_to_server(client_socket, request)
                    response = read_from_server()
                    PRINT_LOCK.acquire()
                    if response["status"] == "success":
                        print("Nickname set")
                    else:
                        print("Failure:", response["reason"])
                    PRINT_LOCK.release()
                except:
                    PRINT_LOCK.acquire()
                    print("Something went wrong")
                    print("Closing connection")
                    PRINT_LOCK.release()
                    client_socket.close()
                    break

            elif action_choice == "2":
                request = json.dumps(
                    {
                        "action": "get_clients",
                    }
                )
                send_to_server(client_socket, request)
                response = read_from_server()
                if response["status"] == "success":
                    PRINT_LOCK.acquire()
                    print("\n".join(response["nicknames"]))
                    PRINT_LOCK.release()
                else:
                    PRINT_LOCK.acquire()
                    print("Failed while getting clients")
                    print("Closing connection")
                    PRINT_LOCK.release()
                    client_socket.close()
                    break

                PRINT_LOCK.acquire()
                request = json.dumps(
                    {
                        "action": "send_message",
                        "target": input("Enter receiver: "),
                        "message": input("Enter message: "),
                    }
                )
                PRINT_LOCK.release()
                send_to_server(client_socket, request)

                try:
                    response = read_from_server()
                    PRINT_LOCK.acquire()
                    if response["status"] == "success":
                        print("Message sent")
                    else:
                        print("Failure:", response["reason"])
                    PRINT_LOCK.release()
                except:
                    PRINT_LOCK.acquire()
                    print("Failed while sending the message")
                    print("Closing connection")
                    PRINT_LOCK.release()
                    client_socket.close()
                    break

            elif action_choice == "3":
                request = json.dumps(
                    {
                        "action": "close_connection",
                    }
                )
                try:
                    send_to_server(client_socket, request)
                except:
                    pass
                PRINT_LOCK.acquire()
                print("Closing socket")
                PRINT_LOCK.release()
                client_socket.close()
                break

            else:
                PRINT_LOCK.acquire()
                print("Please input one of the given options")
                PRINT_LOCK.release()
    except:
        print("something went wrong")
        print("exiting")
