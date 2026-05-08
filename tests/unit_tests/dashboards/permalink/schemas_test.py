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
"""Regression tests for dashboard permalink validation schemas.

The dashboard permalink endpoints rely on these Marshmallow schemas to
reject malformed or invalid payloads before they reach the persistence
layer. The tests below lock down that validation surface so future
changes can't silently relax it.
"""

from __future__ import annotations

from typing import Any

import pytest
from marshmallow import ValidationError

from superset.dashboards.permalink.schemas import (
    DashboardPermalinkSchema,
    DashboardPermalinkStateSchema,
)


def test_state_schema_accepts_empty_payload() -> None:
    """An empty state is valid - all fields are optional."""
    assert DashboardPermalinkStateSchema().load({}) == {}


def test_state_schema_accepts_full_payload() -> None:
    """A fully populated state with the documented field types is valid."""
    payload = {
        "dataMask": {"FILTER_1": {"value": "foo"}},
        "activeTabs": ["tab-1", "tab-2"],
        "urlParams": [["foo", "bar"], ["baz", "qux"]],
        "anchor": "anchor-id",
        "chartStates": {"123": {"sort": "asc"}},
    }
    loaded = DashboardPermalinkStateSchema().load(payload)
    # Marshmallow normalizes urlParams items to tuples on load.
    assert loaded["dataMask"] == payload["dataMask"]
    assert loaded["activeTabs"] == payload["activeTabs"]
    assert loaded["urlParams"] == [("foo", "bar"), ("baz", "qux")]
    assert loaded["anchor"] == payload["anchor"]
    assert loaded["chartStates"] == payload["chartStates"]


def test_state_schema_accepts_none_for_optional_fields() -> None:
    """Optional fields explicitly allow None to support partial state."""
    payload: dict[str, Any] = {
        "dataMask": None,
        "activeTabs": None,
        "urlParams": None,
        "anchor": None,
        "chartStates": None,
    }
    assert DashboardPermalinkStateSchema().load(payload) == payload


@pytest.mark.parametrize(
    "field,value",
    [
        ("dataMask", "not-a-dict"),
        ("dataMask", ["not", "a", "dict"]),
        ("dataMask", 42),
        ("activeTabs", "not-a-list"),
        ("activeTabs", {"not": "a list"}),
        ("activeTabs", [1, 2, 3]),  # list items must be strings
        ("anchor", 123),
        ("anchor", ["not", "a", "string"]),
        ("anchor", {"not": "a string"}),
        ("chartStates", "not-a-dict"),
        ("chartStates", ["not", "a", "dict"]),
        ("chartStates", 7),
    ],
)
def test_state_schema_rejects_malformed_field_types(field: str, value: Any) -> None:
    """Each known field rejects payloads that don't match its declared type."""
    with pytest.raises(ValidationError) as excinfo:
        DashboardPermalinkStateSchema().load({field: value})
    assert field in excinfo.value.messages


@pytest.mark.parametrize(
    "url_params",
    [
        "not-a-list",
        {"foo": "bar"},
        [["only-one"]],
        [["a", "b", "c"]],  # too many elements in tuple
        [[1, 2]],  # tuple values must be strings
        [["valid", "tuple"], "string-instead-of-tuple"],
    ],
)
def test_state_schema_rejects_malformed_url_params(url_params: Any) -> None:
    """urlParams must be a list of (string, string) tuples."""
    with pytest.raises(ValidationError) as excinfo:
        DashboardPermalinkStateSchema().load({"urlParams": url_params})
    assert "urlParams" in excinfo.value.messages


def test_state_schema_rejects_completely_wrong_payload_type() -> None:
    """The schema itself must be loaded from a mapping, not a list/string."""
    with pytest.raises(ValidationError):
        DashboardPermalinkStateSchema().load(["not", "an", "object"])
    with pytest.raises(ValidationError):
        DashboardPermalinkStateSchema().load("not-an-object")


def test_permalink_schema_accepts_dashboard_id_only() -> None:
    """state is optional - a permalink can store just the dashboard reference."""
    loaded = DashboardPermalinkSchema().load({"dashboardId": "1"})
    assert loaded["dashboardId"] == "1"


def test_permalink_schema_accepts_nested_state() -> None:
    """A nested state should be coerced through DashboardPermalinkStateSchema."""
    payload = {
        "dashboardId": "abc-slug",
        "state": {"urlParams": [["foo", "bar"]]},
    }
    loaded = DashboardPermalinkSchema().load(payload)
    assert loaded["dashboardId"] == "abc-slug"
    assert loaded["state"]["urlParams"] == [("foo", "bar")]


def test_permalink_schema_requires_dashboard_id() -> None:
    """dashboardId is required - omitting it must fail validation."""
    with pytest.raises(ValidationError) as excinfo:
        DashboardPermalinkSchema().load({"state": {}})
    assert "dashboardId" in excinfo.value.messages


def test_permalink_schema_rejects_none_dashboard_id() -> None:
    """dashboardId must be a non-null string."""
    with pytest.raises(ValidationError) as excinfo:
        DashboardPermalinkSchema().load({"dashboardId": None})
    assert "dashboardId" in excinfo.value.messages


def test_permalink_schema_rejects_invalid_nested_state() -> None:
    """Invalid nested state should propagate as a validation error."""
    with pytest.raises(ValidationError) as excinfo:
        DashboardPermalinkSchema().load(
            {
                "dashboardId": "1",
                "state": {"activeTabs": "not-a-list"},
            }
        )
    assert "state" in excinfo.value.messages


def test_permalink_schema_rejects_non_object_payload() -> None:
    """The top-level payload must be a JSON object."""
    with pytest.raises(ValidationError):
        DashboardPermalinkSchema().load("not-a-dict")
    with pytest.raises(ValidationError):
        DashboardPermalinkSchema().load([{"dashboardId": "1"}])
