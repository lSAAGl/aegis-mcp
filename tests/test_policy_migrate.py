import sys

import yaml

V1_SAMPLE = {
    'max_refund_cents': 15000,
    'max_payment_link_cents': 25000,
    'allow_tools': ['refunds.*', 'payment_links.create'],
    'deny_tools': []
}

V2_EXPECT_RULES = [
    {'match': 'refunds.*', 'decision': 'allow', 'cap_cents': 15000, 'ops': ['refund']},
    {'match': 'payment_links.create', 'decision': 'allow', 'cap_cents': 25000},
    {'match': '*', 'decision': 'review'}
]


def test_post_policy_migrate_returns_v2(app_client):
    client = app_client
    resp = client.post('/policy/migrate', json={'policy': V1_SAMPLE})
    assert resp.status_code == 200
    body = resp.json()
    assert body['ok'] is True
    assert body['version'] == 2
    rules = body['policy']['rules']
    # ensure first 2 rules look right and default review exists
    assert rules[0]['match'] == 'refunds.*' and rules[0]['decision'] == 'allow' and rules[0]['cap_cents'] == 15000
    assert rules[1]['match'] == 'payment_links.create' and rules[1]['decision'] == 'allow' and rules[1]['cap_cents'] == 25000
    assert any(r['match'] == '*' and r['decision'] == 'review' for r in rules)


def test_get_policy_effective_reads_env(tmp_path, monkeypatch, app_client):
    # Write a v2 policy
    p = tmp_path / 'policy.yml'
    p.write_text(yaml.safe_dump({'version': 2, 'rules': [{'match': '*', 'decision': 'review'}]}), encoding='utf-8')
    monkeypatch.setenv('POLICY_PATH', str(p))
    client = app_client
    r = client.get('/policy/effective')
    assert r.status_code == 200
    body = r.json()
    # For v2 we expect the raw v2 to be preserved by loader
    assert body.get('version') == 2
    assert isinstance(body.get('rules'), list)


def test_cli_policy_migrate_invocation(tmp_path, monkeypatch):
    # Create a v1 file and run CLI to stdout
    v1p = tmp_path / 'v1.yml'
    v1p.write_text(yaml.safe_dump(V1_SAMPLE), encoding='utf-8')
    from subprocess import check_output
    out = check_output([sys.executable, 'tools/policy_migrate.py', str(v1p)])
    data = yaml.safe_load(out.decode('utf-8'))
    assert data['version'] == 2
    assert isinstance(data['rules'], list) and len(data['rules']) >= 3