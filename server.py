import socket
import threading
import secrets


class TCPServer:
    room_members_map = {}  # {room_name : [token, token, token, ...]}
    clients_map = {}  # {token : [client_address, room_name, username, host(0:guest, 1:host)]}

    def __init__(self, server_address, server_port):
        self.server_address = server_address
        self.server_port = server_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.server_address, self.server_port))
        self.HEADER_MAX_BYTE = 32
        self.TOKEN_MAX_BYTE = 255

    def tcp_main(self):
        while True:
            try:
                self.sock.listen()
                print("サーバ待ち受け中...")
                connection, client_address = self.sock.accept()
                print("新しい接続:", client_address)

                # クライアントからのデータ受信
                data = connection.recv(4096)
                header = data[:self.HEADER_MAX_BYTE]
                room_name_size = int.from_bytes(header[:1], "big")
                operation = int.from_bytes(header[1:2], "big")
                state = int.from_bytes(header[2:3], "big")
                payload_size = int.from_bytes(header[3:self.HEADER_MAX_BYTE], "big")

                # ボディを解析
                body = data[self.HEADER_MAX_BYTE:]
                room_name = body[:room_name_size].decode("utf-8")
                payload = body[room_name_size:room_name_size + payload_size].decode("utf-8")

                # トークン生成
                token = secrets.token_bytes(self.TOKEN_MAX_BYTE)

                # 操作の処理
                if operation == 1:  # チャットルーム作成
                    self.create_room(connection, room_name, payload, token)
                elif operation == 2:  # チャットルーム参加
                    self.join_room(connection, room_name, payload, token)
                else:
                    raise ValueError("不正な操作コードです: {}".format(operation))

            except Exception as e:
                print("エラー:", str(e))
            finally:
                connection.close()

    def create_room(self, connection, room_name, username, token):
        """新しいチャットルームを作成"""
        if room_name in self.room_members_map:
            connection.send(b"Room already exists")
            return

        self.room_members_map[room_name] = [token]
        self.clients_map[token] = [None, room_name, username, 1]
        connection.send(token)
        print(f"ルーム '{room_name}' が作成されました (ホスト: {username})")

    def join_room(self, connection, room_name, username, token):
        """既存のチャットルームに参加"""
        if room_name not in self.room_members_map:
            connection.send(b"Room does not exist")
            return

        token = secrets.token_bytes(self.TOKEN_MAX_BYTE)
        self.room_members_map[room_name].append(token)
        self.clients_map[token] = [None, room_name, username, 0]  # ゲストとして追加
        connection.send(token)
        print(f"ユーザー '{username}' がルーム '{room_name}' に参加しました")

    def start(self):
        self.tcp_main()


class UDPServer:
    def __init__(self, server_address, server_port):
        self.server_address = server_address
        self.server_port = server_port
        self.room_members_map = TCPServer.room_members_map
        self.clients_map = TCPServer.clients_map
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.server_address, self.server_port))
        print("UDPサーバ起動:", self.server_port)

    def handle_message(self):
        """メッセージの受信とリレー"""
        while True:
            data, client_address = self.sock.recvfrom(4096)
            room_name_size = data[0]
            token_size = data[1]

            body = data[2:]
            room_name = body[:room_name_size].decode("utf-8")
            token = body[room_name_size:room_name_size + token_size]
            message = body[room_name_size + token_size:].decode("utf-8")

            # トークン検証
            if token not in self.clients_map:
                self.sock.sendto(b"Invalid token", client_address)
                continue

            # クライアントアドレスを更新
            if self.clients_map[token][0] != client_address:
                self.clients_map[token][0] = client_address

            username = self.clients_map[token][2]
            formatted_message = f"{username}: {message}"  # 発言者名を追加
            self.relay_message(room_name, formatted_message)

    def relay_message(self, room_name, message):
        """リレーシステム: ルーム内の全メンバーにメッセージを送信"""
        print(f"リレー: {message} (ルーム: {room_name})")
        for token in self.room_members_map.get(room_name, []):
            client_address = self.clients_map[token][0]
            if client_address:
                print(f"送信先: {client_address}")
                self.sock.sendto(message.encode(), client_address)
            else:
                print(f"トークン {token.hex()} のアドレスが登録されていません")

    def start(self):
        threading.Thread(target=self.handle_message).start()


if __name__ == "__main__":
    server_address = "127.0.0.1"
    tcp_port = 9001
    udp_port = 9002

    tcp_server = TCPServer(server_address, tcp_port)
    udp_server = UDPServer(server_address, udp_port)

    threading.Thread(target=tcp_server.start).start()
    threading.Thread(target=udp_server.start).start()
