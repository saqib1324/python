import sys
import argparse
import socket
import os
import time
import base64
import json

def send_msg(conn, msg):
    serialized = json.dumps(msg).encode('utf-8')
    conn.send(b'%d\n' % len(serialized))
    conn.sendall(serialized)

def get_file_list(client_dir):
    files = os.listdir(client_dir)
    files = [file for file in files if os.path.isfile(os.path.join(client_dir, file))]
    file_list = {}
    for file in files:
        path = os.path.join(client_dir, file)
        mtime = os.path.getmtime(path)
        ctime = os.path.getctime(path)
        file_list[file] = max(ctime, mtime)

    return file_list

def send_new_file(conn, filename):
    with open(filename, "rb") as file:
        data = base64.b64encode(file.read()).decode('utf-8')
        msg = {
            'type': 'file_add',
            'filename': filename,
            'data': data
        }
        send_msg(conn, msg)

def send_username(conn, username):
    msg = {
        'user': username
    }
    send_msg(conn, msg)

def send_delete_file(conn, filename):
    msg = {
        'type': 'file_delete',
        'filename': filename
    }
    send_msg(conn, msg)

def get_changes(client_dir, last_file_list):
    file_list = get_file_list(client_dir)
    changes = {}
    for filename, mtime in file_list.items():
        if filename not in last_file_list or last_file_list[filename] < mtime:
            changes[filename] = 'file_add'

    for filename, time in last_file_list.items():
        if filename not in file_list:
            changes[filename] = 'file_delete'

    return (changes, file_list)

def handle_dir_change(conn, changes):
    for filename, change in changes.items():
        if change == 'file_add':
            print('new file added ', filename)
            send_new_file(conn, filename)
        elif change == 'file_delete':
            print('file deleted ', filename)
            send_delete_file(conn, filename)

def watch_dir(conn, client_dir, handler):
    last_file_list = {}
    while True:
        time.sleep(1)
        changes, last_file_list = get_changes(client_dir, last_file_list)
        handler(conn, changes)

def client(server_addr, server_port,username, client_dir):
    s = socket.socket()
    s.connect((server_addr, server_port))
    send_username(s,username)
    watch_dir(s, client_dir, handle_dir_change)
    s.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("server_addr", help="Address of the server.")
    parser.add_argument("server_port", type=int, help="Port number the server is listening on.")
    parser.add_argument("username", help="Username of the user.")
    args = parser.parse_args()
    client(args.server_addr, args.server_port, args.username, os.getcwd())