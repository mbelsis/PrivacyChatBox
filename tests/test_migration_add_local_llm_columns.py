import migration_add_local_llm_columns


class ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)


class FakeSession:
    def __init__(self):
        self.calls = []
        self.commit_count = 0
        self.rollback_count = 0
        self.closed = False

    def execute(self, statement):
        sql = str(statement)
        self.calls.append(sql)
        if "SELECT 1" in sql:
            return RowsResult([])
        if "SELECT EXISTS" in sql:
            return ScalarResult(True)
        if "SELECT column_name FROM information_schema.columns" in sql:
            return RowsResult([])
        return RowsResult([])

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1

    def close(self):
        self.closed = True


def test_run_migration_commits_for_each_missing_column(monkeypatch):
    fake_session = FakeSession()
    monkeypatch.setattr(migration_add_local_llm_columns, "init_db", lambda: True)
    monkeypatch.setattr(migration_add_local_llm_columns, "get_session", lambda: fake_session)

    migration_add_local_llm_columns.run_migration()

    assert fake_session.commit_count == 3
    assert fake_session.rollback_count == 0
    assert fake_session.closed is True
    assert any("ALTER TABLE settings ADD COLUMN local_model_context_size" in call for call in fake_session.calls)
    assert any("ALTER TABLE settings ADD COLUMN local_model_gpu_layers" in call for call in fake_session.calls)
    assert any("ALTER TABLE settings ADD COLUMN local_model_temperature" in call for call in fake_session.calls)
