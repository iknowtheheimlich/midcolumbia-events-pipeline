import sys

import httpx
import pytest

import tools.publish_reddit_live_notion as wrapper


@pytest.mark.parametrize(
    "failure",
    [
        httpx.ConnectError("[Errno 11001] getaddrinfo failed"),
        httpx.ReadError(
            "[WinError 10054] An existing connection was forcibly closed by the remote host"
        ),
    ],
)
def test_wrapper_writes_nothing_when_notion_acquisition_aborts(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
) -> None:
    temp_file_requested = False
    publisher_called = False

    def failed_query(*args, **kwargs):
        raise failure

    def unexpected_temp_file(*args, **kwargs):
        nonlocal temp_file_requested
        temp_file_requested = True
        raise AssertionError("temporary export requested before Notion query succeeded")

    def unexpected_publisher() -> int:
        nonlocal publisher_called
        publisher_called = True
        return 0

    monkeypatch.setenv("NOTION_API_KEY", "token")
    monkeypatch.setattr(wrapper, "fetch_live_weekly_rows", failed_query)
    monkeypatch.setattr(wrapper.tempfile, "NamedTemporaryFile", unexpected_temp_file)
    monkeypatch.setattr(wrapper, "publish_main", unexpected_publisher)
    monkeypatch.setattr(sys, "argv", ["publish_reddit_live_notion"])

    with pytest.raises(type(failure)):
        wrapper.main()

    assert temp_file_requested is False
    assert publisher_called is False
