from pathlib import Path
import ast
import json
import re


def test_operator_stack_contract() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    compose = (repo_root / "ops" / "docker-compose.yml").read_text(encoding="utf-8")
    prometheus = (repo_root / "ops" / "prometheus.yml").read_text(encoding="utf-8")
    datasource = (
        repo_root
        / "ops"
        / "grafana"
        / "provisioning"
        / "datasources"
        / "datasource.yml"
    ).read_text(encoding="utf-8")
    dashboard_path = repo_root / "ops" / "grafana" / "dashboards" / "marketcore-m1.json"
    ingest_main = (repo_root / "ingest" / "main.py").read_text(encoding="utf-8")

    service_names = set(re.findall(r"(?m)^  ([A-Za-z0-9_-]+):$", compose))
    assert service_names == {"timescaledb", "redis", "api", "ingest", "prometheus", "grafana"}

    api_block = _compose_block(compose, "api")
    assert _yaml_scalar(api_block, "image") == "tiangolo/uvicorn-gunicorn-fastapi:python3.12"
    assert _yaml_scalar(api_block, "command") == "uvicorn api.app:app --host 0.0.0.0 --port 8000"
    assert "pip install" not in api_block

    ingest_block = _compose_block(compose, "ingest")
    assert _yaml_scalar(ingest_block, "command") == "python -m ingest.main"

    api_job_block = _prometheus_job_block(prometheus, "api")
    assert _yaml_scalar(api_job_block, "metrics_path") == "/metrics"
    assert "api:8000" in api_job_block
    assert "ingest:8000" not in prometheus

    assert _yaml_scalar(datasource, "uid") == "marketcore-prometheus"
    assert _yaml_scalar(datasource, "type") == "prometheus"
    assert _yaml_scalar(datasource, "url") == "http://prometheus:9090"

    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    assert dashboard["title"] == "MarketCore M1"
    assert dashboard["panels"][0]["datasource"]["uid"] == "marketcore-prometheus"
    assert dashboard["panels"][0]["type"] == "text"

    ingest_tree = ast.parse(ingest_main)
    main_fn = next(
        node for node in ingest_tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    assert any(
        isinstance(node, ast.While)
        and isinstance(node.test, ast.Constant)
        and node.test.value is True
        for node in ast.walk(main_fn)
    )


def _compose_block(text: str, service_name: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(service_name)}:\n(.*?)(?=^  [A-Za-z0-9_-]+:|\Z)",
        text,
    )
    assert match is not None, service_name
    return match.group(1)


def _prometheus_job_block(text: str, job_name: str) -> str:
    match = re.search(
        rf"(?ms)^  - job_name: {re.escape(job_name)}\n(.*?)(?=^  - job_name: |\Z)",
        text,
    )
    assert match is not None, job_name
    return match.group(1)


def _yaml_scalar(block: str, key: str) -> str:
    match = re.search(rf"(?m)^\s+{re.escape(key)}:\s*(.+)$", block)
    assert match is not None, key
    return match.group(1).strip().strip('"')


def test_health_endpoint_reports_service_status() -> None:
    from fastapi.testclient import TestClient

    from api.app import create_app

    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "api",
        "healthy": False,
        "redis_connected": False,
        "published_events": 0,
    }
