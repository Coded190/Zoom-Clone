import socket
import struct
import threading

import cv2
import numpy as np
import pyaudio

SERVER_IP = "127.0.0.1"
VIDEO_PORT = 12345
AUDIO_PORT = 12346
TEXT_PORT = 12347

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 2048

video_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
audio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
text_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

video_socket.connect((SERVER_IP, VIDEO_PORT))
audio_socket.connect((SERVER_IP, AUDIO_PORT))
text_socket.connect((SERVER_IP, TEXT_PORT))


def play_stream(stream, socket):
    while True:
        data = socket.recv(CHUNK)
        stream.write(data)


p = pyaudio.PyAudio()
stream = p.open(
    format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK
)

audio_thread = threading.Thread(target=play_stream, args=(stream, audio_socket))
audio_thread.start()


def send_messages():
    while True:
        message = input("Enter message: ")
        if message:
            try:
                text_socket.sendall(message.encode("utf-8"))
            except:
                print("Error sending message")
                break


def receive_messages():
    while True:
        try:
            message = text_socket.recv(1024).decode("utf-8")
            if message:
                print(f"\nMessage: {message}\n")
        except:
            print("Error receiving message")
            break


message_send_thread = threading.Thread(target=send_messages)
message_receive_thread = threading.Thread(target=receive_messages)

message_send_thread.start()
message_receive_thread.start()

try:
    while True:
        frame_length_data = video_socket.recv(4)
        if not frame_length_data:
            break
        frame_length = struct.unpack("<L", frame_length_data)[0]

        frame_data = b""
        while len(frame_data) < frame_length:
            packet = video_socket.recv(4096)
            if not packet:
                break
            frame_data += packet

        nparr = np.frombuffer(frame_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is not None:
            cv2.imshow("Video", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
except Exception as e:
    print(f"Error: {e}")

video_socket.close()
audio_socket.close()
text_socket.close()
cv2.destroyAllWindows()
stream.stop_stream()
stream.close()
p.terminate()
