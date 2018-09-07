# This is the computer that will be controlling

import pyautogui
import time
import threading
import queue
import socket
from pynput import keyboard, mouse

pyautogui.PAUSE = 0.02

mouse_relative_mode = True

class MouseMoveListenerThread(threading.Thread):
    # doesn't do anything anymore
    def __init__(self, q):
        super().__init__()
        self.stopEvent = threading.Event()
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
        sock.connect(("192.168.0.185", 1337))

        try:
            while not self.stopSending.is_set():
                try:
                    cnt = self.queue.get(timeout=0.5)
                    sock.sendall(cnt)
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
        prefix = "kb_dn_" if direction == "down" else "kb_up_"
        if key == keyboard.Key.esc:
            print("Keyboard listener stopped")
            return False
        try:
            msg = prefix + key.char
        except AttributeError:
            msg = prefix + key.name
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
        msg = "mscr_" + str(dy)
        queue.put(bytes(msg, "utf-8"))

    return mouse_scroll

def mouse_move(queue):
    def mouse_move(x, y):
        if mouse_relative_mode:
            center = (pyautogui.size()[0]/2, pyautogui.size()[1]/2)
            msg = "msmv_" + str(x - center[0]) + "," + str(y - center[1])
        else:
            msg = "msto_" + str(x) + "," + str(y)
        queue.put(bytes(msg, "utf-8"))
        time.sleep(0.015)
        
    return mouse_move
    


def main():
    q = queue.Queue()
    #mouseMoveListener = MouseMoveListenerThread(q)
    socketThread = SocketThread(q)
    keyboardListener = keyboard.Listener(
        on_press=keyboard_event(q, "down"),
        on_release=keyboard_event(q, "up"),
        suppress=True)
    mouseListener = mouse.Listener(
        on_click=mouse_click(q),
        on_scroll=mouse_scroll(q),
        on_move=mouse_move(q),
        suppress=mouse_relative_mode)

    pyautogui.moveTo(pyautogui.size()[0]/2, pyautogui.size()[1]/2)
    #mouseMoveListener.start()
    mouseListener.start()
    socketThread.start()
    keyboardListener.start()

    keyboardListener.join()
    print("Stopping")
    #mouseMoveListener.stop()
    mouseListener.stop()
    socketThread.stop()

if __name__ == "__main__":
    main()
