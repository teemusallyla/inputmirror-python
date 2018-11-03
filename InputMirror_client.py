# This is the computer that will be controlling

import pyautogui
import time
import threading
import queue
import socket
from pynput import keyboard, mouse
import platform

windows = platform.system() == "Windows"
mac = platform.system() == "Darwin"
pyautogui.PAUSE = 0.02 if not mac else 0.02
partnerpc = {}
with open("connectto.txt") as f:
    partnerpc["ip"] = f.readline().rstrip()
    partnerpc["port"] = int(f.readline().rstrip())
    partnerpc["screens"] = []
    for line in [l.rstrip() for l in f.readlines()]:
        s = {"start": tuple([int(n) for n in line.split(";")[0].split("x")]),
         "size": tuple([int(n) for n in line.split(";")[1].split("x")])
         }
        partnerpc["screens"].append(s)

screen = 0
amount_of_screens = len(partnerpc["screens"])

mouse_relative_mode = True # doesn't work on macOS Mojave
suppress = True # you want to keep this at true

mouseController = mouse.Controller()

class MouseMoveListenerThread(threading.Thread):
    # doesn't do anything anymore
    def __init__(self, q):
        super().__init__()
        self.stopEvcent = threading.Event()
        self.queue = q

    def substract(self, t1, t2):
        return (t1[0] - t2[0], t1[1] - t2[1])

    def divide(self, t, d):
        return (t[0] / d, t[1] / d)

    def stop(self):
        self.stopEvent.set()

    def run(self):
        old_pos = center = self.divide(pyautogui.size(), 2)
        try:
            pyautogui.moveTo(center[0], center[1])
            while not self.stopEvent.is_set():
                pos = pyautogui.position()
                if pos != old_pos:
                    if mouse_relative_mode:
                        diff = self.substract(pos, center)
                        msg = "msmv_" + str(diff[0]) + "," + str(diff[1])
                        self.queue.put(bytes(msg, "utf-8"))
                        pyautogui.moveTo(center[0], center[1])
                        old_pos = center
                    else:
                        msg = "msto_" + str(pos[0]) + "," + str(pos[1])
                        self.queue.put(bytes(msg, "utf-8"))
                        old_pos = pos
                        time.sleep(0.02)
        except Exception as e:
            print("Following exception happened in mouse move listener:")
            print(e)
        except:
            print("Unknown exception happened in mouse move listener")

class SocketThread(threading.Thread):
    def __init__(self, queue):
        super().__init__()
        self.queue = queue
        self.stopSending = threading.Event()

    def stop(self):
        self.stopSending.set()

    def run(self):
        sock = socket.socket()
        sock.connect((partnerpc["ip"], partnerpc["port"]))

        old_msg = None

        try:
            while not self.stopSending.is_set():
                try:
                    cnt = self.queue.get(timeout=0.5)
                    if cnt == old_msg:
                        #continue
                        pass
                    sock.sendall(cnt)
                    old_msg = cnt
                    print("Sending: " + str(cnt, "utf-8"))
                    resp = sock.recv(4096)
                    if resp == b"end":
                        print("Server logged off")
                        break
                except queue.Empty:
                    pass
        except Exception as e:
            print("Exception happened in socket thread:")
            print(e)
        except:
            print("Unknown exception happened in socket thread")
        finally:
            sock.close()    

def keyboard_event(queue, direction):
    def keyboard_event(key):
        global screen
        send_key = True
        prefix = "kb_dn_" if direction == "down" else "kb_up_"
        if key == keyboard.Key.esc:
            print("Keyboard listener stopped")
            return False
        elif key == keyboard.Key.f3 and direction == "up":
            screen = screen + 1 if screen < amount_of_screens - 1 else 0
            print("screen changed: " + str(screen))
            
        if key == keyboard.Key.f3:
            send_key = False
            
        msg = None
        try:
            msg = prefix + key.char
        except AttributeError:
            msg = prefix + key.name
        except TypeError:
            pass
        if msg is not None and send_key:
            queue.put(bytes(msg, "utf-8"))

    return keyboard_event

def mouse_click(queue):
    def mouse_click(x, y, button, pressed):
        prefix = "ms_dn_" if pressed else "ms_up_"
        if button.name in ["left", "right", "middle"]:
            msg = prefix + button.name
            queue.put(bytes(msg, "utf-8"))

    return mouse_click

def mouse_scroll(queue):
    def mouse_scroll(x, y, dx, dy):
        if dy != 0:
            msg = "mscr_" + str(dy)
            queue.put(bytes(msg, "utf-8"))

    return mouse_scroll

def mouse_move(queue):
    def mouse_move(x, y):
        if mouse_relative_mode and not mac:
            center = (pyautogui.size()[0]/2, pyautogui.size()[1]/2)
            dist_x = x - center[0]
            dist_y = y - center[1]
            msg = "msmv_" + str(dist_x) + "," + str(dist_y)
        else:
            m_size = pyautogui.size()
            p_size = partnerpc["screens"][screen]["size"]
            p_start = partnerpc["screens"][screen]["start"]
            
            partner_x = p_start[0] + x / m_size[0] * p_size[0]
            partner_y = p_start[1] + y / m_size[1] * p_size[1]
            msg = "msto_" + str(partner_x) + "," + str(partner_y)
        queue.put(bytes(msg, "utf-8"))
        if windows:
            time.sleep(0.015)
        
    return mouse_move

class Keyboardlistener(keyboard.Listener):
    def __init__(self, pause_event):
        super().__init__(on_release=self.on_release, on_press=self.on_press)
        self.pause_event = pause_event


    def on_press(self, key):
        if key == keyboard.Key.esc:
            return False

    def on_release(self, key):
        global screen
        print("something pressed")
        if key == keyboard.Key.f2:
            self.pause_event.clear()
            print("pause cleared")
        elif key == keyboard.Key.f3:
            screen += 1
            if screen >= amount_of_screens:
                screen = 0
            print("screen changed")
        
        
    


def main():
    q = queue.Queue()
    pause_event = threading.Event()
    pause_event.set()
    
    socketThread = SocketThread(q)
    mainListener = Keyboardlistener(pause_event)

    socketThread.start()
    mainListener.start()

    while True:
        keyboardListener = keyboard.Listener(
            on_press=keyboard_event(q, "down"),
            on_release=keyboard_event(q, "up"),
            suppress=True)
        mouseListener = mouse.Listener(
            on_click=mouse_click(q),
            on_scroll=mouse_scroll(q),
            on_move=mouse_move(q),
            suppress=suppress)

        pyautogui.moveTo(pyautogui.size()[0]/2, pyautogui.size()[1]/2)

        mouseListener.start()
        keyboardListener.start()
        keyboardListener.join()
        print("Pausing")
        mouseListener.stop()
        while pause_event.is_set():
            if not mainListener.running:
                break
            time.sleep(0.2)
        if not mainListener.running:
            break

        pause_event.set()

    print("Stopping the whole thing")
    socketThread.stop()

if __name__ == "__main__":
    main()
