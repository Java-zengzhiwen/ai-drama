from ai_drama_web.suppliers.rate_limits import SupplierRateLimiter


def test_supplier_rate_limiter_is_shared_by_bucket_and_uses_a_rolling_minute():
    now = [100.0]
    limiter = SupplierRateLimiter(rpm=2, clock=lambda: now[0])

    assert limiter.acquire("shared") is True
    assert limiter.acquire("shared") is True
    assert limiter.acquire("shared") is False
    assert limiter.acquire("other") is True
    now[0] += 60.1
    assert limiter.acquire("shared") is True


def test_supplier_rate_limiter_keeps_the_strictest_registered_bucket_limit():
    now = [100.0]
    limiter = SupplierRateLimiter(rpm=60, clock=lambda: now[0])

    assert limiter.acquire("agnes", rpm=1) is True
    assert limiter.acquire("agnes") is False
    assert limiter.acquire("openai") is True
