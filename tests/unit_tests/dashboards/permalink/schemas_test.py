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
"""
Regression coverage for the dashboard permalink payload validators.

These tests exercise ``DashboardPermalinkStateSchema`` (used by the POST
``/api/v1/dashboard/<pk>/permalink`` endpoint to validate inbound state
payloads) so that future changes cannot silently regress the validation
contract.
"""

from typing import Any

import pytest
from marshmallow import ValidationError

from superset.dashboards.permalink.schemas import DashboardPermalinkStateSchema


def test_state_schema_load_empty_payload() -> None:
    """An empty payload is valid because every field is optional."""
    assert DashboardPermalinkStateSchema().load({}) == {}


def test_state_schema_load_full_valid_payload() -> None:
    """A fully-specified payload deserializes with ``urlParams`` as tuples."""
    payload = {
        "dataMask": {"FILTER_1": {"value": "foo"}},
        "activeTabs": ["TAB-1", "TAB-2"],
        "urlParams": [["foo", "bar"], ["baz", "qux"]],
        "anchor": "section-1",
        "chartStates": {"42": {"sortBy": "name"}},
    }
    assert DashboardPermalinkStateSchema().load(payload) == {
        "dataMask": {"FILTER_1": {"value": "foo"}},
        "activeTabs": ["TAB-1", "TAB-2"],
        "urlParams": [("foo", "bar"), ("baz", "qux")],
        "anchor": "section-1",
        "chartStates": {"42": {"sortBy": "name"}},
    }


def test_state_schema_load_allows_none_for_nullable_fields() -> None:
    """All declared fields permit ``None`` and round-trip unchanged."""
    payload = {
        "dataMask": None,
        "activeTabs": None,
        "urlParams": None,
        "anchor": None,
        "chartStates": None,
    }
    assert DashboardPermalinkStateSchema().load(payload) == payload


@pytest.mark.parametrize(
    "payload,invalid_field",
    [
        ({"foo": "bar"}, "foo"),
        ({"dataMask": ["not", "a", "dict"]}, "dataMask"),
        ({"activeTabs": "not-a-list"}, "activeTabs"),
        ({"activeTabs": [{"unhashable": "object"}]}, "activeTabs"),
        ({"urlParams": [["only-one-element"]]}, "urlParams"),
        ({"urlParams": [["a", "b", "c"]]}, "urlParams"),
        ({"urlParams": "not-a-list"}, "urlParams"),
        ({"chartStates": ["not", "a", "dict"]}, "chartStates"),
    ],
)
def test_state_schema_rejects_invalid_payload(
    payload: dict[str, Any], invalid_field: str
) -> None:
    """Malformed payloads raise ``ValidationError`` flagging the bad field."""
    with pytest.raises(ValidationError) as exc_info:
        DashboardPermalinkStateSchema().load(payload)
    assert invalid_field in exc_info.value.messages
