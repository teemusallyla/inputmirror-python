# This is the computer whose inputs will be controlled

import socket
import pyautogui
from pynput.keyboard import Controller, Key
from pynput.mouse import Controller as MouseController
from pynput.mouse import Button

sock = socket.socket()
sock.settimeout(0.5)
with open("thispc.txt") as f:
    thisip = f.readline().rstrip()
    thisport = int(f.readline().rstrip())
sock.bind((thisip, thisport))
sock.listen()
pyautogui.PAUSE = 0
keyboard = Controller()
mouse = MouseController()

key_map = {}
for key in list(Key):
    key_map[key.name] = key

mouseButton_map = {}
for button in list(Button):
    mouseButton_map[button.name] = button

def onMouseMove(msg):
    movement_type = msg.split("_")[0]
    data = msg.split("_")[1]
    xpos = float(data.split(",")[0])
    ypos = float(data.split(",")[1])
    if movement_type == "msmv":
        pyautogui.moveRel(xpos, ypos)
    elif movement_type == "msto":
        mouse.position = xpos, ypos

def onKeyboard(msg):
    direction = msg.split("_")[1]
    key = msg.split("_")[2]
    if len(key) == 1:
        if direction == "dn":
            keyboard.press(key)
        elif direction == "up":
            keyboard.release(key)
    elif key in key_map:
        kkey = key_map[key]
        if direction == "dn":
            keyboard.press(kkey)
        elif direction == "up":
            keyboard.release(kkey)

def onMouse(msg):
    direction = msg.split("_")[1]
    button = msg.split("_")[2]
    if button in mouseButton_map:
        if direction == "dn":
            mouse.press(mouseButton_map[button])
        elif direction == "up":
            mouse.release(mouseButton_map[button])

def onScroll(msg):
    mouse.scroll(0, int(msg.split("_")[1]) * 10)


def loop():
    try:
        while True:
            conn = None
            try:
                conn, addr = sock.accept()
            except socket.timeout:
                continue
            data = conn.recv(4096)
            while data != b"":
                conn.sendall(b"ack")
                data = str(data, "utf-8")
                command = data.split("_")[0]
                
                if command in ["msmv", "msto"]:
                    onMouseMove(data)
                        
                elif command == "kb":
                    onKeyboard(data)
                            
                elif command == "ms":
                    onMouse(data)
                            
                elif command == "mscr":
                    onScroll(data)
                    
                data = conn.recv(4096)
            conn.close()
            
    except Exception as e:
        print("Exception occured:")
        print(e)
    except KeyboardInterrupt:
        print("Server closing")
    except:
        print("Unknown exception occured")
    finally:
        if conn:
            conn.sendall(b"end")
            conn.close()
            
        sock.close()
        print("Stopped")

loop()
