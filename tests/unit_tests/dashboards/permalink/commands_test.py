# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from __future__ import annotations

from unittest.mock import patch

import pytest

from superset.dashboards.permalink.exceptions import DashboardPermalinkGetFailedError
from superset.key_value.exceptions import KeyValueParseKeyError

# -- GetDashboardPermalinkCommand with malformed keys -------------------------


@pytest.mark.parametrize(
    "bad_key",
    [
        "",
        "!@#$%^&*()",
        "a" * 1000,
        " ",
        "\t\n",
        "null",
        "<script>alert(1)</script>",
        "'; DROP TABLE key_value; --",
    ],
    ids=[
        "empty_string",
        "special_characters",
        "very_long_key",
        "whitespace_only",
        "tab_newline",
        "null_literal",
        "xss_attempt",
        "sql_injection_attempt",
    ],
)
def test_get_command_rejects_malformed_keys(bad_key: str) -> None:
    """GetDashboardPermalinkCommand should fail gracefully for invalid keys."""
    with patch(
        "superset.commands.dashboard.permalink.base.get_permalink_salt",
        return_value="test_salt",
    ):
        from superset.commands.dashboard.permalink.get import (
            GetDashboardPermalinkCommand,
        )

        cmd = GetDashboardPermalinkCommand(key=bad_key)
        with pytest.raises(DashboardPermalinkGetFailedError):
            cmd.run()


# -- decode_permalink_id with invalid keys ------------------------------------


@pytest.mark.parametrize(
    "bad_key",
    [
        "",
        "not-a-valid-hashid",
        "!@#$%",
        " ",
        "0",
        "-1",
        "a" * 500,
    ],
    ids=[
        "empty_string",
        "invalid_hashid",
        "special_chars",
        "whitespace",
        "zero_string",
        "negative_string",
        "very_long",
    ],
)
def test_decode_permalink_id_rejects_invalid_keys(bad_key: str) -> None:
    from superset.key_value.utils import decode_permalink_id

    with pytest.raises(KeyValueParseKeyError):
        decode_permalink_id(bad_key, "some_salt")


def test_encode_decode_permalink_roundtrip() -> None:
    """Encoded key should decode back to the original integer id."""
    from superset.key_value.utils import decode_permalink_id, encode_permalink_key

    salt = "test_salt_value"
    original_id = 42
    encoded = encode_permalink_key(original_id, salt)
    decoded = decode_permalink_id(encoded, salt)
    assert decoded == original_id


def test_decode_permalink_wrong_salt_fails() -> None:
    """Decoding with the wrong salt should raise KeyValueParseKeyError."""
    from superset.key_value.utils import decode_permalink_id, encode_permalink_key

    encoded = encode_permalink_key(42, "correct_salt")
    with pytest.raises(KeyValueParseKeyError):
        decode_permalink_id(encoded, "wrong_salt")
