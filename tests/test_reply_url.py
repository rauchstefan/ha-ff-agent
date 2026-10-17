"""Tests for the mission reply URL parser."""

from __future__ import annotations

import pytest

from custom_components.ff_agent.const import DEFAULT_REPLY_HOST
from custom_components.ff_agent.reply_url import (
    InvalidReplyUrl,
    ReplyTarget,
    parse_reply_input,
    reply_unique_id,
)

from .const import OTHER_REPLY_ID, REPLY_ID

BASE = "https://www.ff-agent.com/app2/missionreplies"
HOST = "www.ff-agent.com"
PATH = "/app2/missionreplies"
QUERY = "?transport=CAR&lat=1.2345&lng=6.789#x"


@pytest.mark.parametrize(
    ("value", "host"),
    [
        (f"{BASE}/{REPLY_ID}/accept?transport=CAR", HOST),
        (f"{BASE}/{REPLY_ID}/accept{QUERY}", HOST),
        (f"{BASE}/{REPLY_ID}/reject", HOST),
        (f"{BASE}/{REPLY_ID.upper()}/accept", HOST),
        (f"  \n{BASE}/{REPLY_ID}/accept\t ", HOST),
        (f"{BASE}/{REPLY_ID}/accept/", HOST),
        (
            f"https://free.ff-agent.com/app2/missionreplies/{REPLY_ID}/accept",
            "free.ff-agent.com",
        ),
        (
            f"https://WWW.FF-AGENT.COM/app2/missionreplies/{REPLY_ID}/accept",
            HOST,
        ),
        (f"https://ff-agent.com/app2/missionreplies/{REPLY_ID}/accept", "ff-agent.com"),
        (
            f"https://www.ff-agent.com:443/app2/missionreplies/{REPLY_ID}/accept",
            HOST,
        ),
        (REPLY_ID, DEFAULT_REPLY_HOST),
        (REPLY_ID.upper(), DEFAULT_REPLY_HOST),
        (f"  {REPLY_ID}  ", DEFAULT_REPLY_HOST),
    ],
)
def test_valid_input(value: str, host: str) -> None:
    """Valid URLs and bare UUIDs yield the normalized UUID and the host."""
    assert parse_reply_input(value) == ReplyTarget(host=host, reply_id=REPLY_ID)


@pytest.mark.parametrize(
    "value",
    [
        f"http://www.ff-agent.com/app2/missionreplies/{REPLY_ID}/accept",
        f"https://ff-agent.com.example.org/app2/missionreplies/{REPLY_ID}/accept",
        f"https://example.com/app2/missionreplies/{REPLY_ID}/accept",
        f"https://evilff-agent.com/app2/missionreplies/{REPLY_ID}/accept",
        f"https://www.ff-agent.com@example.com/app2/missionreplies/{REPLY_ID}/accept",
        f"https://user:pw@www.ff-agent.com/app2/missionreplies/{REPLY_ID}/accept",
        f"https://www.ff-agent.com:8443/app2/missionreplies/{REPLY_ID}/accept",
        f"https://www.ff-agent.com/app3/missionreplies/{REPLY_ID}/accept",
        f"https://www.ff-agent.com/app2/other/{REPLY_ID}/accept",
        f"https://www.ff-agent.com/x/app2/missionreplies/{REPLY_ID}/accept",
        f"https://www.ff-agent.com/app2/missionreplies/{REPLY_ID}/accept/more",
        f"https://www.ff-agent.com/app2/missionreplies/{REPLY_ID}",
        f"https://www.ff-agent.com/app2/missionreplies/{REPLY_ID}/",
        f"https://www.ff-agent.com/app2/missionreplies/{REPLY_ID}/cancel",
        f"https://www.ff-agent.com/app2/missionreplies/{REPLY_ID}/ACCEPT",
        "https://www.ff-agent.com/app2/missionreplies/not-a-uuid/accept",
        "https://www.ff-agent.com/app2/missionreplies/accept",
        f"www.ff-agent.com/app2/missionreplies/{REPLY_ID}/accept",
        "https://[broken/app2/missionreplies/x/accept",
        "not-a-uuid",
        "0000",
        "",
        "   ",
    ],
)
def test_invalid_input(value: str) -> None:
    """Everything else is rejected without echoing the input."""
    with pytest.raises(InvalidReplyUrl) as err:
        parse_reply_input(value)
    assert not err.value.args


