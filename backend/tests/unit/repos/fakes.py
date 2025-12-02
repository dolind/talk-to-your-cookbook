class FakeResult:
    def __init__(self, *, scalar=None, scalars=None, unique_rows=None, rows=None, rowcount=None):
        self._scalar = scalar
        self._scalars = scalars or []
        self._unique = unique_rows or []
        self._rows = rows or []
        self.rowcount = rowcount if rowcount is not None else (getattr(scalar, "rowcount", None))

    # allow "await FakeResult"
    def __await__(self):
        async def _():
            return self

        return _().__await__()

    def scalar_one_or_none(self):
        return self._scalar

    def scalar(self):
        return self._scalar

    class _Scalars:
        def __init__(self, parent):
            self.parent = parent

        def all(self):
            return list(self.parent._scalars)

        def first(self):
            return self.parent._scalars[0] if self.parent._scalars else None

    def scalars(self):
        return FakeResult._Scalars(self)

    class _Unique:
        def __init__(self, parent):
            self.parent = parent

        def all(self):
            return list(self.parent._unique)

    def unique(self):
        return FakeResult._Unique(self)

    def all(self):
        return list(self._rows)


class FakeQuery:
    def __init__(self, result):
        self._result = result

    # all query-modifiers return self
    def filter(self, *a, **k):
        return self

    def where(self, *a, **k):
        return self

    def order_by(self, *a, **k):
        return self

    def offset(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    # when executed by FakeSession.execute(...)
    def __await__(self):
        async def _():
            return self._result if isinstance(self._result, FakeResult) else FakeResult()

        return _().__await__()


class FakeSession:
    def __init__(self, execute_return=None):
        self.execute_map = {}
        self.scalar_map = {}
        self.get_map = {}
        self.to_return = {}
        self.execute_returns = {}

        self.added = []
        self.deleted = []
        self.refreshed = []
        self.committed = 0
        self.flushed = 0
        self._id_counter = 1

        if execute_return:
            self.execute_returns["DEFAULT"] = execute_return

    def add(self, obj):
        self.added.append(obj)

    async def delete(self, obj):
        self.deleted.append(obj)

    async def commit(self):
        self.committed += 1

    async def refresh(self, obj):
        self.refreshed.append(obj)

    async def flush(self):
        self.flushed += 1
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = f"fake-{self._id_counter}"
                self._id_counter += 1

    async def execute(self, stmt):
        # match exact mapping
        if stmt in self.execute_map:
            result = self.execute_map[stmt]
            return result if isinstance(result, FakeResult) else FakeResult(scalars=result)

        # return default
        if "DEFAULT" in self.execute_returns:
            return self.execute_returns["DEFAULT"]

        # wrap plain statement in FakeQuery so repo can call .filter(), .order_by(), etc.
        return FakeQuery(FakeResult())

    async def scalar(self, stmt):
        return self.scalar_map.get(stmt, None)

    async def get(self, model, id_):
        return self.get_map.get(id_)
