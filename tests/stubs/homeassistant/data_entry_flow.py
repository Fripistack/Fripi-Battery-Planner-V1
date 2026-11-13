class section:
    def __init__(self, schema, options=None):
        self.schema = schema; self.options = options or {}
    def __call__(self, value):
        return self.schema(value)
