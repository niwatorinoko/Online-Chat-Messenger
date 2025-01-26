import socket
import threading


class TCPClient:
    def __init__(self, server_address, server_port):
        self.server_address = server_address
        self.server_port = server_port
        self.TOKEN_MAX_BYTE = 255
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_info = {}

    def protocol_header(self, room_name, operation, state, payload):
        """ヘッダーを作成"""
        room_name_size = len(room_name)
        payload_size = len(payload)
        return (
            room_name_size.to_bytes(1, "big") +
            operation.to_bytes(1, "big") +
            state.to_bytes(1, "big") +
            payload_size.to_bytes(29, "big")
        )

    def tcp_main(self):
        try:
            self.sock.connect((self.server_address, self.server_port))
            print("サーバに接続しました。")

            username = input("ユーザー名を入力してください -> ")
            operation = int(input("1: ルーム作成, 2: ルームに参加 -> "))
            room_name = input("ルーム名を入力してください -> ")

            state = 0
            header = self.protocol_header(room_name, operation, state, username)
            data = header + room_name.encode("utf-8") + username.encode("utf-8")

            self.sock.send(data)
            token = self.sock.recv(self.TOKEN_MAX_BYTE)
            self.my_info = {token: [room_name, username]}
            print("トークンを受け取りました:", token.hex())

        except Exception as e:
            print(f"エラー: {e}")
        finally:
            self.sock.close()

    def start(self):
        self.tcp_main()
        return self.my_info


class UDPClient:
    def __init__(self, server_address, server_port, my_info):
        self.server_address = server_address
        self.server_port = server_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.my_info = my_info

    def send_message(self):
        for token, info in self.my_info.items():
            room_name = info[0]
            while True:
                message = input()
                header = len(room_name).to_bytes(1, "big") + len(token).to_bytes(1, "big")
                data = header + room_name.encode("utf-8") + token + message.encode("utf-8")
                self.sock.sendto(data, (self.server_address, self.server_port))

    def receive_message(self):
        while True:
            data, _ = self.sock.recvfrom(4096)
            print(data.decode("utf-8"))

    def start(self):
        threading.Thread(target=self.send_message, daemon=True).start()
        self.receive_message()


if __name__ == "__main__":
    server_address = "127.0.0.1"
    tcp_server_port = 9001
    udp_server_port = 9002

    tcp_client = TCPClient(server_address, tcp_server_port)
    my_info = tcp_client.start()

    udp_client = UDPClient(server_address, udp_server_port, my_info)
    udp_client.start()
