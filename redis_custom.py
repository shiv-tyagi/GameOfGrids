import socket
import enum
import time
import threading
import select


'''
    to-do
    - use select.select
'''
class RedisException(Exception):
    def __init__(self, message):
        super.__init__(message)

class OpSide(enum.Enum):
    LEFT = 1
    RIGHT = 2

class RedisCustom:
    def __init__(self, host="localhost", port=6379):
        self.__sock_desc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__connected = False
        self.__subscription_info = {}
        self.__connect(host=host, port=port)

    def __del__(self):
        self.close()

    def is_connected(self):
        return self.__connected
    
    def __subscriber_thread_method(self, channel, callback):
        # create duplicate connection for listening
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(self.__sock_desc.getpeername())
        self.__subscription_info[channel] = {
            "socket_desc": sock,
            "running": True
        }
        sock.send(("SUBSCRIBE "+ channel +"\r\n").encode())
        response = sock.recv(1024).decode()
        if response.find(":1") == -1 or response.lower().find("subscribe") == -1:
            raise RedisException("Something went wrong. Could not subscribe.")

        print("Listening to channel %s" % channel)
        while self.__subscription_info[channel]["running"]:
            readables, _, _ = select.select([sock,] , [], [], 1)
            for readable in readables:
                callback(readable.recv(1024).decode().split("\r\n")[-2]) # pass the last line of the received text (i.e., the message string) to the callback method

        sock.send(("UNSUBSCRIBE "+ channel +"\r\n").encode())
        response = sock.recv(1024).decode()
        if response.find(":0") == -1 or response.lower().find("unsubscribe") == -1:
            raise RedisException("Something went wrong. Could not unsubscribe.")
        # close socket while exiting
        sock.close()
        print("Stopped listening to channel %s" % channel)

    def subsribe(self, channel, callback):
        listen_thread = threading.Thread(target=self.__subscriber_thread_method, args=(channel, callback))
        listen_thread.start()


    def unsubscribe(self, channel):
        if self.__subscription_info.get(channel, None) is None:
            print("Subscription information not found")
            return
        self.__subscription_info[channel]["running"] = False

    def __connect(self, host, port):
        if self.is_connected():
            return

        try:
            self.__sock_desc.connect((host, port))
            self.__connected = True
        except Exception as e:
            print(e)

    def close(self):
        if not self.is_connected():
            return

        try:
            self.__sock_desc.close()
            self.__connected = False
        except Exception as e:
            print(e)
        return

    def set(self, key, value):
        if not self.is_connected():
            return False

        self.__sock_desc.send(("set "+key+" '"+value+"' \r\n").encode())
        response = self.__sock_desc.recv(1024).decode()
        
        if response.find("OK"):
            return True
        
        print(response)
        return False

    def get(self, key):
        if not self.is_connected():
            print("Not connected")
            return ""

        self.__sock_desc.send(("get "+key+"\r\n").encode())
        response = self.__sock_desc.recv(1024).decode()

        header, body = response.split("\r\n", 1)
        
        if header[1:] == "-1":
            print("Not set")
            return ""

        value, _ = body.split("\r\n", 1)
        return value
    
    def __push(self, key, element, side):
        if not self.is_connected():
            return -1
        
        if side == OpSide.LEFT:
            self.__sock_desc.send(("LPUSH "+key+" '"+element+"' \r\n").encode())
        elif side == OpSide.RIGHT:
            self.__sock_desc.send(("RPUSH "+key+" '"+element+"' \r\n").encode())
        else:
            raise RedisException("Invalid operation side")

        response = self.__sock_desc.recv(1024).decode()

        if (response[0] != ":"):
            raise RedisException("Something went wrong. Could not push into the queue.")

        return response[1:].split("\r\n")[0]
    
    def __pop(self, key, side):
        if not self.is_connected():
            print("Not connected")
            return ""

        if side == OpSide.LEFT:
            self.__sock_desc.send(("lpop "+key+"\r\n").encode())
        elif side == OpSide.RIGHT:
            self.__sock_desc.send(("rpop "+key+"\r\n").encode())
        else:
            raise RedisException("Invalid operation side")
        
        response = self.__sock_desc.recv(1024).decode()

        header, body = response.split("\r\n", 1)
        
        if header[1:] == "-1":
            print("Empty queue at key %s" % key)
            return ""

        value, _ = body.split("\r\n", 1)
        return value
    
    def lpop(self, key):
        return self.__pop(key, OpSide.LEFT)
    
    def rpop(self, key):
        return self.__pop(key, OpSide.RIGHT)
    
    def lpush(self, key, element):
        return self.__push(key, element, OpSide.LEFT)
    
    def rpush(self, key, element):
        return self.__push(key, element, OpSide.RIGHT)

    def publish(self, channel, message):
        if not self.is_connected():
            return

        self.__sock_desc.send(("PUBLISH "+channel+" '"+message+"' \r\n").encode())
        response = self.__sock_desc.recv(1024).decode()
        if response.find(":") == -1:
            raise RedisException("Something strange happened.")
