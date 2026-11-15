"""The persisted-request funnel is staff-only; missing attribution remains unknown."""

from tests.support import form, submit


def test_request_funnel_uses_real_saved_requests_and_requires_auth(client, admin):
    assert client.get('/api/v1/admin/requests/funnel').status_code == 401
    assert submit(client, form()).status_code == 201
    answer = admin.ok(admin.get('/requests/funnel'))
    assert answer['totals']['leads'] == 1
    assert answer['totals']['confirmedOrders'] == answer['totals']['paymentReceived'] == 0
    [channel] = answer['channels']
    assert channel['channel'] == 'unknown' and channel['name'] == 'Не определён'
    assert admin.get('/requests/funnel?period=0').status_code == 422
