#!/usr/bin/env python3
"""HAAC Framework v0.3 - synthetic execution-control laboratory.
Standard library only. No networking, production keys, or external AI calls.
Read README.md for scope and evaluation-use terms. Not a production gateway.
"""
from __future__ import annotations
import argparse
import concurrent.futures
from contextlib import closing
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import tempfile
import time

VERSION = '0.3.0'
ROOT = Path(__file__).resolve().parent
PROFILES = ('notification', 'configuration')
FILES = ('README.md', 'FRAMEWORK.md', 'CONFORMANCE.md', 'assurance.py', 'verify.py', 'PolicyKernel.lean', 'lean-toolchain', '.github/workflows/verify.yml')
FIELDS = {'schema', 'id', 'issuer', 'profile', 'target', 'resource', 'actor', 'payload', 'ruleset', 'expected_revision'}
INITIAL = dict(now=100, rule_version=1, revoked=False, approval=True, evidence=True,
               condition=True, evidence_at=100, revision=0)


def canonical(x: object) -> str:
    return json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def no_duplicates(pairs: list) -> dict:
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError('duplicate JSON key')
        result[k] = v
    return result


def load_json(text: str) -> object:
    def bad_constant(x):
        raise ValueError('non-finite JSON number')
    return json.loads(text, object_pairs_hook=no_duplicates, parse_constant=bad_constant)


def catalogue() -> list:
    text = (ROOT / 'CONFORMANCE.md').read_text(encoding='utf-8')
    start = text.index('<!-- CASES_V02_BEGIN -->')
    end = text.index('<!-- CASES_V02_END -->')
    raw = text[start:end].split('```json\n', 1)[1].rsplit('```', 1)[0]
    return load_json(raw)


def operation(profile: str) -> dict:
    return dict(schema=1, id='op-1', issuer='org-a', profile=profile,
                target='org-b' if profile == 'notification' else 'service-a',
                resource='shipment-1' if profile == 'notification' else 'config-1',
                actor='agent-a', payload='handoff-ready' if profile == 'notification' else 'enabled',
                ruleset=1, expected_revision=0)


def valid_op(op: object) -> bool:
    if not isinstance(op, dict) or set(op) != FIELDS:
        return False
    for k in ('schema', 'ruleset', 'expected_revision'):
        if type(op[k]) is not int or not 0 <= op[k] <= 10**9:
            return False
    if op['schema'] != 1 or op['profile'] not in PROFILES:
        return False
    return all(type(op[k]) is str and 0 < len(op[k]) <= 128
               and all(32 <= ord(ch) < 127 for ch in op[k])
               for k in FIELDS - {'schema', 'ruleset', 'expected_revision'})


def safe_op(op: object) -> dict:
    # Rejected unknown fields (including the synthetic secret) never enter evidence.
    return {k: v for k, v in op.items() if k in FIELDS} if isinstance(op, dict) else {}


def decision(state: dict, op: dict, mutant: str = '') -> tuple:
    missing = [k for k in ('condition', 'evidence') if state[k] is None]
    if not valid_op(op):
        return ('UNSATISFIED', 'NOT_ADOPTABLE', 'NOT_AUTHORIZED', 'INVALID_INPUT', missing)
    if op['ruleset'] != state['rule_version']:
        return ('UNSATISFIED', 'NOT_ADOPTABLE', 'NOT_AUTHORIZED', 'RULE_VERSION', missing)
    if state['condition'] is False or state['evidence'] is False:
        return ('UNSATISFIED', 'NOT_ADOPTABLE', 'NOT_AUTHORIZED', 'CONDITION_VIOLATION', missing)
    if missing:
        return ('INDETERMINATE', 'PENDING_EVIDENCE', 'REQUIRES_REVIEW', 'MISSING_EVIDENCE', missing)
    if not 0 <= state['now'] - state['evidence_at'] <= 20:
        return ('INDETERMINATE', 'PENDING_EVIDENCE', 'REQUIRES_REVIEW', 'EVIDENCE_TIME', ['evidence_freshness'])
    if state['revoked'] and mutant != 'skip_revocation':
        return ('SATISFIED', 'ADOPTABLE', 'NOT_AUTHORIZED', 'REVOKED', [])
    if not state['approval'] and mutant != 'ignore_approval':
        return ('SATISFIED', 'ADOPTABLE', 'REQUIRES_REVIEW', 'APPROVAL_REQUIRED', [])
    return ('SATISFIED', 'ADOPTABLE', 'AUTHORIZED', 'OK', [])


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), timeout=20, isolation_level=None)
    conn.execute('PRAGMA busy_timeout=20000')
    conn.execute('PRAGMA synchronous=FULL')
    return conn


def init_db(path: Path, profile: str) -> None:
    with closing(connect(path)) as db:
        db.executescript('''
        CREATE TABLE state(data TEXT NOT NULL);
        CREATE TABLE permits(id TEXT PRIMARY KEY, operation TEXT NOT NULL, start INTEGER, expiry INTEGER);
        CREATE TABLE effects(issuer TEXT NOT NULL, op_id TEXT NOT NULL, data TEXT NOT NULL,
                            PRIMARY KEY(issuer,op_id));
        CREATE TABLE cancellations(issuer TEXT NOT NULL, op_id TEXT NOT NULL, PRIMARY KEY(issuer,op_id));
        CREATE TABLE notices(issuer TEXT,op_id TEXT,target TEXT,body TEXT,PRIMARY KEY(issuer,op_id));
        CREATE TABLE settings(resource TEXT PRIMARY KEY,value TEXT NOT NULL,revision INTEGER NOT NULL);
        CREATE TABLE audit(seq INTEGER PRIMARY KEY AUTOINCREMENT,data TEXT NOT NULL);
        ''')
        db.execute('INSERT INTO state VALUES (?)', (canonical(INITIAL),))
        if profile == 'configuration':
            db.execute('INSERT INTO settings VALUES (?,?,?)', ('config-1', 'disabled', 0))


