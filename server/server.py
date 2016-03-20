import sys
import argparse
import socket
import os
import time
import threading
import base64
import json

def get_user_dir(server_dir, username):
    path = os.path.join(server_dir, username)
    os.makedirs(path, exist_ok=True)
    return path
    
def send_msg(conn, msg):
    serialized = json.dumps(msg).encode('utf-8')
    x=len(serialized) 
    x=str(x)
    x=x+'\n'
    x=bytes(x,encoding='utf-8')
    conn.send(x)
    conn.sendall(serialized)
    # conn.send(b"%d\n" % len(serialized))
    # conn.sendall(serialized)
    
def send_new_file(conn, filename,username):
    path = os.path.join(os.getcwd(),username)
    file_path = os.path.join( path , filename)
    if os.path.isfile(file_path):
        with open(file_path, "rb") as file:
            data = base64.b64encode(file.read()).decode('utf-8')
            msg = {
                'type': 'file_add',
                'filename': filename,
                'data': data
            }
            send_msg(conn, msg)
        print (file_path + ' sent')
            
def send_delete_file(conn, filename,username):
    # path = os.path.join(os.getcwd(),username)
    # file_path = os.path.join( path , filename)
    # if os.path.isfile(file_path):
    msg = {
        'type': 'file_delete',
        'filename': filename
    }
    send_msg(conn, msg)

def add_file(client_dir, filename, data):
    path = os.path.join(client_dir, filename)
    if not os.path.isfile(path):
        with open(path, 'wb') as file:
            file.write(base64.b64decode(data.encode('utf-8')))
        return 1
    else:
        return 0
        
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

def handle_client(conn, client_dir_server):
    while True:
        msg = get_message(conn)
        if msg['type'] == 'file_share':
            shared_user = get_message(conn)
            path = os.path.join(os.path.dirname(client_dir_server),shared_user)
            if os.path.exists(path):    # if user directory exists
                if not os.path.isfile(os.path.join(path, msg['filename'])):     #if shared file is not already in directory
                    if add_file(path, msg['filename'], msg['data']):
                        print('file shared ', os.path.join(path, msg['filename']))
                    
        elif msg['type'] == 'file_deleteshared':
            shared_user = get_message(conn)
            path = os.path.join(os.path.dirname(client_dir_server),shared_user)
            if os.path.exists(path):
                if os.path.isfile(os.path.join(path, msg['filename'])):
                    delete_file(path, msg['filename'])
                    print('file deleted ', os.path.join(path, msg['filename']))
        elif msg['type'] == 'file_add':
            if add_file(client_dir_server, msg['filename'], msg['data']):
                print('file added ', os.path.join(client_dir_server, msg['filename']))
        elif msg['type'] == 'file_delete':
            print('file deleted ', os.path.join(client_dir_server, msg['filename']))
            delete_file(client_dir_server, msg['filename'])

    conn.close()

def get_file_list(client_dir_server):
    files = os.listdir(client_dir_server)
    files = [file for file in files if os.path.isfile(os.path.join(client_dir_server, file))]
    file_list = {}
    for file in files:
        path = os.path.join(client_dir_server, file)
        mtime = os.path.getmtime(path)
        ctime = os.path.getctime(path)
        file_list[file] = max(ctime, mtime)

    return file_list

def get_changes(client_dir_server, last_file_list):
    file_list = get_file_list(client_dir_server)
    changes = {}
    for filename, mtime in file_list.items():
        if filename not in last_file_list or last_file_list[filename] < mtime:
            changes[filename] = 'file_add'

    for filename, time in last_file_list.items():
        if filename not in file_list:
            changes[filename] = 'file_delete'

    return (changes, file_list)

def handle_dir_change(conn, changes,username):
    for filename, change in changes.items():
        if change == 'file_add':
            print('new file added ', os.path.join(os.path.join(os.getcwd(),username),filename))
            send_new_file(conn, filename,username)
        elif change == 'file_delete':
            print('file deleted ', os.path.join(os.path.join(os.getcwd(),username),filename))
            send_delete_file(conn, filename,username)


def watch_dir(conn, client_dir_server,username):
    last_file_list = {}
    while True:
        time.sleep(1)
        changes, last_file_list = get_changes(client_dir_server, last_file_list)
        handle_dir_change(conn, changes,username)

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
        threading.Thread(target=watch_dir,args=(conn,get_user_dir(server_dir, username),username)).start()
    s.close()
     
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("port", type=int, help="Port number the server will listen on.")
    args = parser.parse_args()
    server(args.port, os.getcwd())
