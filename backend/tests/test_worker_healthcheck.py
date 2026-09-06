import os
import time

from app import worker_healthcheck


class Database:
    def __init__(self, fails=False): self.fails=fails
    def __enter__(self): return self
    def __exit__(self,*_): pass
    def execute(self,_):
        if self.fails: raise RuntimeError("database unavailable")


def test_recent_heartbeat_and_database_pass(monkeypatch,tmp_path):
    heartbeat=tmp_path/"heartbeat";heartbeat.touch()
    monkeypatch.setattr(worker_healthcheck.settings,"evaluation_worker_heartbeat_path",str(heartbeat))
    monkeypatch.setattr(worker_healthcheck,"SessionLocal",lambda:Database())
    assert worker_healthcheck.check()

def test_missing_or_stale_heartbeat_fails(monkeypatch,tmp_path):
    heartbeat=tmp_path/"heartbeat"
    monkeypatch.setattr(worker_healthcheck.settings,"evaluation_worker_heartbeat_path",str(heartbeat))
    assert not worker_healthcheck.check()
    heartbeat.touch(); old=time.time()-100;os.utime(heartbeat,(old,old))
    monkeypatch.setattr(worker_healthcheck.settings,"evaluation_worker_health_max_age_seconds",45)
    assert not worker_healthcheck.check()

def test_database_failure_fails_without_provider_call(monkeypatch,tmp_path):
    heartbeat=tmp_path/"heartbeat";heartbeat.touch()
    monkeypatch.setattr(worker_healthcheck.settings,"evaluation_worker_heartbeat_path",str(heartbeat))
    monkeypatch.setattr(worker_healthcheck,"SessionLocal",lambda:Database(fails=True))
    assert not worker_healthcheck.check()
