import sys
import argparse
import socket
import os
import time
import base64
import json
import threading

def send_msg(conn, msg):
    serialized = json.dumps(msg).encode('utf-8')
    # x=len(serialized) 
    # x=str(x)
    # x=x+'\n'
    # x=bytes(x,encoding='utf-8')
    # conn.send(x)
    # conn.sendall(serialized)
    conn.send(b'%d\n' % len(serialized))
    conn.sendall(serialized)

def send_delshared_file(conn, username,filename):
    msg = {
        'type': 'file_deleteshared',
        'filename': filename
    }
    send_msg(conn, msg)
    send_msg(conn,username)

def send_shared_file(conn, filename,username):
    with open(filename, "rb") as file:
        data = base64.b64encode(file.read()).decode('utf-8')
        msg = {
            'type': 'file_share',
            'filename': filename,
            'data': data
        }
        send_msg(conn, msg)
        send_msg(conn,username)

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
    filename2 = "Sharefile.dropbin"
    if os.path.isfile(os.path.join(os.getcwd(), filename2)):
        with open(filename2, "r") as file:
            for line in file:
                line_words = line.split()
                if (line_words[0]==filename):
                    for i in range(1,len(line_words)):
                        user = line_words[i] 
                        send_delshared_file(conn,user,line_words[0])

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


def selectfiles(conn,client_dir):
    filename1 = "Selectfile.dropbin"
    filename2 = "Sharefile.dropbin"
    if os.path.isfile(os.path.join(client_dir, filename1)) and os.path.isfile(os.path.join(client_dir, filename2)):
        sfiles = []         #Selectedfiles
        with open(filename1, "r") as file:
            for line in file:
                words = line.split()
                sfiles.append(words[0])
            file.close()
        with open(filename2, "r") as file:
            for line in file:
                line_words = line.split()
                shared_file = line_words[0]
                if os.path.isfile(os.path.join(client_dir, shared_file)) and shared_file in sfiles:
                    for i in range(1,len(line_words)):
                        user = line_words[i]
                        send_shared_file(conn,shared_file,user)
                elif os.path.isfile(os.path.join(client_dir, shared_file)):
                    for i in range(1,len(line_words)):
                        user = line_words[i]
                        #Delete this file from this user 
                        send_delshared_file(conn,user,shared_file)
            file.close()
    elif os.path.isfile(os.path.join(client_dir, filename2)):
        with open(filename2, "r") as file:
            for line in file:
                line_words = line.split()
                shared_file = line_words[0]
                if os.path.isfile(os.path.join(client_dir, shared_file)):
                    for i in range(1,len(line_words)):
                        user = line_words[i]
                        send_shared_file(conn,shared_file,user)
            file.close()

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

def watch_dir(s, client_dir):
    last_file_list = {}
    while True:
        time.sleep(1)
        selectfiles(s,client_dir)
        changes, last_file_list = get_changes(client_dir, last_file_list)
        handle_dir_change(s, changes)

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



def handle_client(s, client_dir):
    while True:
        msg = get_message(s)
        if msg['type'] == 'file_add':
            if add_file(client_dir, msg['filename'], msg['data']):
                print('file added ', os.path.join(client_dir, msg['filename']))
            
        elif msg['type'] == 'file_delete':
            print('file deleted ', os.path.join(client_dir, msg['filename']))
            delete_file(client_dir, msg['filename'])
    s.close() 
            
def client(server_addr, server_port,username, client_dir):
    s = socket.socket()
    s.connect((server_addr, server_port))
    send_username(s,username)
    threading.Thread(target=handle_client, args=(s, os.getcwd())).start()
    threading.Thread(target=watch_dir,args=(s, client_dir)).start()
    # s.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("server_addr", help="Address of the server.")
    parser.add_argument("server_port", type=int, help="Port number the server is listening on.")
    parser.add_argument("username", help="Username of the user.")
    args = parser.parse_args()
    client(args.server_addr, args.server_port, args.username, os.getcwd())