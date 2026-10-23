from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.exc import OperationalError

from backend.auth.service import AuthDenied, digest
from backend.models import AuthEvent, AuthSession, AuthUser, RegistrationApplication
from backend.user_management import UserConflict
from tests.test_auth import auth, login, ORIGIN
from tests.test_module_management import headers
from tests.test_registration import applicant, set_policy, signup, PENDING


def candidate(owner):
    assert login(owner).status_code == 200
    assert set_policy(owner).status_code == 200
    with applicant(owner.app) as guest:
        result, password = signup(guest)
        assert result.status_code == 202
    return owner.get(PENDING).json()['items'][0], password


def test_rejection_is_durable_private_unapproved_and_not_an_account(auth):
    owner, service, _ = auth
    row, password = candidate(owner)
    path = PENDING+'/'+row['id']
    directory = owner.get('/api/admin/users').json()['items']
    assert row['id'] not in {item['id'] for item in directory}
    detail = owner.get(path)
    assert detail.status_code == 200 and detail.json()['state'] == 'pending'
    assert set(detail.json()) == {'id', 'username', 'state', 'created_at'}
    assert 'no-store' in detail.headers['Cache-Control']
    assert owner.post(path+'/reject', headers={'Origin': ORIGIN}).status_code == 403
    assert owner.post(path+'/reject', headers={**headers(owner), 'Origin':'https://evil.test'}).status_code == 403
    for _ in range(2):
        result = owner.post(path+'/reject', headers=headers(owner))
        assert result.status_code == 200 and result.json() == {'state':'rejected'}
    assert owner.get(PENDING).json()['items'] == []
    assert owner.get(PENDING+'?state=rejected').json()['items'] == [{**row, 'state':'rejected'}]
    assert owner.get(path).json()['state'] == 'rejected'
    assert owner.post(path+'/approve', headers=headers(owner)).status_code == 409
    assert owner.patch('/api/admin/users/'+row['id'], json=dict(role='viewer',active=True,
        expected_role='viewer',expected_active=False), headers=headers(owner)).status_code == 403
    with applicant(owner.app) as guest:
        assert login(guest,password,'candidate').status_code == 401
    with service.transaction() as session:
        target = session.get(AuthUser,row['id'])
        assert not target.active and target.role == 'viewer' and not target.is_admin
        assert session.get(RegistrationApplication,row['id']).pending
        assert session.scalar(select(func.count()).select_from(AuthEvent).where(
            AuthEvent.user_id == row['id'],AuthEvent.event == 'registration_rejected')) == 1
    assert owner.get(PENDING+'?state=approved').status_code == 422
    assert owner.get(PENDING+'/missing').status_code == 404
    assert owner.post(PENDING+'/missing/reject',headers=headers(owner)).status_code == 404


@pytest.mark.parametrize('role', ['admin', 'viewer'])
def test_reviews_are_owner_only_and_revoked_session_cannot_review(auth,role):
    owner, service, actor = auth
    row, _ = candidate(owner)
    key = digest(owner.cookies.get('__Host-runtu_session'))
    with service.transaction() as session: session.get(AuthUser,actor).role = role
    path = PENDING+'/'+row['id']
    assert owner.get(PENDING+'?state=rejected').status_code == 403
    assert owner.get(path).status_code == 403
    assert owner.post(path+'/reject',headers=headers(owner)).status_code == 403
    with service.transaction() as session:
        session.get(AuthUser,actor).role = 'owner'
        session.delete(session.get(AuthSession,key))
    with pytest.raises(AuthDenied): owner.app.state.registration.reject(actor,key,row['id'])


def test_opposing_reviews_serialize_without_enabling_rejected_users(auth):
    owner, service, actor = auth
    row, _ = candidate(owner)
    key = digest(owner.cookies.get('__Host-runtu_session'))
    review = owner.app.state.registration
    def decide(action):
        try: return getattr(review,action)(actor,key,row['id'])['state']
        except UserConflict: return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(decide,['approve','reject']))
    assert sorted(results) in (['approved','conflict'],['conflict','rejected'])
    state = owner.get(PENDING+'/'+row['id']).json()['state']
    with service.transaction() as session:
        assert session.get(AuthUser,row['id']).active == (state == 'approved')
        assert session.scalar(select(func.count()).select_from(AuthEvent).where(AuthEvent.user_id == row['id'],
            AuthEvent.event.in_(['registration_approved','registration_rejected']))) == 1


def test_reject_audit_failure_rolls_back_and_approved_cannot_be_rejected(auth):
    owner, service, _ = auth
    row, _ = candidate(owner)
    path = PENDING+'/'+row['id']
    def fail(*_): raise OperationalError('isolated audit failure',{},Exception('unavailable'))
    event.listen(AuthEvent,'before_insert',fail)
    try: assert owner.post(path+'/reject',headers=headers(owner)).status_code == 503
    finally: event.remove(AuthEvent,'before_insert',fail)
    assert owner.get(path).json()['state'] == 'pending'
    assert owner.post(path+'/approve',headers=headers(owner)).status_code == 200
    assert owner.post(path+'/reject',headers=headers(owner)).status_code == 409
    assert owner.get(path).json()['state'] == 'approved'
    assert row['id'] in {item['id'] for item in owner.get('/api/admin/users').json()['items']}
