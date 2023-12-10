import socket
import struct
import threading

import cv2
import numpy as np
import pyaudio

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 2048

VIDEO_PORT = 12345
AUDIO_PORT = 12346
TEXT_PORT = 12347

video_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
audio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
text_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

video_socket.bind(("0.0.0.0", VIDEO_PORT))
audio_socket.bind(("0.0.0.0", AUDIO_PORT))
text_socket.bind(("0.0.0.0", TEXT_PORT))

video_socket.listen(1)
audio_socket.listen(1)
text_socket.listen(1)

audio = pyaudio.PyAudio()
stream = audio.open(
    format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK
)

all_clients = []


def handle_video(client_socket):
    global CAP
    CAP = cv2.VideoCapture(0)  # Capture video from the first webcam
    while CAP.isOpened():
        ret, frame = CAP.read()
        if ret:
            _, buffer = cv2.imencode(".jpg", frame)
            frame_length = struct.pack("<L", len(buffer))
            client_socket.sendall(frame_length + buffer.tobytes())
        else:
            break


def handle_audio(client_socket):
    global stream
    while True:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            client_socket.sendall(data)
        except IOError as e:
            if e.errno == pyaudio.paInputOverflowed:
                print("Input overflowed, discarding data")
            elif e.errno == pyaudio.paInternalError:
                print("Internal PyAudio error, trying to continue")
            else:
                print(f"Unhandled IOError: {e}")
        except Exception as ex:
            print(f"Unhandled exception in audio thread: {ex}")
            break


def handle_messages(client_socket):
    while True:
        try:
            message = client_socket.recv(1024).decode("utf-8")
            if message:
                print(f"Message received: {message}")
                broadcast_message(message, client_socket)
        except:
            all_clients.remove(client_socket)
            client_socket.close()
            break


def broadcast_message(message, sender_socket):
    for client in all_clients:
        if client != sender_socket:
            try:
                client.send(message.encode("utf-8"))
            except:
                client.close()
                all_clients.remove(client)


print("Server Started. Waiting for connections...")
while True:
    video_client, _ = video_socket.accept()
    audio_client, _ = audio_socket.accept()
    text_client, _ = text_socket.accept()

    all_clients.append(text_client)
    print(f"Connection established with a client.")

    threading.Thread(target=handle_video, args=(video_client,)).start()
    threading.Thread(target=handle_audio, args=(audio_client,)).start()
    threading.Thread(target=handle_messages, args=(text_client,)).start()

for client in all_clients:
    client.close()
video_socket.close()
audio_socket.close()
text_socket.close()
if CAP is not None and CAP.isOpened():
    CAP.release()
cv2.destroyAllWindows()
stream.stop_stream()
stream.close()
audio.terminate()
