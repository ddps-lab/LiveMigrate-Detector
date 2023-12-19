import redis

# Redis 서버에 연결
r = redis.StrictRedis(host='localhost', port=7777, db=0)

# 데이터 생성 (Create)
r.set('testKey', 'testValue')