def snapshot(path: Path) -> dict:
    # Observer reads receiver-owned tables, not the controller's success label.
    with closing(connect(path)) as db:
        return dict(state=json.loads(db.execute('SELECT data FROM state').fetchone()[0]),
                    permits=[dict(id=r[0], operation=json.loads(r[1]), start=r[2], expiry=r[3])
                             for r in db.execute('SELECT * FROM permits ORDER BY id')],
                    effects=[json.loads(r[0]) for r in db.execute('SELECT data FROM effects ORDER BY issuer,op_id')],
                    cancellations=[list(r) for r in db.execute('SELECT * FROM cancellations ORDER BY issuer,op_id')],
                    notices=[list(r) for r in db.execute('SELECT * FROM notices ORDER BY issuer,op_id')],
                    settings=[list(r) for r in db.execute('SELECT * FROM settings ORDER BY resource')],
                    audit=[json.loads(r[0]) for r in db.execute('SELECT data FROM audit ORDER BY seq')])


def worker(path: Path, command: dict, mutant: str = '') -> dict:
    db = connect(path)
    try:
        db.execute('BEGIN IMMEDIATE')
        s = json.loads(db.execute('SELECT data FROM state').fetchone()[0])
        op = command.get('operation', {})
        kind = command['do']
        count = db.execute('SELECT COUNT(*) FROM effects').fetchone()[0]
        d = ('INDETERMINATE', 'PENDING_EVIDENCE', 'NOT_AUTHORIZED', 'NO_NEW_AUTHORIZATION', [])
        status = 'DENIED'
        reason = 'UNSUPPORTED'
        key = (op.get('issuer'), op.get('id'))
        prior = db.execute('SELECT data FROM effects WHERE issuer=? AND op_id=?', key).fetchone()
        cancelled = db.execute('SELECT 1 FROM cancellations WHERE issuer=? AND op_id=?', key).fetchone()
        grant = db.execute('SELECT operation,start,expiry FROM permits WHERE id=?', ('permit-1',)).fetchone()
        if kind == 'control':
            patch = command['set']
            for k, v in patch.items():
                if k not in INITIAL:
                    raise ValueError('unknown harness control')
                if k in ('condition', 'evidence'):
                    if v is not None and type(v) is not bool:
                        raise ValueError('tri-state type')
                elif type(v) is not type(INITIAL[k]):
                    raise ValueError('control type')
                if type(v) is int and not 0 <= v <= 10**9:
                    raise ValueError('control bound')
            s.update(patch)
            if 'revision' in patch:
                db.execute('UPDATE settings SET revision=?', (patch['revision'],))
            status, reason = 'UPDATED', 'HARNESS_CONTROL'
        elif kind == 'grant':
            d = decision(s, op, mutant)
            reason = d[3]
            if mutant == 'all_stop':
                reason = 'ALL_STOP_MUTATION'
            elif d[2] == 'AUTHORIZED' and not prior and not cancelled:
                db.execute('INSERT OR REPLACE INTO permits VALUES (?,?,?,?)',
                           ('permit-1', canonical(op), s['now'], s['now'] + 10))
                status = 'GRANTED'
            elif prior or cancelled:
                reason = 'TERMINAL_OPERATION'
        elif kind == 'execute':
            if not valid_op(op):
                reason = 'INVALID_INPUT'
            elif not grant:
                reason = 'NO_PERMIT'
            elif canonical(op) != grant[0]:
                reason = 'PERMIT_BINDING'
            elif prior:
                status, reason = 'REPLAYED', 'HISTORICAL_RESULT'
            elif cancelled:
                reason = 'CANCELLED'
            elif not grant[1] <= s['now'] < grant[2] and mutant != 'allow_expired':
                reason = 'PERMIT_TIME'
            elif s['revision'] != op['expected_revision']:
                reason = 'STALE_STATE'
            else:
                d = decision(s, op, mutant)
                reason = d[3]
                if d[2] == 'AUTHORIZED':
                    observed = op['payload']
                    status = 'COMPLETED'
                    if command.get('fault') == 'mismatch':
                        observed, status = 'unexpected', 'QUARANTINED'
                        if mutant == 'hide_mismatch':
                            status = 'COMPLETED'
                    if command.get('fault') == 'partial':
                        observed, status = 'partial:' + op['payload'], 'PARTIAL'
                    effect = dict(operation=op, observed_payload=observed, outcome=status,
                                  revision_before=s['revision'], revision_after=s['revision'] + 1)
                    db.execute('INSERT INTO effects VALUES (?,?,?)', (*key, canonical(effect)))
                    if op['profile'] == 'notification':
                        db.execute('INSERT INTO notices VALUES (?,?,?,?)', (*key, op['target'], observed))
                    else:
                        updated = db.execute('UPDATE settings SET value=?,revision=revision+1 WHERE resource=? AND revision=?',
                                             (observed, op['resource'], op['expected_revision']))
                        if updated.rowcount != 1:
                            raise ValueError('resource compare-and-set failed')
                    s['revision'] += 1
                    count += 1
        elif kind == 'reconcile':
            if prior:
                status, reason = json.loads(prior[0])['outcome'], 'HISTORICAL_RESULT'
            elif cancelled:
                status, reason = 'CANCELLED', 'HISTORICAL_RESULT'
            else:
                status, reason = 'UNKNOWN', 'NO_DURABLE_RECEIPT'
        elif kind == 'cancel':
            if prior:
                reason = 'ALREADY_EFFECTED'
            elif not grant or canonical(op) != grant[0]:
                reason = 'NO_MATCHING_PERMIT'
            else:
                db.execute('INSERT OR IGNORE INTO cancellations VALUES (?,?)', key)
                status, reason = 'CANCELLED', 'CANCELLATION_RECORDED'
        elif kind == 'override':
            reason = 'OVERRIDE_NOT_SUPPORTED'
        elif kind == 'switch':
            reason = 'SWITCH_NOT_SUPPORTED'
        result = dict(status=status, verification=d[0], adoption=d[1], authorization=d[2],
                      reason=reason, unverified=d[4], effect_count=count)
        event = dict(command=kind, operation=safe_op(op), result=result)
        if kind == 'control':
            event['control'] = command['set']
        db.execute('UPDATE state SET data=?', (canonical(s),))
        db.execute('INSERT INTO audit(data) VALUES (?)', (canonical(event),))
        if command.get('fault') == 'before_commit':
            # Real process termination: uncommitted effect/audit changes roll back.
            os._exit(71)
        db.execute('COMMIT')
        if command.get('fault') == 'after_commit':
            # Durable effect exists, but controller receives no reply.
            os._exit(72)
        return result
    except Exception:
        if db.in_transaction:
            db.execute('ROLLBACK')
        raise
    finally:
        db.close()


