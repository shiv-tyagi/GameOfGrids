import redis

r = redis.Redis()

r.set('a', 'b')

print(r.get('a'))

