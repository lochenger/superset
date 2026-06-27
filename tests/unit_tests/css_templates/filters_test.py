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

from unittest.mock import MagicMock

from superset.css_templates.filters import CssTemplateAllTextFilter


def _make_filter() -> CssTemplateAllTextFilter:
    """Instantiate the filter bypassing FAB's __init__."""
    instance = CssTemplateAllTextFilter.__new__(CssTemplateAllTextFilter)
    return instance


def test_filter_name() -> None:
    assert str(CssTemplateAllTextFilter.name) == "All Text"


def test_filter_arg_name() -> None:
    assert CssTemplateAllTextFilter.arg_name == "css_template_all_text"


def test_filter_apply_returns_query_unchanged_for_empty_value() -> None:
    filter_instance = _make_filter()
    mock_query = MagicMock()
    result = filter_instance.apply(mock_query, "")
    assert result is mock_query
    mock_query.filter.assert_not_called()


def test_filter_apply_returns_query_unchanged_for_none_value() -> None:
    filter_instance = _make_filter()
    mock_query = MagicMock()
    result = filter_instance.apply(mock_query, None)
    assert result is mock_query
    mock_query.filter.assert_not_called()


def test_filter_apply_filters_query_for_nonempty_value() -> None:
    filter_instance = _make_filter()
    mock_query = MagicMock()
    filter_instance.apply(mock_query, "dark theme")
    mock_query.filter.assert_called_once()