def invoke(path: Path, command: dict, mutant: str = '') -> dict:
    cmd = [sys.executable, '-I', '-S', str(ROOT / 'assurance.py'), '_worker', str(path), '--mutation', mutant]
    proc = subprocess.run(cmd, input=canonical(command), text=True, capture_output=True, timeout=30)
    if proc.returncode not in (0, 71, 72):
        raise RuntimeError('receiver failed: ' + proc.stderr[-800:])
    if proc.returncode == 0:
        reply = load_json(proc.stdout)
        return dict(returncode=0, controller_state=reply['status'], reply=reply)
    if proc.stdout:
        raise RuntimeError('crashed receiver unexpectedly returned data')
    return dict(returncode=proc.returncode, controller_state='UNKNOWN', reply=None)


def run_case(case: dict, profile: str, mutant: str = '') -> dict:
    with tempfile.TemporaryDirectory(prefix='haac-v02-') as temp:
        path = Path(temp) / 'receiver.sqlite'
        init_db(path, profile)
        attempts = []
        for step in case['steps']:
            op = operation(profile)
            op.update(copy.deepcopy(step.get('change', {})))
            cmd = {**step, 'operation': op}
            cmd.pop('change', None)
            if step['do'] == 'parallel':
                parallel = {**cmd, 'do': 'execute'}
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(lambda _: invoke(path, parallel, mutant), range(2)))
                attempts.append({'parallel': sorted(results, key=lambda x: x['reply']['status'])})
            else:
                attempts.append(invoke(path, cmd, mutant))
        observed = snapshot(path)
    return dict(id=case['id'], profile=profile, attempts=attempts, receiver=observed)


def verifier_module():
    spec = importlib.util.spec_from_file_location('haac_separate_verifier', ROOT / 'verify.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def source_digests() -> dict:
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in FILES}


def suite() -> dict:
    cases = catalogue()
    jobs = [(c, p) for p in PROFILES for c in cases]
    # Each case owns a separate temporary DB; ordering remains deterministic.
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        records = list(pool.map(lambda job: run_case(*job), jobs))
    return dict(format='haac-reference-evidence/0.2', framework=VERSION,
                scope='SYNTHETIC_SQLITE_REFERENCE_ONLY', origin='SELF_TEST',
                authentication='NOT_IMPLEMENTED', external_review='NOT_RUN',
                normative_haap_interoperability='NOT_CLAIMED',
                runtime={'python': platform.python_version(), 'platform': platform.platform(),
                         'sqlite': sqlite3.sqlite_version},
                sources=source_digests(), cases=records,
                reviews={'T18': 'NOT_RUN', 'T20': 'NOT_RUN',
                         'T22_authorized_exception': 'NOT_APPLICABLE',
                         'real_system_bypass': 'NOT_RUN', 'organizational_authority': 'NOT_RUN'})


def write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as fh:
        fh.write(data)


