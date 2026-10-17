"""Placeholder values shared by the tests. None of them is a real identifier."""

from __future__ import annotations

from typing import Final

REPLY_ID: Final = "00000000-0000-4000-8000-000000000000"
OTHER_REPLY_ID: Final = "00000000-0000-4000-8000-000000000001"
REPLY_URL: Final = (
    f"https://www.ff-agent.com/app2/missionreplies/{REPLY_ID}/accept?transport=CAR"
)
OTHER_REPLY_URL: Final = (
    f"https://www.ff-agent.com/app2/missionreplies/{OTHER_REPLY_ID}/accept"
    "?transport=CAR"
)
WEBHOOK_ID: Final = "test-webhook-id-placeholder"
CLOUDHOOK_URL: Final = "https://hooks.nabu.casa/test-placeholder"
EXTERNAL_URL: Final = "https://example.com"
INTERNAL_URL: Final = "http://192.168.1.10:8123"
HEADER_TOKEN: Final = "test-header-token-placeholder-0123456789abcdef"

# Reply URLs without a query: the mock of the HTTP client matches any query.
ACCEPT_URL: Final = f"https://www.ff-agent.com/app2/missionreplies/{REPLY_ID}/accept"
REJECT_URL: Final = f"https://www.ff-agent.com/app2/missionreplies/{REPLY_ID}/reject"
OTHER_ACCEPT_URL: Final = (
    f"https://www.ff-agent.com/app2/missionreplies/{OTHER_REPLY_ID}/accept"
)
OTHER_WEBHOOK_ID: Final = "test-webhook-id-placeholder-other"

# An invented position and the entity that provides it. Not a real place.
LATITUDE: Final = 1.2345
LONGITUDE: Final = 6.789
LOCATION_ENTITY: Final = "person.test_person"
