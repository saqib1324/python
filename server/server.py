import sys
import argparse
import socket
import os
import threading
import base64
import json

def get_user_dir(server_dir, username):
    path = os.path.join(server_dir, username)
    os.makedirs(path, exist_ok=True)
    return path

def add_file(client_dir, filename, data):
    path = os.path.join(client_dir, filename)
    with open(path, 'wb') as file:
        file.write(base64.b64decode(data.encode('utf-8')))

def delete_file(client_dir, filename):
    path = os.path.join(client_dir, filename)
    if os.path.exists(path):
        os.remove(path)

def get_message(conn):
    length_str = b''
    char = conn.recv(1)
    while char != b'\n':
        length_str += char
        char = conn.recv(1)
    total = int(length_str)
    off = 0
    msg = b''
    while off < total:
        temp = conn.recv(total - off)
        off = off + len(temp)
        msg = msg + temp
    return json.loads(msg.decode('utf-8'))

def handle_client(conn, client_dir):
    while True:
        msg = get_message(conn)
        if msg['type'] == 'file_share':
            shared_user = get_message(conn)
            path = os.path.join(os.path.dirname(client_dir),shared_user)
            if not os.path.isfile(os.path.join(path, msg['filename'])):
                print('file shared ', os.path.join(path, msg['filename']))
                add_file(path, msg['filename'], msg['data'])
        elif msg['type'] == 'file_add':
            print('file added ', os.path.join(client_dir, msg['filename']))
            add_file(client_dir, msg['filename'], msg['data'])
        elif msg['type'] == 'file_delete':
            print('file deleted ', os.path.join(client_dir, msg['filename']))
            delete_file(client_dir, msg['filename'])

    conn.close()

def server(port, server_dir):
    host = socket.gethostbyname(socket.gethostname())

    s = socket.socket()
    s.bind((host, port))
    s.listen(10)

    print("Host ", host, " is listening on ", port)

    while True:
        conn, addr = s.accept()
        print("Got connection from ", addr)
        msg = get_message(conn)
        username = msg['user']
        threading.Thread(target=handle_client, args=(conn, get_user_dir(server_dir, username))).start()

    s.close()
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("port", type=int, help="Port number the server will listen on.")
    args = parser.parse_args()
    server(args.port, os.getcwd())