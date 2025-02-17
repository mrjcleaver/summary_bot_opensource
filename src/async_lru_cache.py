# Type: Source Code
# Description: The code snippet defines an asynchronous least recently used (LRU) cache class that stores key-value pairs. 
# The cache has a maximum size, and when the cache exceeds this size, the least recently used item is removed. 
# The class provides methods to get and set values in the cache asynchronously.

from cachetools import LRUCache

class AsyncLRUCache:
    def __init__(self, maxsize=100):
        self.cache = LRUCache(maxsize=maxsize)

    async def get(self, key):
        return self.cache.get(key)

    async def set(self, key, value):
        self.cache[key] = value
        if len(self.cache) > self.cache.maxsize:
            self.cache.popitem()
