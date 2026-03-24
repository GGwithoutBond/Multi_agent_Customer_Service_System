from src.api.middlewares import _should_skip_rate_limit


def test_health_paths_are_rate_limit_exempt():
    assert _should_skip_rate_limit("/health")
    assert _should_skip_rate_limit("/api/v1/health")
    assert _should_skip_rate_limit("/api/v1/admin/health")


def test_regular_api_path_not_exempt():
    assert not _should_skip_rate_limit("/api/v1/chat")
