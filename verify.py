#!/usr/bin/env python3
"""Separate evidence checker for HAAC v0.3 policy and retained execution profiles.
Does not import assurance.py, execute the receiver, trust its PASS flags, or use SQLite.
The published fixtures are a shared specification; this is not organizational independence.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
FILES = ('README.md', 'FRAMEWORK.md', 'CONFORMANCE.md', 'assurance.py', 'verify.py', 'PolicyKernel.lean', 'lean-toolchain', '.github/workflows/verify.yml')
PROFILES = ('notification', 'configuration')


def encoded(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def strict_load(text: str):
    def unique(pairs):
        out = {}
        for key, val in pairs:
            if key in out:
                raise ValueError('duplicate JSON key: ' + key)
            out[key] = val
        return out
    def nonfinite(s):
        raise ValueError('non-finite number: ' + s)
    return json.loads(text, object_pairs_hook=unique, parse_constant=nonfinite)


def fixtures() -> list:
    contents = (ROOT / 'CONFORMANCE.md').read_text(encoding='utf-8')
    fragment = contents.split('<!-- CASES_V02_BEGIN -->', 1)[1].split('<!-- CASES_V02_END -->', 1)[0]
    rows = strict_load(fragment.split('```json\n', 1)[1].rsplit('```', 1)[0])
    if len(rows) != 41 or len({x['id'] for x in rows}) != 41:
        raise ValueError('fixture catalogue changed; version/reviewer update required')
    return rows


def base_operation(profile: str) -> dict:
    kind = {'notification': ('org-b', 'shipment-1', 'handoff-ready'),
            'configuration': ('service-a', 'config-1', 'enabled')}
    target, resource, payload = kind[profile]
    return {'schema': 1, 'id': 'op-1', 'issuer': 'org-a', 'profile': profile,
            'target': target, 'resource': resource, 'actor': 'agent-a',
            'payload': payload, 'ruleset': 1, 'expected_revision': 0}


def schema_ok(op: dict) -> bool:
    shape = base_operation('notification')
    if set(op) != set(shape):
        return False
    if any(type(op[key]) != type(sample) for key, sample in shape.items()):
        return False
    if op['schema'] != 1 or op['profile'] not in PROFILES:
        return False
    return all((0 <= x <= 10**9) if type(x) is int else
               (0 < len(x) <= 128 and x.isascii() and all(' ' <= ch <= '~' for ch in x))
               for x in op.values())


def assess(op: dict, state: dict) -> dict:
    # Declarative independent classification; no execution-side decision calls.
    unresolved = [name for name in ('condition', 'evidence') if state[name] is None]
    if not schema_ok(op):
        key = 'invalid'
    elif op['ruleset'] != state['rule_version']:
        key = 'version'
    elif False in [state[name] for name in ('condition', 'evidence') if state[name] is not None]:
        key = 'violated'
    elif unresolved:
        key = 'missing'
    elif state['now'] < state['evidence_at'] or state['now'] > state['evidence_at'] + 20:
        key, unresolved = 'stale', ['evidence_freshness']
    elif state['revoked']:
        key = 'revoked'
    elif state['approval']:
        key = 'ok'
    else:
        key = 'approval'
    table = {
        'invalid': ('UNSATISFIED', 'NOT_ADOPTABLE', 'NOT_AUTHORIZED', 'INVALID_INPUT'),
        'version': ('UNSATISFIED', 'NOT_ADOPTABLE', 'NOT_AUTHORIZED', 'RULE_VERSION'),
        'violated': ('UNSATISFIED', 'NOT_ADOPTABLE', 'NOT_AUTHORIZED', 'CONDITION_VIOLATION'),
        'missing': ('INDETERMINATE', 'PENDING_EVIDENCE', 'REQUIRES_REVIEW', 'MISSING_EVIDENCE'),
        'stale': ('INDETERMINATE', 'PENDING_EVIDENCE', 'REQUIRES_REVIEW', 'EVIDENCE_TIME'),
        'revoked': ('SATISFIED', 'ADOPTABLE', 'NOT_AUTHORIZED', 'REVOKED'),
        'approval': ('SATISFIED', 'ADOPTABLE', 'REQUIRES_REVIEW', 'APPROVAL_REQUIRED'),
        'ok': ('SATISFIED', 'ADOPTABLE', 'AUTHORIZED', 'OK')}
    v, a, p, reason = table[key]
    return dict(verification=v, adoption=a, authorization=p, reason=reason, unverified=unresolved)


def initial_model(profile: str) -> dict:
    return {'state': {'now': 100, 'rule_version': 1, 'revoked': False, 'approval': True,
                      'evidence': True, 'condition': True, 'evidence_at': 100, 'revision': 0},
            'permits': [], 'effects': [], 'cancellations': [], 'notices': [],
            'settings': [['config-1', 'disabled', 0]] if profile == 'configuration' else [], 'audit': []}


def transition(model: dict, op: dict, step: dict) -> dict:
    s = model['state']
    kind = step['do']
    row = {'status': 'DENIED', 'verification': 'INDETERMINATE', 'adoption': 'PENDING_EVIDENCE',
           'authorization': 'NOT_AUTHORIZED', 'reason': 'UNSUPPORTED', 'unverified': [],
           'effect_count': len(model['effects'])}
    identity = [op.get('issuer'), op.get('id')]
    past = next((x for x in model['effects'] if [x['operation']['issuer'], x['operation']['id']] == identity), None)
    canceled = identity in model['cancellations']
    permit = model['permits'][0] if model['permits'] else None
    if kind == 'control':
        s.update(step['set'])
        if 'revision' in step['set'] and model['settings']:
            model['settings'][0][2] = step['set']['revision']
        row.update(status='UPDATED', reason='HARNESS_CONTROL')
    elif kind == 'grant':
        row.update(assess(op, s))
        if past or canceled:
            row['reason'] = 'TERMINAL_OPERATION'
        elif row['authorization'] == 'AUTHORIZED':
            model['permits'] = [dict(id='permit-1', operation=copy.deepcopy(op), start=s['now'], expiry=s['now'] + 10)]
            row['status'] = 'GRANTED'
    elif kind == 'execute':
        if not schema_ok(op):
            row['reason'] = 'INVALID_INPUT'
        elif permit is None:
            row['reason'] = 'NO_PERMIT'
        elif encoded(permit['operation']) != encoded(op):
            row['reason'] = 'PERMIT_BINDING'
        elif past is not None:
            row.update(status='REPLAYED', reason='HISTORICAL_RESULT')
        elif canceled:
            row['reason'] = 'CANCELLED'
        elif s['now'] < permit['start'] or s['now'] >= permit['expiry']:
            row['reason'] = 'PERMIT_TIME'
        elif op['expected_revision'] != s['revision']:
            row['reason'] = 'STALE_STATE'
        else:
            row.update(assess(op, s))
            if row['authorization'] == 'AUTHORIZED':
                variant = step.get('fault')
                if variant == 'mismatch':
                    payload, result = 'unexpected', 'QUARANTINED'
                elif variant == 'partial':
                    payload, result = 'partial:' + op['payload'], 'PARTIAL'
                else:
                    payload, result = op['payload'], 'COMPLETED'
                old = s['revision']
                model['effects'].append({'operation': copy.deepcopy(op), 'observed_payload': payload,
                                         'outcome': result, 'revision_before': old, 'revision_after': old + 1})
                if op['profile'] == 'notification':
                    model['notices'].append([op['issuer'], op['id'], op['target'], payload])
                else:
                    model['settings'] = [[op['resource'], payload, old + 1]]
                s['revision'] += 1
                row.update(status=result, effect_count=len(model['effects']))
    elif kind == 'reconcile':
        row['status'] = past['outcome'] if past else ('CANCELLED' if canceled else 'UNKNOWN')
        row['reason'] = 'HISTORICAL_RESULT' if (past or canceled) else 'NO_DURABLE_RECEIPT'
    elif kind == 'cancel':
        if past:
            row['reason'] = 'ALREADY_EFFECTED'
        elif permit is None or encoded(op) != encoded(permit['operation']):
            row['reason'] = 'NO_MATCHING_PERMIT'
        else:
            if not canceled:
                model['cancellations'].append(identity)
            row.update(status='CANCELLED', reason='CANCELLATION_RECORDED')
    elif kind == 'override':
        row['reason'] = 'OVERRIDE_NOT_SUPPORTED'
    elif kind == 'switch':
        row['reason'] = 'SWITCH_NOT_SUPPORTED'
    event = {'command': kind, 'operation': {k: v for k, v in op.items() if k in base_operation('notification')},
             'result': copy.deepcopy(row)}
    if kind == 'control':
        event['control'] = copy.deepcopy(step['set'])
    model['audit'].append(event)
    return row


def expected_case(case: dict, profile: str) -> dict:
    model = initial_model(profile)
    attempts = []
    def one(step):
        nonlocal model
        before = copy.deepcopy(model)
        op = base_operation(profile)
        op.update(copy.deepcopy(step.get('change', {})))
        reply = transition(model, op, step)
        fault = step.get('fault')
        if fault == 'before_commit':
            model = before
            return dict(returncode=71, controller_state='UNKNOWN', reply=None)
        if fault == 'after_commit':
            return dict(returncode=72, controller_state='UNKNOWN', reply=None)
        return dict(returncode=0, controller_state=reply['status'], reply=reply)
    for step in case['steps']:
        if step['do'] == 'parallel':
            answers = [one({'do': 'execute'}), one({'do': 'execute'})]
            attempts.append({'parallel': sorted(answers, key=lambda x: x['reply']['status'])})
        else:
            attempts.append(one(step))
    return {'id': case['id'], 'profile': profile, 'attempts': attempts, 'receiver': model}


def first_difference(a, b, path='record') -> str:
    if type(a) != type(b):
        return path + ': type mismatch'
    if isinstance(a, dict):
        if set(a) != set(b):
            return path + ': field set differs'
        for key in a:
            msg = first_difference(a[key], b[key], path + '.' + key)
            if msg:
                return msg
    elif isinstance(a, list):
        if len(a) != len(b):
            return path + ': length differs'
        for i, (left, right) in enumerate(zip(a, b)):
            msg = first_difference(left, right, path + '[' + str(i) + ']')
            if msg:
                return msg
    elif a != b:
        return path + ': value differs'
    return ''


def validate_case(actual: dict, fixture: dict) -> list[str]:
    try:
        profile = actual['profile']
        if profile not in PROFILES:
            return ['unknown profile']
        expected = expected_case(fixture, profile)
        # The manually declared acceptance values also check the independent model.
        last = expected['attempts'][-1]
        last_status = last['parallel'][-1]['reply']['status'] if 'parallel' in last else last['reply']['status']
        if len(expected['receiver']['effects']) != fixture['expected']['effects'] or last_status != fixture['expected']['status']:
            return ['specification/oracle disagreement: ' + fixture['id']]
        difference = first_difference(actual, expected)
        return [difference] if difference else []
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        return ['invalid reference record: ' + str(exc)]


def validate(bundle: dict) -> list[str]:
    issues = []
    try:
        shape = {'format', 'framework', 'scope', 'origin', 'authentication', 'external_review',
                 'normative_haap_interoperability', 'runtime', 'sources', 'cases', 'reviews'}
        if type(bundle) is not dict or set(bundle) != shape:
            return ['evidence envelope field set differs']
        constants = {'format': 'haac-reference-evidence/0.2', 'framework': '0.3.0',
                     'scope': 'SYNTHETIC_SQLITE_REFERENCE_ONLY', 'origin': 'SELF_TEST',
                     'authentication': 'NOT_IMPLEMENTED', 'external_review': 'NOT_RUN',
                     'normative_haap_interoperability': 'NOT_CLAIMED'}
        for k, value in constants.items():
            if bundle[k] != value:
                issues.append('invalid claim: ' + k)
        if type(bundle['runtime']) is not dict or set(bundle['runtime']) != {'python', 'platform', 'sqlite'} or not all(type(x) is str and x for x in bundle['runtime'].values()):
            issues.append('runtime metadata malformed')
        wanted_reviews = {'T18': 'NOT_RUN', 'T20': 'NOT_RUN', 'T22_authorized_exception': 'NOT_APPLICABLE',
                          'real_system_bypass': 'NOT_RUN', 'organizational_authority': 'NOT_RUN'}
        if encoded(bundle['reviews']) != encoded(wanted_reviews):
            issues.append('unsupported review claim')
        local = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in FILES}
        if bundle['sources'] != local:
            issues.append('source/version mismatch; use the same reviewed release')
        specs = {x['id']: x for x in fixtures()}
        wanted = {(p, cid) for p in PROFILES for cid in specs}
        seen = set()
        if type(bundle['cases']) is not list:
            return issues + ['cases must be an array']
        for record in bundle['cases']:
            if type(record) is not dict or type(record.get('profile')) is not str or type(record.get('id')) is not str:
                issues.append('case identity must be an object with string profile and id')
                continue
            key = (record.get('profile'), record.get('id'))
            if key in seen or key not in wanted:
                issues.append('duplicate or unknown case: ' + str(key))
                continue
            seen.add(key)
            issues.extend(str(key) + ': ' + text for text in validate_case(record, specs[key[1]]))
        if seen != wanted:
            issues.append('case coverage mismatch')
    except (KeyError, TypeError, ValueError, IndexError, OSError) as exc:
        issues.append('malformed evidence: ' + str(exc))
    return issues


def mutation_checks(clean: dict) -> list[str]:
    trials = []
    def check(name, alter):
        bad = copy.deepcopy(clean)
        alter(bad)
        if not validate(bad):
            raise ValueError('verifier missed evidence mutation: ' + name)
        trials.append(name)
    check('missing-case', lambda b: b['cases'].pop())
    check('duplicate-case', lambda b: b['cases'].append(copy.deepcopy(b['cases'][0])))
    check('unknown-case', lambda b: b['cases'][0].update(id='T99'))
    check('unknown-profile', lambda b: b['cases'][0].update(profile='medical'))
    check('forged-success', lambda b: b['cases'][0]['attempts'][1]['reply'].update(status='DENIED'))
    check('modified-receiver-effect', lambda b: b['cases'][0]['receiver']['effects'][0].update(observed_payload='tampered'))
    check('removed-audit-tail', lambda b: b['cases'][0]['receiver']['audit'].pop())
    check('boolean-effect-count', lambda b: b['cases'][0]['attempts'][1]['reply'].update(effect_count=True))
    check('invented-authentication', lambda b: b.update(authentication='VERIFIED'))
    check('invented-third-party-review', lambda b: b.update(external_review='PASS'))
    check('different-code', lambda b: b['sources'].update({'assurance.py': '0' * 64}))
    check('unknown-envelope-version', lambda b: b.update(framework='1.0'))
    check('changed-profile-effect', lambda b: b['cases'][41]['receiver']['settings'][0].__setitem__(1, 'wrong'))
    check('unsupported-review-pass', lambda b: b['reviews'].update(T18='PASS'))
    check('non-object-case', lambda b: b['cases'].__setitem__(0, []))
    check('non-string-profile', lambda b: b['cases'][0].update(profile=[]))
    check('non-object-runtime', lambda b: b.update(runtime=[]))
    check('non-array-cases', lambda b: b.update(cases=1))
    for label, raw in [('duplicate-json-key', '{"a":1,"a":2}'), ('nan', '{"a":NaN}'), ('infinity', '{"a":Infinity}')]:
        try:
            strict_load(raw)
        except ValueError:
            trials.append(label)
        else:
            raise ValueError('unsafe JSON accepted')
    return trials


# --- Independent policy semantics. Never imports the execution program. ---
POLICY_STATES=('SATISFIED','UNSATISFIED','INDETERMINATE')


def policy_fixtures() -> list[dict]:
    txt=(ROOT/'CONFORMANCE.md').read_text(encoding='utf-8')
    cut=txt.split('<!-- POLICY_V03_BEGIN -->',1)[1].split('<!-- POLICY_V03_END -->',1)[0]
    spec=strict_load(cut.split('```json\n',1)[1].rsplit('```',1)[0])
    if spec['format']!='haac-policy-fixtures/0.3' or len(spec['cases'])!=30 or len({c['id'] for c in spec['cases']})!=30:
        raise ValueError('policy fixtures/version mismatch')
    return spec['cases']


def summarize_policy(results: list[str]) -> str:
    # Rank of logical information, not policy preference or a safety score.
    if len(results)==0:return 'INDETERMINATE'
    has_no=any(x=='UNSATISFIED' for x in results)
    all_yes=all(x=='SATISFIED' for x in results)
    return 'UNSATISFIED' if has_no else ('SATISFIED' if all_yes else 'INDETERMINATE')


def abstract_policy_result(values: list[str],approval: bool,active: bool,bound: bool) -> tuple:
    state=summarize_policy(values)
    permitted=(len(values)>0 and all(x=='SATISFIED' for x in values) and
               (approval,active,bound)==(True,True,True))
    return state,permitted


def policy_hash(value: object) -> str:
    return hashlib.sha256(encoded(value).encode('ascii')).hexdigest()


def recheck_rule(rule: object,facts: dict,source_error: str) -> dict:
    required={'id','field','op','value','unit'}
    valid=type(rule) is dict and set(rule)==required
    if valid:valid=all(type(rule[x]) is str and 0<len(rule[x])<=128 for x in ['id','field','op','unit'])
    if not valid:return {'id':'INVALID_RULE','outcome':'INDETERMINATE','reason':'INVALID_RULE'}
    state,why='INDETERMINATE',source_error
    if not why:
        item=facts.get(rule['field'])
        if item is None:why='MISSING_EVIDENCE'
        elif type(item) is not dict or set(item)!={'value','unit'} or item['unit']!=rule['unit']:
            why='EVIDENCE_SHAPE_OR_UNIT'
        else:
            value,criterion,operator=item['value'],rule['value'],rule['op']
            integer=lambda a: type(a) is int and -10**9<=a<=10**9
            if operator in {'lte','gte','between'}:
                if not integer(value):why='TYPE_MISMATCH'
                elif operator=='between':
                    if type(criterion) is not list or len(criterion)!=2 or not all(integer(x) for x in criterion) or criterion[1]<criterion[0]:
                        why='INVALID_RULE_VALUE'
                    else:state='SATISFIED' if value>=criterion[0] and value<=criterion[1] else 'UNSATISFIED'
                elif not integer(criterion):why='INVALID_RULE_VALUE'
                else:
                    checks={'lte':lambda: not value>criterion,'gte':lambda: not value<criterion}
                    state='SATISFIED' if checks[operator]() else 'UNSATISFIED'
            elif operator=='eq':
                if type(value) not in {bool,int,str} or type(value)!=type(criterion):why='TYPE_MISMATCH'
                else:state='SATISFIED' if value==criterion else 'UNSATISFIED'
            elif operator=='one_of':
                if type(value)!=str or type(criterion)!=list or len(criterion)==0 or any(type(x)!=str for x in criterion):why='TYPE_MISMATCH'
                else:state='SATISFIED' if any(value==x for x in criterion) else 'UNSATISFIED'
            else:why='UNSUPPORTED_OPERATOR'
    if not why:why={'SATISFIED':'MATCH','UNSATISFIED':'VIOLATION'}[state]
    return {'id':rule['id'],'outcome':state,'reason':why}


def policy_assessment(c: dict) -> dict:
    # Input validity is checked independently and bounded before interpretation.
    shape={'domain','operation','required_parties','policy_pins','policies','evidence_format',
           'evidence','evidence_at','now','approved','active'}
    if type(c)!=dict or set(c)!=shape or c['domain'] not in {'coldchain','cyber'} or not schema_ok(c['operation']):
        raise ValueError('policy context schema')
    required=c['required_parties'];pins=c['policy_pins'];policies=c['policies']
    if type(required)!=list or len(required)>16 or any(type(x)!=str or not 0<len(x)<=64 for x in required):raise ValueError('policy required ids')
    if type(pins)!=dict or any(type(k)!=str or type(v)!=str or len(v)!=64 or any(ch not in '0123456789abcdef' for ch in v) for k,v in pins.items()):raise ValueError('policy pins')
    if type(policies)!=list or len(policies)>16 or type(c['evidence'])!=dict or len(c['evidence'])>32 or type(c['evidence_format'])!=str:raise ValueError('policy collection')
    if any(type(c[k])!=bool for k in ['approved','active']) or any(type(c[k])!=int or not 0<=c[k]<=10**9 for k in ['now','evidence_at']):raise ValueError('policy authority/time')
    for policy in policies:
        if type(policy)!=dict or set(policy)!={'party','id','version','source','interpretation','rules'}:raise ValueError('policy definition shape')
        if any(type(policy[k])!=str or not 0<len(policy[k])<=128 for k in ['party','id','source','interpretation']):raise ValueError('policy id')
        if type(policy['version'])!=int or policy['version']<1 or type(policy['rules'])!=list or len(policy['rules'])>32:raise ValueError('policy rules')
    error='';facts={}
    if c['now']<c['evidence_at'] or c['now']>c['evidence_at']+20:error='EVIDENCE_TIME'
    elif c['evidence_format']=='canonical':facts=c['evidence']
    elif c['evidence_format']=='centi-C-v1' and c['domain']=='coldchain':
        raw=c['evidence'];x=raw.get('temperature_centi_C')
        if set(raw)=={'temperature_centi_C'} and type(x)==int and -10**6<=x<=10**6:
            facts={'temperature':dict(value=x*10,unit='mC')}
        else:error='INVALID_ADAPTER_INPUT'
    else:error='UNSUPPORTED_ADAPTER'
    diagnostics=[]
    if len(required)==0:diagnostics.append('EMPTY_SCOPE')
    if len(set(required))!=len(required):diagnostics.append('DUPLICATE_REQUIRED_PARTY')
    if set(required)!=set(pins):diagnostics.append('PIN_INVENTORY_MISMATCH')
    if any(x['party'] not in required for x in policies):diagnostics.append('UNSCOPED_POLICY')
    records=[]
    for party in sorted(set(required)):
        matches=[x for x in policies if x['party']==party]
        ref=None;results=[];issue=''
        if not matches:issue='MISSING_POLICY'
        elif len(matches)>1:issue='DUPLICATE_POLICY'
        else:
            p=matches[0];ref=dict(id=p['id'],version=p['version'],sha256=policy_hash(p))
            if pins.get(party)!=ref['sha256']:issue='POLICY_PIN_MISMATCH'
            elif len(p['rules'])==0:issue='EMPTY_POLICY'
            else:
                results=[recheck_rule(r,facts,error) for r in p['rules']]
                if len(set(x['id'] for x in results))<len(results):issue='DUPLICATE_RULE_ID'
        state='INDETERMINATE' if issue else summarize_policy([x['outcome'] for x in results])
        records.append({'party':party,'policy_ref':ref,'outcome':state,'rules':results,
                        'violations':[x['id'] for x in results if x['outcome']=='UNSATISFIED'],
                        'unresolved':[x['id'] for x in results if x['outcome']=='INDETERMINATE'],'issue':issue})
    values=[x['outcome'] for x in records]
    if diagnostics:values.append('INDETERMINATE')
    overall=summarize_policy(values)
    choice={'SATISFIED':'ADOPTABLE','UNSATISFIED':'NOT_ADOPTABLE','INDETERMINATE':'PENDING_EVIDENCE'}[overall]
    permission=('NOT_AUTHORIZED' if (overall=='UNSATISFIED' or c['active'] is False) else
                ('AUTHORIZED' if overall=='SATISFIED' and c['approved'] is True else 'REQUIRES_REVIEW'))
    return {'records':records,'verification':overall,'adoption':choice,'authorization':permission,'diagnostics':diagnostics}


def scope_digest(c: dict) -> str:
    body={key:copy.deepcopy(value) for key,value in c.items() if key!='now'}
    body['required_parties']=sorted(body['required_parties'])
    body['policies']=sorted(body['policies'],key=lambda x:(x['party'],x['id'],x['version']))
    return policy_hash(body)


def expected_policy_case(case: dict) -> dict:
    first=case['input'];assessment=policy_assessment(first);grant=[];responses=[];audit=[]
    def record(command,result):
        responses.append(copy.deepcopy(result));audit.append(dict(command=command,result=copy.deepcopy(result)))
    row=dict(status='DENIED',reason='REQUIREMENTS_NOT_AUTHORIZED',assessment=assessment)
    if assessment['authorization']=='AUTHORIZED':
        grant=[dict(binding=scope_digest(first),start=first['now'],expiry=first['now']+10,
                    operation=copy.deepcopy(first['operation']),assessment=copy.deepcopy(assessment))]
        row.update(status='GRANTED',reason='ALL_REQUIRED_SATISFIED')
    record('grant',row)
    current=case.get('after_grant',first)
    final=policy_assessment(current)
    if 'after_grant' in case:record('change',dict(status='UPDATED',reason='HARNESS_CONTROL',assessment=final))
    result=dict(status='DENIED',reason='NO_PERMIT',assessment=final)
    effects=[];kind=first['operation']['profile'];action=[kind,'disabled' if kind=='configuration' else 'EMPTY',0]
    if grant:
        permitted=grant[0]
        if scope_digest(current)!=permitted['binding']:result['reason']='BINDING_CHANGED'
        elif current['now']<permitted['start'] or current['now']>=permitted['expiry']:result['reason']='PERMIT_TIME'
        elif final['authorization']!='AUTHORIZED':result['reason']='RECHECK_NOT_AUTHORIZED'
        else:
            op=copy.deepcopy(current['operation'])
            if op['expected_revision']!=0:raise ValueError('unsupported policy initial revision')
            effects=[dict(operation=op,binding=scope_digest(current),outcome='COMPLETED',observed=op['payload'],assessment=final)]
            action=[kind,op['payload'],1];result.update(status='COMPLETED',reason='EXECUTED')
    record('execute',result)
    return dict(id=case['id'],responses=responses,
                receiver=dict(context=copy.deepcopy(current),grant=grant,effects=effects,action=action,audit=audit))


def validate_policy_case(actual: object,fixture: dict) -> list[str]:
    try:
        model=expected_policy_case(fixture)
        start=model['responses'][0]['assessment'];last=model['responses'][-1];expected=fixture['expected']
        manual=dict(local={r['party']:r['outcome'] for r in start['records']},verification=start['verification'],
                    authorization=start['authorization'],status=last['status'],effects=len(model['receiver']['effects']))
        if 'reason' in expected:manual['reason']=last['reason']
        problem=first_difference(manual,expected,'fixture_expectations')
        if problem:return [problem]
        difference=first_difference(actual,model,'policy_record')
        return [difference] if difference else []
    except (KeyError,TypeError,ValueError,IndexError):
        return ['invalid policy record/specification']


def validate_policy_bundle(bundle: object) -> list[str]:
    try:
        shape={'format','framework','origin','scope','authentication','external_review','sources','cases'}
        if type(bundle)!=dict or set(bundle)!=shape:return ['policy envelope shape']
        constants={'format':'haac-policy-evidence/0.3','framework':'0.3.0','origin':'SELF_TEST',
                   'scope':'SYNTHETIC_DECLARED_POLICY_SCOPE_ONLY','authentication':'NOT_IMPLEMENTED','external_review':'NOT_RUN'}
        problems=['invalid policy claim: '+k for k,v in constants.items() if bundle[k]!=v]
        local={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in FILES}
        if bundle['sources']!=local:problems.append('policy source/version mismatch')
        if type(bundle['cases'])!=list:return problems+['policy cases array']
        catalog={c['id']:c for c in policy_fixtures()};seen=set()
        for row in bundle['cases']:
            if type(row)!=dict or type(row.get('id'))!=str or row['id'] not in catalog or row['id'] in seen:
                problems.append('invalid/duplicate policy case');continue
            seen.add(row['id']);problems.extend(row['id']+': '+x for x in validate_policy_case(row,catalog[row['id']]))
        if seen!=set(catalog):problems.append('policy case coverage mismatch')
        return problems
    except (KeyError,TypeError,ValueError,IndexError,OSError):return ['malformed policy evidence']


def policy_mutation_checks(clean: dict) -> list[str]:
    detected=[]
    def trial(name,change):
        bad=copy.deepcopy(clean);change(bad)
        if not validate_policy_bundle(bad):raise ValueError('missed policy evidence mutation: '+name)
        detected.append(name)
    trial('missing-case',lambda b:b['cases'].pop())
    trial('duplicate-case',lambda b:b['cases'].append(copy.deepcopy(b['cases'][0])))
    trial('forged-joint-permission',lambda b:b['cases'][0]['responses'][0]['assessment'].update(authorization='AUTHORIZED'))
    trial('erase-party-difference',lambda b:b['cases'][0]['responses'][0]['assessment']['records'][1].update(outcome='SATISFIED'))
    trial('remove-required-party-result',lambda b:b['cases'][0]['responses'][0]['assessment']['records'].pop())
    trial('invent-execution',lambda b:b['cases'][0]['responses'][-1].update(status='COMPLETED'))
    trial('change-observed-effect',lambda b:b['cases'][1]['receiver']['effects'][0].update(observed='wrong'))
    trial('change-scope-in-retained-input',lambda b:b['cases'][1]['receiver']['context'].update(required_parties=['A']))
    trial('wrong-policy-pin',lambda b:b['cases'][1]['receiver']['context']['policy_pins'].update(B='0'*64))
    trial('remove-unresolved-condition',lambda b:b['cases'][12]['responses'][0]['assessment']['records'][1]['unresolved'].clear())
    trial('forged-formal-certification',lambda b:b.update(formal='PROVEN_SAFE'))
    trial('forged-external-review',lambda b:b.update(external_review='PASS'))
    trial('different-policy-code',lambda b:b['sources'].update({'assurance.py':'0'*64}))
    trial('boolean-revision',lambda b:b['cases'][1]['receiver']['action'].__setitem__(2,True))
    trial('changed-grant-binding',lambda b:b['cases'][1]['receiver']['grant'][0].update(binding='0'*64))
    trial('removed-policy-audit-tail',lambda b:b['cases'][1]['receiver']['audit'].pop())
    trial('empty-policy-record',lambda b:b['cases'].__setitem__(0,{}))
    trial('non-array-policy-cases',lambda b:b.update(cases=1))
    return detected


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('evidence', type=Path)
    anchors = ap.add_mutually_exclusive_group()
    anchors.add_argument('--sha256', help='digest retained independently of the evidence')
    anchors.add_argument('--sha256-file', type=Path, help='local baseline only unless obtained through a trusted separate channel')
    ap.add_argument('--mutations', action='store_true', help='also test evidence mutations against this valid bundle')
    args = ap.parse_args()
    try:
        if args.evidence.stat().st_size > 32 * 1024 * 1024:
            raise ValueError('evidence exceeds 32 MiB limit')
        raw = args.evidence.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        wanted = args.sha256
        if args.sha256_file:
            wanted = args.sha256_file.read_text(encoding='ascii').strip()
        if wanted is not None:
            if len(wanted) != 64 or any(ch not in '0123456789abcdef' for ch in wanted):
                raise ValueError('expected lowercase SHA-256 hex')
            if wanted != digest:
                print(json.dumps({'result': 'INVALID', 'errors': ['EVIDENCE_DIGEST_MISMATCH']}))
                return 1
        bundle = strict_load(raw.decode('utf-8'))
        is_policy=type(bundle) is dict and bundle.get("format")=="haac-policy-evidence/0.3"
        issues = validate_policy_bundle(bundle) if is_policy else validate(bundle)
        result = {'result': 'INVALID' if issues else ('CONSISTENT_REFERENCE' if wanted else 'CONSISTENT_UNANCHORED'),
                  'cases_checked': len(bundle['cases']) if type(bundle) is dict and type(bundle.get('cases')) is list else 0,
                  'integrity_basis': 'CALLER_SUPPLIED_DIGEST' if wanted else 'NONE',
                  'issuer_authentication': 'NOT_ESTABLISHED', 'real_world_truth': 'NOT_ESTABLISHED',
                  'external_review': 'NOT_RUN', 'full_framework_conformance': 'NOT_CLAIMED', 'errors': issues}
        if args.mutations and not issues:
            result['evidence_mutations_rejected'] = len(policy_mutation_checks(bundle) if is_policy else mutation_checks(bundle))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if issues else (0 if wanted else 2)
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        print(json.dumps({'result': 'NOT_VERIFIABLE', 'error': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
