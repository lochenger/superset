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

from superset.temporary_cache.schemas import (
    TemporaryCachePostSchema,
    TemporaryCachePutSchema,
)


def test_post_schema_accepts_valid_json_string() -> None:
    schema = TemporaryCachePostSchema()
    result = schema.load({"value": '{"key": "val"}'})
    assert result["value"] == '{"key": "val"}'


def test_post_schema_accepts_json_array() -> None:
    schema = TemporaryCachePostSchema()
    result = schema.load({"value": "[1, 2, 3]"})
    assert result["value"] == "[1, 2, 3]"


def test_post_schema_rejects_missing_value() -> None:
    schema = TemporaryCachePostSchema()
    with pytest.raises(ValidationError) as exc_info:
        schema.load({})
    assert "value" in exc_info.value.messages


def test_post_schema_rejects_none_value() -> None:
    schema = TemporaryCachePostSchema()
    with pytest.raises(ValidationError):
        schema.load({"value": None})


def test_post_schema_rejects_invalid_json() -> None:
    schema = TemporaryCachePostSchema()
    with pytest.raises(ValidationError):
        schema.load({"value": "not valid json {"})


def test_put_schema_accepts_valid_json_string() -> None:
    schema = TemporaryCachePutSchema()
    result = schema.load({"value": '{"updated": true}'})
    assert result["value"] == '{"updated": true}'


def test_put_schema_rejects_missing_value() -> None:
    schema = TemporaryCachePutSchema()
    with pytest.raises(ValidationError) as exc_info:
        schema.load({})
    assert "value" in exc_info.value.messages


def test_put_schema_rejects_invalid_json() -> None:
    schema = TemporaryCachePutSchema()
    with pytest.raises(ValidationError):
        schema.load({"value": "{bad json"})
