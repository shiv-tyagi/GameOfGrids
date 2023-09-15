import redis_custom
import time

# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# s.connect(('127.0.0.1', 6379))
# \+([\w\d\s]*) - regex to match a simple string output
# \$\d+\\r\\n(.*) - regex to match bulk string output
# s.send(b"set a b\r\n")
# result = s.recv(1024).decode()
# s.send(b"get a\r\n")
# result = s.recv(1024).decode()
# print(result)


r = redis_custom.RedisCustom("localhost", 6379)
# r.set("a", "b")
# r.get("d")
# r.lpush("w", "8")
# print(r.rpop("w"))
# r.rpush("w", "8")
# print(r.lpop("w"))

r.subsribe("pogo", callback=print)
time.sleep(1)
r.publish("pogo", "hi")
time.sleep(1)
r.unsubscribe("pogo")