def run_tests(output: Path, require_lean: bool = False) -> int:
    if output.exists():
        raise ValueError('output directory already exists; choose a new path')
    bundle = suite()
    v = verifier_module()
    issues = v.validate(bundle)
    if issues:
        raise ValueError('reference validation failed: ' + '; '.join(issues[:8]))
    by_id = {c['id']: c for c in catalogue()}
    controls = [('ignore_approval', 'T05'), ('allow_expired', 'T08-equal'),
                ('skip_revocation', 'T09-after'), ('all_stop', 'T01'),
                ('hide_mismatch', 'T17-mismatch')]
    killed = []
    for mutation, cid in controls:
        for p in PROFILES:
            trial = run_case(by_id[cid], p, mutation)
            problems = v.validate_case(trial, by_id[cid])
            if not problems:
                raise ValueError('faulty control escaped: ' + mutation + '/' + p)
            killed.append(dict(mutation=mutation, case=cid, profile=p, detected=True))
    mutations = v.mutation_checks(bundle)
    raw = (json.dumps(bundle, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    sha = hashlib.sha256(raw).hexdigest()
    summary = dict(reference_cases=len(bundle['cases']), reference_case_result='PASS',
                   faulty_controls_detected=len(killed), evidence_mutations_rejected=len(mutations),
                   evidence_sha256=sha, faulty_controls=killed, evidence_mutations=mutations,
                   claims='Reference checks only; no full conformance, authentication or third-party audit.')
    policy_bundle=policy_suite()
    policy_report=policy_checks(policy_bundle)
    summary['policy_checks']=policy_report
    summary['formal']=formal_check(require_lean)
    output.mkdir(parents=True)
    policy_raw=(json.dumps(policy_bundle,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    write_new(output/'policy-evidence.json',policy_raw)
    write_new(output/'policy-evidence.sha256',(hashlib.sha256(policy_raw).hexdigest()+'\n').encode('ascii'))
    write_new(output / 'evidence.json', raw)
    write_new(output / 'evidence.sha256', (sha + '\n').encode('ascii'))
    write_new(output / 'test-report.json', (json.dumps(summary, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({k: val for k, val in summary.items() if k not in ('faulty_controls', 'evidence_mutations')}, indent=2))
    return 0


# --- Heterogeneous-policy laboratory: one assurance kernel, different rules. ---
V_SAT, V_BAD, V_UNKNOWN = 'SATISFIED', 'UNSATISFIED', 'INDETERMINATE'
CONTEXT_FIELDS = {'domain','operation','required_parties','policy_pins','policies','evidence_format',
                  'evidence','evidence_at','now','approved','active'}


def policy_catalogue() -> list[dict]:
    text = (ROOT / 'CONFORMANCE.md').read_text(encoding='utf-8')
    raw = text.split('<!-- POLICY_V03_BEGIN -->', 1)[1].split('<!-- POLICY_V03_END -->', 1)[0]
    data = load_json(raw.split('```json\n', 1)[1].rsplit('```', 1)[0])
    if data['format'] != 'haac-policy-fixtures/0.3' or len(data['cases']) != 30:
        raise ValueError('unsupported policy catalogue')
    return data['cases']


def sha_object(value: object) -> str:
    return hashlib.sha256(canonical(value).encode('ascii')).hexdigest()


def aggregate(values: list[str]) -> str:
    if not values:
        return V_UNKNOWN
    if V_BAD in values:
        return V_BAD
    return V_SAT if all(v == V_SAT for v in values) else V_UNKNOWN


def policy_authorize(values: list[str], approved: bool, active: bool, bound: bool = True) -> bool:
    return aggregate(values) == V_SAT and approved and active and bound


def checked_context(c: object) -> None:
    if type(c) is not dict or set(c) != CONTEXT_FIELDS:
        raise ValueError('policy context shape')
    if not valid_op(c['operation']) or c['domain'] not in ('coldchain','cyber'):
        raise ValueError('policy operation/domain')
    if type(c['required_parties']) is not list or len(c['required_parties']) > 16 or not all(type(x) is str and 0 < len(x) <= 64 for x in c['required_parties']):
        raise ValueError('required party list')
    if type(c['policy_pins']) is not dict or not all(type(k) is str and type(v) is str and len(v) == 64 and all(t in '0123456789abcdef' for t in v) for k,v in c['policy_pins'].items()):
        raise ValueError('policy pins')
    if type(c['policies']) is not list or len(c['policies']) > 16 or type(c['evidence']) is not dict:
        raise ValueError('policy/evidence container')
    if type(c['evidence_format']) is not str or len(c['evidence']) > 32:
        raise ValueError('evidence format/size')
    for k in ('approved','active'):
        if type(c[k]) is not bool:
            raise ValueError('authority flag type')
    for k in ('now','evidence_at'):
        if type(c[k]) is not int or not 0 <= c[k] <= 10**9:
            raise ValueError('logical time')
    for p in c['policies']:
        if type(p) is not dict or set(p) != {'party','id','version','source','interpretation','rules'}:
            raise ValueError('policy shape')
        if any(type(p[k]) is not str or not 0 < len(p[k]) <= 128 for k in ('party','id','source','interpretation')):
            raise ValueError('policy identity')
        if type(p['version']) is not int or p['version'] < 1 or type(p['rules']) is not list or len(p['rules']) > 32:
            raise ValueError('policy version/rules')


def adapted_facts(c: dict) -> tuple[dict, str]:
    if not 0 <= c['now'] - c['evidence_at'] <= 20:
        return {}, 'EVIDENCE_TIME'
    if c['evidence_format'] == 'canonical':
        return c['evidence'], ''
    if c['evidence_format'] == 'centi-C-v1' and c['domain'] == 'coldchain':
        raw = c['evidence']
        value = raw.get('temperature_centi_C')
        if set(raw) == {'temperature_centi_C'} and type(value) is int and -10**6 <= value <= 10**6:
            return {'temperature': {'value': value * 10, 'unit': 'mC'}}, ''
        return {}, 'INVALID_ADAPTER_INPUT'
    return {}, 'UNSUPPORTED_ADAPTER'


def evaluate_rule(rule: object, facts: dict, source_error: str) -> dict:
    if type(rule) is not dict or set(rule) != {'id','field','op','value','unit'} or not all(type(rule[k]) is str and 0 < len(rule[k]) <= 128 for k in ('id','field','op','unit')):
        return dict(id='INVALID_RULE', outcome=V_UNKNOWN, reason='INVALID_RULE')
    rid = rule['id']
    def answer(result: str, reason: str) -> dict:
        return dict(id=rid, outcome=result, reason=reason)
    if source_error:
        return answer(V_UNKNOWN, source_error)
    item = facts.get(rule['field'])
    if item is None:
        return answer(V_UNKNOWN, 'MISSING_EVIDENCE')
    if type(item) is not dict or set(item) != {'value','unit'} or item['unit'] != rule['unit']:
        return answer(V_UNKNOWN, 'EVIDENCE_SHAPE_OR_UNIT')
    observed, expected, op = item['value'], rule['value'], rule['op']
    if op in ('lte','gte','between'):
        if type(observed) is not int or not -10**9 <= observed <= 10**9:
            return answer(V_UNKNOWN, 'TYPE_MISMATCH')
        if op == 'between':
            if type(expected) is not list or len(expected) != 2 or not all(type(x) is int and -10**9 <= x <= 10**9 for x in expected) or expected[0] > expected[1]:
                return answer(V_UNKNOWN, 'INVALID_RULE_VALUE')
            ok = expected[0] <= observed <= expected[1]
        else:
            if type(expected) is not int or not -10**9 <= expected <= 10**9:
                return answer(V_UNKNOWN, 'INVALID_RULE_VALUE')
            ok = observed <= expected if op == 'lte' else observed >= expected
    elif op == 'eq':
        if type(observed) not in (str,bool,int) or type(observed) is not type(expected):
            return answer(V_UNKNOWN, 'TYPE_MISMATCH')
        ok = observed == expected
    elif op == 'one_of':
        if type(observed) is not str or type(expected) is not list or not expected or not all(type(x) is str for x in expected):
            return answer(V_UNKNOWN, 'TYPE_MISMATCH')
        ok = observed in expected
    else:
        return answer(V_UNKNOWN, 'UNSUPPORTED_OPERATOR')
    return answer(V_SAT if ok else V_BAD, 'MATCH' if ok else 'VIOLATION')


def assess_policies(c: dict) -> dict:
    checked_context(c)
    facts, source_error = adapted_facts(c)
    parties = c['required_parties']
    diagnostics = []
    if not parties:
        diagnostics.append('EMPTY_SCOPE')
    if len(parties) != len(set(parties)):
        diagnostics.append('DUPLICATE_REQUIRED_PARTY')
    if set(c['policy_pins']) != set(parties):
        diagnostics.append('PIN_INVENTORY_MISMATCH')
    if any(p['party'] not in parties for p in c['policies']):
        diagnostics.append('UNSCOPED_POLICY')
    records = []
    for party in sorted(set(parties)):
        candidates = [p for p in c['policies'] if p['party'] == party]
        rules, ref = [], None
        issue = ''
        if len(candidates) != 1:
            issue = 'MISSING_POLICY' if not candidates else 'DUPLICATE_POLICY'
        else:
            p = candidates[0]
            ref = {'id':p['id'],'version':p['version'],'sha256':sha_object(p)}
            if c['policy_pins'].get(party) != ref['sha256']:
                issue = 'POLICY_PIN_MISMATCH'
            elif not p['rules']:
                issue = 'EMPTY_POLICY'
            else:
                rules = [evaluate_rule(r, facts, source_error) for r in p['rules']]
                if len({r['id'] for r in rules}) != len(rules):
                    issue = 'DUPLICATE_RULE_ID'
        state = V_UNKNOWN if issue else aggregate([r['outcome'] for r in rules])
        records.append(dict(party=party,policy_ref=ref,outcome=state,rules=rules,
                            violations=[r['id'] for r in rules if r['outcome']==V_BAD],
                            unresolved=[r['id'] for r in rules if r['outcome']==V_UNKNOWN],issue=issue))
    values = [r['outcome'] for r in records] + ([V_UNKNOWN] if diagnostics else [])
    overall = aggregate(values)
    adoption = {V_SAT:'ADOPTABLE',V_BAD:'NOT_ADOPTABLE',V_UNKNOWN:'PENDING_EVIDENCE'}[overall]
    if overall == V_BAD or not c['active']:
        permission = 'NOT_AUTHORIZED'
    elif overall != V_SAT or not c['approved']:
        permission = 'REQUIRES_REVIEW'
    else:
        permission = 'AUTHORIZED'
    return dict(records=records,verification=overall,adoption=adoption,authorization=permission,diagnostics=diagnostics)


def policy_binding(c: dict) -> str:
    # Only inventory order is normalized. Event order and rule revisions are not erased.
    stable = copy.deepcopy(c)
    stable.pop('now')
    stable['required_parties'] = sorted(stable['required_parties'])
    stable['policies'] = sorted(stable['policies'], key=lambda p:(p['party'],p['id'],p['version']))
    return sha_object(stable)


def init_policy_db(path: Path, c: dict) -> None:
    checked_context(c)
    with closing(connect(path)) as db:
        db.executescript('''CREATE TABLE context(data TEXT NOT NULL);
        CREATE TABLE grant_record(data TEXT NOT NULL);
        CREATE TABLE effect_record(data TEXT NOT NULL);
        CREATE TABLE action_state(kind TEXT NOT NULL, value TEXT NOT NULL, revision INTEGER NOT NULL);
        CREATE TABLE policy_audit(seq INTEGER PRIMARY KEY AUTOINCREMENT,data TEXT NOT NULL);''')
        db.execute('INSERT INTO context VALUES (?)',(canonical(c),))
        db.execute('INSERT INTO action_state VALUES (?,?,0)',(c['operation']['profile'],'disabled' if c['operation']['profile']=='configuration' else 'EMPTY'))


def policy_worker(path: Path, cmd: dict, mutant: str = '') -> dict:
    db=connect(path)
    try:
        db.execute('BEGIN IMMEDIATE')
        current=json.loads(db.execute('SELECT data FROM context').fetchone()[0])
        kind=cmd['do']
        if kind=='change':
            checked_context(cmd['context']); current=cmd['context']
            db.execute('UPDATE context SET data=?',(canonical(current),))
        assessment=assess_policies(current)
        if mutant=='any_party':
            if any(r['outcome']==V_SAT for r in assessment['records']) and current['approved'] and current['active']:
                assessment['authorization']='AUTHORIZED'
        if mutant=='unknown_pass' and assessment['verification']==V_UNKNOWN:
            assessment['authorization']='AUTHORIZED'
        if mutant=='approval_ignored' and assessment['verification']==V_SAT and current['active']:
            assessment['authorization']='AUTHORIZED'
        if mutant=='collapse_disagreement':
            for row in assessment['records']:
                row['outcome']=assessment['verification']
        if mutant=='all_stop':
            assessment['authorization']='NOT_AUTHORIZED'
        result={'status':'DENIED','reason':'NO_PERMIT','assessment':assessment}
        raw_grant=db.execute('SELECT data FROM grant_record').fetchone()
        grant=json.loads(raw_grant[0]) if raw_grant else None
        if kind=='grant':
            if assessment['authorization']=='AUTHORIZED':
                grant=dict(binding=policy_binding(current),start=current['now'],expiry=current['now']+10,
                           operation=copy.deepcopy(current['operation']),assessment=assessment)
                db.execute('DELETE FROM grant_record');db.execute('INSERT INTO grant_record VALUES (?)',(canonical(grant),))
                result.update(status='GRANTED',reason='ALL_REQUIRED_SATISFIED')
            else:
                result['reason']='REQUIREMENTS_NOT_AUTHORIZED'
        elif kind=='change':
            result.update(status='UPDATED',reason='HARNESS_CONTROL')
        elif kind=='execute':
            previous=db.execute('SELECT data FROM effect_record').fetchone()
            if not grant:
                pass
            elif policy_binding(current)!=grant['binding'] and mutant!='ignore_binding':
                result['reason']='BINDING_CHANGED'
            elif previous:
                result.update(status='REPLAYED',reason='HISTORICAL_RESULT')
            elif not grant['start']<=current['now']<grant['expiry']:
                result['reason']='PERMIT_TIME'
            elif assessment['authorization']!='AUTHORIZED':
                result['reason']='RECHECK_NOT_AUTHORIZED'
            else:
                op=current['operation']
                changed=db.execute('UPDATE action_state SET value=?,revision=revision+1 WHERE revision=?',
                                   (op['payload'],op['expected_revision']))
                if changed.rowcount!=1:
                    raise ValueError('policy compare-and-set failed')
                effect=dict(operation=op,binding=policy_binding(current),outcome='COMPLETED',
                            observed=op['payload'],assessment=assessment)
                db.execute('INSERT INTO effect_record VALUES (?)',(canonical(effect),))
                result.update(status='COMPLETED',reason='EXECUTED')
        else:
            raise ValueError('unknown policy worker command')
        db.execute('INSERT INTO policy_audit(data) VALUES (?)',(canonical(dict(command=kind,result=result)),))
        db.execute('COMMIT')
        return result
    except Exception:
        if db.in_transaction:db.execute('ROLLBACK')
        raise
    finally:db.close()


def invoke_policy(path: Path, command: dict, mutant: str = '') -> dict:
    p=subprocess.run([sys.executable,'-I','-S',str(ROOT/'assurance.py'),'_policy_worker',str(path),'--mutation',mutant],
                     input=canonical(command),text=True,capture_output=True,timeout=30)
    if p.returncode!=0:raise RuntimeError('policy receiver failed: '+p.stderr[-500:])
    return load_json(p.stdout)


def policy_case(case: dict, mutant: str = '') -> dict:
    with tempfile.TemporaryDirectory(prefix='haac-policy-') as temp:
        path=Path(temp)/'receiver.sqlite';init_policy_db(path,case['input'])
        responses=[invoke_policy(path,{'do':'grant'},mutant)]
        if 'after_grant' in case:responses.append(invoke_policy(path,{'do':'change','context':case['after_grant']},mutant))
        responses.append(invoke_policy(path,{'do':'execute'},mutant))
        with closing(connect(path)) as db:
            observed=dict(context=json.loads(db.execute('SELECT data FROM context').fetchone()[0]),
                          grant=[json.loads(r[0]) for r in db.execute('SELECT data FROM grant_record')],
                          effects=[json.loads(r[0]) for r in db.execute('SELECT data FROM effect_record')],
                          action=list(db.execute('SELECT * FROM action_state').fetchone()),
                          audit=[json.loads(r[0]) for r in db.execute('SELECT data FROM policy_audit ORDER BY seq')])
    return dict(id=case['id'],responses=responses,receiver=observed)


def policy_suite() -> dict:
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        cases=list(pool.map(policy_case,policy_catalogue()))
    return dict(format='haac-policy-evidence/0.3',framework=VERSION,
                origin='SELF_TEST',scope='SYNTHETIC_DECLARED_POLICY_SCOPE_ONLY',
                authentication='NOT_IMPLEMENTED',external_review='NOT_RUN',
                sources=source_digests(),cases=cases)


def policy_checks(bundle: dict) -> dict:
    v=verifier_module();issues=v.validate_policy_bundle(bundle)
    if issues:raise ValueError('policy validation failed: '+ '; '.join(issues[:8]))
    cases={c['id']:c for c in policy_catalogue()}
    negative=[('any_party','P01'),('unknown_pass','P03'),('approval_ignored','P11'),
              ('ignore_binding','P18'),('collapse_disagreement','P01'),('all_stop','P02')]
    killed=[]
    for mutation,cid in negative:
        observed=policy_case(cases[cid],mutation)
        if not v.validate_policy_case(observed,cases[cid]):
            raise ValueError('policy mutation survived: '+mutation)
        killed.append(mutation)
    tampering=v.policy_mutation_checks(bundle)
    # Direct comparison of two separately implemented checkers over every abstract
    # verdict vector of length 0..4 and every approval/active/binding combination.
    import itertools
    vectors=0
    invariant_checks=0
    for n in range(5):
        for xs in itertools.product((V_SAT,V_BAD,V_UNKNOWN),repeat=n):
            # Structural obligations checked separately from differential agreement.
            expected_satisfied=bool(xs) and all(x==V_SAT for x in xs)
            if (aggregate(list(xs))==V_SAT)!=expected_satisfied:raise ValueError('all-required invariant')
            if aggregate(list(xs))!=aggregate(list(reversed(xs))):raise ValueError('order invariant')
            invariant_checks+=2
            for added in (V_SAT,V_BAD,V_UNKNOWN):
                if xs and aggregate(list(xs))!=V_SAT and aggregate(list(xs)+( [added]))==V_SAT:raise ValueError('weakened aggregation')
                invariant_checks+=1
            for flags in itertools.product((False,True),repeat=3):
                own=(aggregate(list(xs)),policy_authorize(list(xs),*flags))
                other=v.abstract_policy_result(list(xs),*flags)
                if own!=other:raise ValueError('finite kernel correspondence failed')
                vectors+=1
    # Numeric evaluators also agree over boundary and malformed values, five operators.
    agreement=0
    values=[None,True,False,-1,0,1999,2000,5000,6000,6001,7000,8000,8001,'staging','production']
    rules=[dict(id='x',field='x',op=op,value=value,unit=unit) for op,value,unit in
           [('between',[2000,8000],'mC'),('lte',6000,'mC'),('gte',2,'count'),('eq','staging','label'),('one_of',['staging','production'],'label')]]
    for r in rules:
        for value in values:
            for unit in (r['unit'],'wrong'):
                facts={} if value is None else {'x':{'value':value,'unit':unit}}
                left=evaluate_rule(r,facts,'');right=v.recheck_rule(r,facts,'')
                if left!=right:raise ValueError('rule evaluator disagreement')
                agreement+=1
    return dict(policy_cases=len(bundle['cases']),policy_negative_controls=killed,
                policy_evidence_mutations=tampering,abstract_kernel_comparisons=vectors,
                typed_rule_comparisons=agreement,finite_structural_checks=invariant_checks)


def formal_check(required: bool = False) -> dict:
    import shutil,re
    tool=shutil.which('lean')
    version=(ROOT/'lean-toolchain').read_text().strip().rsplit(':v',1)[-1]
    source=(ROOT/'PolicyKernel.lean').read_text(encoding='utf-8')
    # Reject proof holes/unsafe discharge or custom axioms in the source.
    stripped=re.sub(r'/\-.*?\-/|--[^\n]*','',source,flags=re.S)
    if re.search(r'\b(sorry|admit|axiom|native_decide|unsafe)\b',stripped):
        raise ValueError('unacceptable formal-source declaration')
    # Never trigger an Elan auto-download during the ordinary offline Python suite.
    if not required:
        return dict(status='NOT_RUN',reason='FORMAL_COMMAND_NOT_REQUESTED' if tool else 'LEAN_NOT_INSTALLED',expected_version=version)
    if not tool:
        raise ValueError('Lean '+version+' is required but unavailable')
    ver=subprocess.run([tool,'--version'],cwd=ROOT,text=True,capture_output=True,timeout=60)
    if ver.returncode or not re.search(r'\b'+re.escape(version)+r'\b',ver.stdout):
        raise ValueError('Lean version mismatch: '+ver.stdout+ver.stderr)
    proc=subprocess.run([tool,str(ROOT/'PolicyKernel.lean')],cwd=ROOT,text=True,capture_output=True,timeout=120)
    if proc.returncode or 'sorryAx' in proc.stdout+proc.stderr:
        raise ValueError('Lean kernel check failed:\n'+proc.stdout+proc.stderr)
    # Generate concrete obligations from Python; the kernel recomputes these,
    # not native_decide. No generated proof files enter the public repository.
    import itertools
    rows=[];names={V_SAT:'satisfied',V_BAD:'violated',V_UNKNOWN:'unknown'}
    for n in range(5):
        for xs in itertools.product((V_SAT,V_BAD,V_UNKNOWN),repeat=n):
            encoded_list='['+','.join(names[x] for x in xs)+']'
            rows.append('example : summary '+encoded_list+' = '+names[aggregate(list(xs))]+' := by decide')
            for f in itertools.product((False,True),repeat=3):
                args=' '.join(str(x).lower() for x in f)
                answer=str(policy_authorize(list(xs),*f)).lower()
                rows.append('example : authorize '+encoded_list+' '+args+' = '+answer+' := by decide')
    with tempfile.TemporaryDirectory(prefix='haac-formal-') as td:
        file=Path(td)/'Check.lean'
        file.write_text(source+'\nopen HAAC HAAC.Verdict\n'+'\n'.join(rows),encoding='utf-8')
        checked=subprocess.run([tool,str(file)],cwd=ROOT,text=True,capture_output=True,timeout=180)
        if checked.returncode:raise ValueError('Lean/Python concrete correspondence failed:\n'+checked.stdout+checked.stderr)
        rejected=0
        for false_claim in ['authorize [unknown] true true true = true',
                            'authorize [satisfied,violated] true true true = true',
                            'authorize [satisfied] false true true = true']:
            file.write_text(source+'\nopen HAAC HAAC.Verdict\nexample : '+false_claim+' := by decide\n',encoding='utf-8')
            bad=subprocess.run([tool,str(file)],cwd=ROOT,text=True,capture_output=True,timeout=120)
            if bad.returncode==0:raise ValueError('Lean accepted intentionally false obligation')
            rejected+=1
    return dict(status='PASS',version=ver.stdout.strip(),theorem_declarations=len(re.findall(r'^theorem ',source,re.M)),
                concrete_correspondence_obligations=len(rows),false_obligations_rejected=rejected,
                axiom_report=proc.stdout,scope='ABSTRACT_POLICY_KERNEL_NOT_WHOLE_IMPLEMENTATION')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    run = sub.add_parser('test', help='run full suite, real process faults, and negative controls')
    run.add_argument('--output', type=Path, required=True)
    run.add_argument('--require-lean',action='store_true')
    sub.add_parser('policies',help='demonstrate different safety rules with the same assurance procedure')
    sub.add_parser('formal',help='require Lean kernel checking, correspondence checks and negative proofs')
    pw=sub.add_parser('_policy_worker',help=argparse.SUPPRESS)
    pw.add_argument('database',type=Path)
    pw.add_argument('--mutation',default='')
    demo = sub.add_parser('demo', help='one declared reference scenario; no output files')
    demo.add_argument('--profile', choices=PROFILES, default='notification')
    demo.add_argument('--case', default='T14')
    sub.add_parser('cases', help='list executable reference cases')
    w = sub.add_parser('_worker', help=argparse.SUPPRESS)
    w.add_argument('database', type=Path)
    w.add_argument('--mutation', default='')
    args = parser.parse_args()
    try:
        if args.cmd=='formal':
            print(json.dumps(formal_check(True),ensure_ascii=False,indent=2));return 0
        if args.cmd=='policies':
            for case in policy_catalogue():
                if case['id'] not in ('P01','P02','P03','P10','P14','P15','P18','P25'):continue
                record=policy_case(case)
                errors=verifier_module().validate_policy_case(record,case)
                if errors:raise ValueError('; '.join(errors))
                a=record['responses'][0]['assessment'];end=record['responses'][-1]
                print(case['id']+' '+case['title'])
                print('  '+' | '.join(r['party']+': '+r['outcome'] for r in a['records']))
                print('  joint='+a['authorization']+'; execution='+end['status']+'; reason='+end['reason']+'; effects='+str(len(record['receiver']['effects'])))
            return 0
        if args.cmd=='_policy_worker':
            if args.mutation not in ('','any_party','unknown_pass','approval_ignored','ignore_binding','collapse_disagreement','all_stop'):raise ValueError('unknown policy mutation')
            if not args.database.is_file():raise ValueError('policy receiver database missing')
            text=sys.stdin.read(1_000_001)
            if len(text)>1_000_000:raise ValueError('policy input too large')
            print(canonical(policy_worker(args.database,load_json(text),args.mutation)));return 0
        if args.cmd == '_worker':
            if not args.database.is_file():
                raise ValueError('receiver database missing')
            if args.mutation not in ('', 'ignore_approval', 'allow_expired', 'skip_revocation', 'all_stop', 'hide_mismatch'):
                raise ValueError('unknown test mutation')
            text = sys.stdin.read(1_000_001)
            if len(text) > 1_000_000:
                raise ValueError('worker input too large')
            result = worker(args.database, load_json(text), args.mutation)
            print(canonical(result))
            return 0
        if args.cmd == 'cases':
            for c in catalogue():
                print(c['id'] + '\t' + c['title'])
            return 0
        if args.cmd == 'demo':
            found = next((c for c in catalogue() if c['id'] == args.case), None)
            if not found:
                raise ValueError('unknown case; use cases command')
            record = run_case(found, args.profile)
            issues = verifier_module().validate_case(record, found)
            print(json.dumps(record, ensure_ascii=False, indent=2))
            print('REFERENCE_CHECK=' + ('FAIL' if issues else 'PASS'))
            return 1 if issues else 0
        return run_tests(args.output.resolve(),args.require_lean)
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, sqlite3.Error, subprocess.TimeoutExpired) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
