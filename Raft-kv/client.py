import socket
import sys


def main():
    if len(sys.argv) < 4:
        print("Usage: python3 client.py <port> <command...>")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    command = " ".join(sys.argv[3:])

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall((command + "\n").encode())
        response = s.recv(4096)
        print(response.decode(), end="")


if __name__ == "__main__":
    main()