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

import pytest
from marshmallow import ValidationError

from superset.dashboards.permalink.schemas import DashboardPermalinkStateSchema

schema = DashboardPermalinkStateSchema()


# -- Valid payloads -----------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"dataMask": None},
        {"activeTabs": None},
        {"dataMask": {"FILTER_1": "foo"}, "activeTabs": ["tab-1"]},
        {"anchor": "my-anchor"},
        {"urlParams": [("key", "value")]},
        {"chartStates": {"chart_1": {"sortBy": "col_a"}}},
        {
            "dataMask": {"FILTER_1": {"filterState": {"value": [1]}}},
            "activeTabs": ["tab-1", "tab-2"],
            "anchor": "section-1",
            "urlParams": [("k", "v")],
            "chartStates": {},
        },
    ],
    ids=[
        "empty_payload",
        "dataMask_null",
        "activeTabs_null",
        "typical_state",
        "anchor_only",
        "urlParams_only",
        "chartStates_only",
        "all_fields_populated",
    ],
)
def test_valid_payloads_load_successfully(payload: dict[str, object]) -> None:
    result = schema.load(payload)
    for key, value in payload.items():
        assert result.get(key) == value


# -- Unknown fields are stripped (Marshmallow RAISE default) ------------------


def test_unknown_fields_are_rejected() -> None:
    """Unknown top-level keys should raise a ValidationError."""
    with pytest.raises(ValidationError, match="Unknown field"):
        schema.load({"unknownField": "should_fail"})


def test_unknown_fields_alongside_valid_are_rejected() -> None:
    with pytest.raises(ValidationError, match="Unknown field"):
        schema.load(
            {
                "dataMask": {"FILTER_1": "foo"},
                "activeTabs": ["tab-1"],
                "totallyBogus": 123,
            }
        )


# -- dataMask type validation -------------------------------------------------


@pytest.mark.parametrize(
    "bad_value",
    [
        "a-string",
        42,
        True,
        ["a", "list"],
    ],
    ids=["string", "int", "bool", "list"],
)
def test_data_mask_rejects_non_dict(bad_value: object) -> None:
    with pytest.raises(ValidationError, match="dataMask"):
        schema.load({"dataMask": bad_value})


# -- activeTabs type validation -----------------------------------------------


@pytest.mark.parametrize(
    "bad_value",
    [
        "not-a-list",
        {"key": "val"},
        123,
        True,
    ],
    ids=["string", "dict", "int", "bool"],
)
def test_active_tabs_rejects_non_list(bad_value: object) -> None:
    with pytest.raises(ValidationError, match="activeTabs"):
        schema.load({"activeTabs": bad_value})


def test_active_tabs_rejects_non_string_items() -> None:
    with pytest.raises(ValidationError, match="activeTabs"):
        schema.load({"activeTabs": [1, 2, 3]})


# -- urlParams type validation -----------------------------------------------


@pytest.mark.parametrize(
    "bad_value",
    [
        "not-a-list",
        {"key": "val"},
        123,
    ],
    ids=["string", "dict", "int"],
)
def test_url_params_rejects_non_list(bad_value: object) -> None:
    with pytest.raises(ValidationError, match="urlParams"):
        schema.load({"urlParams": bad_value})


def test_url_params_rejects_wrong_tuple_length() -> None:
    """Each urlParam entry must be a 2-tuple (key, value)."""
    with pytest.raises(ValidationError):
        schema.load({"urlParams": [["only_one_element"]]})


def test_url_params_rejects_three_element_tuple() -> None:
    with pytest.raises(ValidationError):
        schema.load({"urlParams": [["a", "b", "c"]]})


# -- anchor type validation ---------------------------------------------------


@pytest.mark.parametrize(
    "bad_value",
    [
        123,
        ["a", "list"],
        {"key": "val"},
        True,
    ],
    ids=["int", "list", "dict", "bool"],
)
def test_anchor_rejects_non_string(bad_value: object) -> None:
    with pytest.raises(ValidationError, match="anchor"):
        schema.load({"anchor": bad_value})


# -- chartStates type validation ----------------------------------------------


@pytest.mark.parametrize(
    "bad_value",
    [
        "a-string",
        42,
        True,
        ["a", "list"],
    ],
    ids=["string", "int", "bool", "list"],
)
def test_chart_states_rejects_non_dict(bad_value: object) -> None:
    with pytest.raises(ValidationError, match="chartStates"):
        schema.load({"chartStates": bad_value})


# -- Empty string edge cases --------------------------------------------------


def test_anchor_accepts_empty_string() -> None:
    result = schema.load({"anchor": ""})
    assert result["anchor"] == ""


def test_active_tabs_accepts_empty_list() -> None:
    result = schema.load({"activeTabs": []})
    assert result["activeTabs"] == []


def test_data_mask_accepts_empty_dict() -> None:
    result = schema.load({"dataMask": {}})
    assert result["dataMask"] == {}


def test_url_params_accepts_empty_list() -> None:
    result = schema.load({"urlParams": []})
    assert result["urlParams"] == []


def test_chart_states_accepts_empty_dict() -> None:
    result = schema.load({"chartStates": {}})
    assert result["chartStates"] == {}
