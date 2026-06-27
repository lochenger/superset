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

from superset.explorables.base import (
    ColumnMetadata,
    Explorable,
    MetricMetadata,
    TimeGrainDict,
)


class ConcreteMetric:
    """Minimal implementation that satisfies MetricMetadata."""

    @property
    def metric_name(self) -> str:
        return "count_star"

    @property
    def expression(self) -> str:
        return "COUNT(*)"

    @property
    def verbose_name(self) -> str | None:
        return "Count"

    @property
    def description(self) -> str | None:
        return "Row count"

    @property
    def d3format(self) -> str | None:
        return ",d"

    @property
    def currency(self) -> dict[str, Any] | None:
        return None

    @property
    def warning_text(self) -> str | None:
        return None

    @property
    def certified_by(self) -> str | None:
        return None

    @property
    def certification_details(self) -> str | None:
        return None


class ConcreteColumn:
    """Minimal implementation that satisfies ColumnMetadata."""

    @property
    def column_name(self) -> str:
        return "user_id"

    @property
    def type(self) -> str:
        return "INTEGER"

    @property
    def is_dttm(self) -> bool:
        return False

    @property
    def verbose_name(self) -> str | None:
        return "User ID"

    @property
    def description(self) -> str | None:
        return None

    @property
    def groupby(self) -> bool:
        return True

    @property
    def filterable(self) -> bool:
        return True

    @property
    def expression(self) -> str | None:
        return None

    @property
    def python_date_format(self) -> str | None:
        return None

    @property
    def advanced_data_type(self) -> str | None:
        return None

    @property
    def extra(self) -> str | None:
        return None


def test_metric_metadata_protocol_isinstance() -> None:
    metric = ConcreteMetric()
    assert isinstance(metric, MetricMetadata)


def test_metric_metadata_properties() -> None:
    metric = ConcreteMetric()
    assert metric.metric_name == "count_star"
    assert metric.expression == "COUNT(*)"
    assert metric.verbose_name == "Count"


def test_column_metadata_protocol_isinstance() -> None:
    col = ConcreteColumn()
    assert isinstance(col, ColumnMetadata)


def test_column_metadata_properties() -> None:
    col = ConcreteColumn()
    assert col.column_name == "user_id"
    assert col.type == "INTEGER"
    assert col.is_dttm is False
    assert col.groupby is True
    assert col.filterable is True


def test_non_conforming_object_not_metric_metadata() -> None:
    class BadMetric:
        pass

    assert not isinstance(BadMetric(), MetricMetadata)


def test_non_conforming_object_not_column_metadata() -> None:
    class BadColumn:
        pass

    assert not isinstance(BadColumn(), ColumnMetadata)


def test_time_grain_dict_structure() -> None:
    grain: TimeGrainDict = {
        "name": "Hour",
        "function": "DATE_TRUNC('hour', {col})",
        "duration": "PT1H",
    }
    assert grain["name"] == "Hour"
    assert grain["function"] == "DATE_TRUNC('hour', {col})"
    assert grain["duration"] == "PT1H"


def test_time_grain_dict_with_none_duration() -> None:
    grain: TimeGrainDict = {
        "name": "Smart Date",
        "function": "{col}",
        "duration": None,
    }
    assert grain["duration"] is None


def test_explorable_protocol_is_runtime_checkable() -> None:
    assert hasattr(Explorable, "__protocol_attrs__") or hasattr(
        Explorable, "__abstractmethods__"
    )
