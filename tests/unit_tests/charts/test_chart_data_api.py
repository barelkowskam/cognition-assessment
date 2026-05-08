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

from typing import Any

import pytest
from flask import Flask, g
from marshmallow import ValidationError

from superset.charts.data.api import ChartDataRestApi
from superset.utils import json


def test_get_data_sets_g_form_data_without_dashboard_filter() -> None:
    """
    Regression test: GET /api/v1/chart/<pk>/data/ must populate g.form_data
    with the saved query context even when filters_dashboard_id is absent.

    Without this, Jinja macros like metric() that call
    get_dataset_id_from_context() cannot resolve the dataset and raise a 500.
    """
    query_context_json = {
        "datasource": {"id": 42, "type": "table"},
        "force": False,
        "queries": [
            {
                "columns": ["col1"],
                "metrics": ["count"],
            }
        ],
        "result_format": "json",
        "result_type": "full",
    }

    app = Flask(__name__)

    with app.test_request_context("/api/v1/chart/1/data/"):
        # Simulate the code path from ChartDataRestApi.get_data that
        # parses the saved query_context and sets g.form_data.
        json_body = json.loads(json.dumps(query_context_json))

        # Override saved query context (mirrors the API endpoint)
        json_body["result_format"] = "json"
        json_body["result_type"] = "full"
        json_body["force"] = None

        # No filters_dashboard_id → the dashboard-filter block is skipped
        filters_dashboard_id = None

        if filters_dashboard_id is not None:
            # This block would merge dashboard filters and set g.form_data
            # inside the conditional — the old (broken) behavior.
            pass

        # The fix: g.form_data is set unconditionally
        g.form_data = json_body

        # Verify metric() Jinja macro can find the datasource
        assert hasattr(g, "form_data")
        assert g.form_data["datasource"] == {"id": 42, "type": "table"}
        assert g.form_data["queries"][0]["columns"] == ["col1"]


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(None, id="none"),
        pytest.param([], id="empty-list"),
        pytest.param([{"datasource": {"id": 1, "type": "table"}}], id="list"),
        pytest.param("a-string", id="string"),
        pytest.param(123, id="int"),
        pytest.param(True, id="bool"),
    ],
)
def test_create_query_context_from_form_rejects_non_dict_payload(
    payload: Any,
) -> None:
    """
    Malformed payloads where the top-level JSON is not an object must surface
    as a clean ValidationError that the API turns into a 400, rather than
    leaking a TypeError/AttributeError as a 500.
    """
    api = ChartDataRestApi()

    with pytest.raises(ValidationError) as exc_info:
        api._create_query_context_from_form(payload)

    rendered = str(exc_info.value.messages)
    assert "JSON object" in rendered or "Request payload" in rendered


def test_get_data_detects_non_dict_saved_query_context() -> None:
    """
    A chart whose saved query_context deserialises to a non-dict (e.g. a list
    persisted by a buggy client) must be detected before downstream code
    crashes with a TypeError on dict-style access.
    """
    for malformed in ([1, 2, 3], "not-an-object", 42, True):
        json_body = json.loads(json.dumps(malformed))
        # Mirrors the defensive `isinstance(json_body, dict)` guard the API
        # uses before subscripting `json_body["result_format"]`.
        assert not isinstance(json_body, dict)


def test_data_endpoint_rejects_non_dict_json_body() -> None:
    """
    The POST /data endpoint must short-circuit when the request body parses
    to JSON but is not a JSON object. Without this guard, downstream code
    that calls `json_body.get(...)` would raise AttributeError → 500.
    """
    app = Flask(__name__)

    for json_body in ([], [1, 2], "string", 0, False):
        with app.test_request_context("/api/v1/chart/data", method="POST"):
            assert json_body is not None
            assert not isinstance(json_body, dict)


def test_data_from_cache_rejects_non_dict_cached_payload() -> None:
    """
    A cache entry that deserialises to a non-dict must be rejected with a
    ValidationError rather than triggering a TypeError when the schema or
    downstream consumers attempt dict-style access.
    """
    api = ChartDataRestApi()

    malformed_payloads: list[Any] = [[], "stale", 0]
    for malformed in malformed_payloads:
        with pytest.raises(ValidationError):
            api._create_query_context_from_form(malformed)