def test_unique_id_is_deterministic_and_hides_the_uuid() -> None:
    """The unique ID is a stable 16 character hash without the UUID in it."""
    unique_id = reply_unique_id(REPLY_ID)

    assert unique_id == reply_unique_id(REPLY_ID)
    assert len(unique_id) == 16
    assert all(char in "0123456789abcdef" for char in unique_id)
    assert REPLY_ID not in unique_id
    assert REPLY_ID.replace("-", "") not in unique_id


def test_unique_id_differs_per_person() -> None:
    """Two different reply IDs never share a unique ID."""
    assert reply_unique_id(REPLY_ID) != reply_unique_id(OTHER_REPLY_ID)


@pytest.mark.parametrize(
    "value",
    [
        f"HTTPS://WWW.FF-AGENT.COM/app2/missionreplies/{REPLY_ID}/accept",
        f"https://www.ff-agent.com/app2/missionreplies/{REPLY_ID.upper()}/reject/",
        f"https://www.ff-agent.com/app2/missionreplies/{REPLY_ID}/accept?x=1&x=2",
    ],
)
def test_valid_input_case_and_query_variants(value: str) -> None:
    """Scheme and host case, an upper-case UUID and odd queries are accepted."""
    target = parse_reply_input(value)

    assert target.reply_id == REPLY_ID
    assert target.host in {"www.ff-agent.com"}


@pytest.mark.parametrize(
    "value",
    [
        f"https://ff-agent.com.evil.example{PATH}/{REPLY_ID}/accept",
        f"https://www.ff-agent.com.evil.example{PATH}/{REPLY_ID}/accept",
        f"https://evil.example/ff-agent.com{PATH}/{REPLY_ID}/accept",
        f"https://evil.example/?u=www.ff-agent.com{PATH}/{REPLY_ID}/accept",
        f"https://evil.example/#www.ff-agent.com{PATH}/{REPLY_ID}/accept",
        f"https://www.ff-agent.com./app2/missionreplies/{REPLY_ID}/accept",
        f"https://www.ff-agent.com//app2/missionreplies/{REPLY_ID}/accept",
        f"https://www.ff-agent.com/app2//missionreplies/{REPLY_ID}/accept",
        rf"https://example.com\@www.ff-agent.com{PATH}/{REPLY_ID}/accept",
        f"ftp://www.ff-agent.com/app2/missionreplies/{REPLY_ID}/accept",
        f"//www.ff-agent.com/app2/missionreplies/{REPLY_ID}/accept",
        f"https:///app2/missionreplies/{REPLY_ID}/accept",
        f"https://www.ff-agent.com:0/app2/missionreplies/{REPLY_ID}/accept",
        f"{BASE}/{OTHER_REPLY_ID}/{REPLY_ID}",
        f"https://www.ff-agent.com/app2/missionreplies/{REPLY_ID}x/accept",
        f"{REPLY_ID}/accept",
        f"{REPLY_ID}\n{REPLY_ID}",
    ],
)
def test_hostile_and_malformed_input_is_rejected(value: str) -> None:
    """Look-alike hosts, smuggled hosts and malformed paths are not accepted."""
    with pytest.raises(InvalidReplyUrl):
        parse_reply_input(value)


@pytest.mark.parametrize(
    "value",
    [
        f"http://www.ff-agent.com{PATH}/{REPLY_ID}/accept?t=secret",
        "https://example.com/app2/missionreplies/not-a-uuid/accept?t=secret",
        "",
    ],
)
def test_error_does_not_carry_the_input(value: str) -> None:
    """Neither the message nor the exception chain contains the input."""
    with pytest.raises(InvalidReplyUrl) as err:
        parse_reply_input(value)

    assert str(err.value) == ""
    assert err.value.__cause__ is None
    assert err.value.__suppress_context__ or err.value.__context__ is None
    assert REPLY_ID not in repr(err.value)


@pytest.mark.parametrize(
    "host",
    [
        "evil-ff-agent.com",
        "www.ff‑agent.com",  # U+2011 non-breaking hyphen
        "www.ff‐agent.com",  # U+2010 hyphen
        "www.ff-agent.com。evil.example",  # ideographic full stop
        "www.ff-agent.com_.evil.example",
        "www.ff-agent.coм",  # Cyrillic letter
        "www..ff-agent.com",
    ],
)
def test_lookalike_hosts_are_rejected(host: str) -> None:
    """Non-ASCII look-alikes and odd host labels never pass the host check."""
    with pytest.raises(InvalidReplyUrl):
        parse_reply_input(f"https://{host}{PATH}/{REPLY_ID}/accept")
