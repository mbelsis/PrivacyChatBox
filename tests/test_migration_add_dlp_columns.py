import migration_add_dlp_columns


class FakeResult:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class FakeSession:
    def __init__(self):
        self.calls = []
        self.commit_called = False
        self.rollback_called = False
        self.closed = False
        self._responses = [
            FakeResult(None),
            FakeResult(None),
            FakeResult(None),
            FakeResult(None),
        ]

    def execute(self, statement):
        sql = str(statement)
        self.calls.append(sql)
        if self._responses:
            return self._responses.pop(0)
        return FakeResult(None)

    def commit(self):
        self.commit_called = True

    def rollback(self):
        self.rollback_called = True

    def close(self):
        self.closed = True


def test_run_migration_commits_changes(monkeypatch):
    fake_session = FakeSession()
    monkeypatch.setattr(migration_add_dlp_columns, "init_db", lambda: True)
    monkeypatch.setattr(migration_add_dlp_columns, "get_session", lambda: fake_session)

    migration_add_dlp_columns.run_migration()

    assert fake_session.commit_called is True
    assert fake_session.rollback_called is False
    assert fake_session.closed is True
    assert any("ALTER TABLE settings ADD COLUMN enable_ms_dlp" in call for call in fake_session.calls)
    assert any("ALTER TABLE settings ADD COLUMN ms_dlp_sensitivity_threshold" in call for call in fake_session.calls)
