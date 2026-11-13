
class Store:
    saved={}
    def __init__(s, hass, v, key): s.key=key
    async def async_load(s): return Store.saved.get(s.key)
    async def async_save(s, data): Store.saved[s.key]=data
    def async_delay_save(s, f, delay): Store.saved[s.key]=f()
