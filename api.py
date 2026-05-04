from fastapi import FastAPI, HTTPException, Header
import socket
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware

import ast

app = FastAPI() 

RAFT_HOST = "localhost"
RAFT_PORT = 5002

API_KEY = "secret123"




def find_leader_port():
    for port in [5001, 5002, 5003]:
        try:
            response = send_command(port, "status")
            print(f"Port {port} status: {response}")
            status = parse_status_string(response)
            if status and status.get("role") == "leader":
                return port
        except:
            continue
    return 5001  # fallback

def parse_status_string(raw):
    try:
        return ast.literal_eval(raw)
    except:
        return None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    


def send_command(port: int, command: str) -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(2)
        s.connect((RAFT_HOST,port))
        s.sendall((command + "\n").encode())
        response = s.recv(4096)
        return response.decode().strip()


@app.get("/kv/{key}")
def get_key(key: str, x_api_key: str = Header(...) ):
    verify_api_key(x_api_key)
    port = find_leader_port()
    response = send_command(port, f"get {key}")
    return {"key": key, "value": response}

@app.get("/status")
def get_status(node_port: int = 5001, x_api_key: str = Header(...)):
    verify_api_key(x_api_key)
    response = send_command(node_port, "status")
    return {"status": response}


class Item(BaseModel):
    value: str

@app.post("/kv/{key}")
def post_key(key: str, item: Item,  x_api_key: str = Header(...)):
    verify_api_key(x_api_key)
    port = find_leader_port()
    response = send_command(port,f"set {key} {item.value}")
    return {"key": key, "value": item.value, "response": response}


@app.delete("/kv/{key}")
def delete_key(key: str, x_api_key: str = Header(...)):
    verify_api_key(x_api_key)
    port = find_leader_port()
    response = send_command(port,f"del {key}")
    return {"key": key, "response": response}

