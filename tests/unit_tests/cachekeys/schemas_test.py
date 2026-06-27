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

from superset.cachekeys.schemas import CacheInvalidationRequestSchema, Datasource


def test_datasource_schema_valid_table_type() -> None:
    schema = Datasource()
    result = schema.load(
        {
            "database_name": "my_db",
            "datasource_name": "my_table",
            "schema": "public",
            "datasource_type": "table",
        }
    )
    assert result["datasource_type"] == "table"
    assert result["database_name"] == "my_db"


def test_datasource_schema_accepts_catalog() -> None:
    schema = Datasource()
    result = schema.load(
        {
            "datasource_type": "table",
            "catalog": "my_catalog",
        }
    )
    assert result["catalog"] == "my_catalog"


def test_datasource_schema_allows_none_catalog() -> None:
    schema = Datasource()
    result = schema.load(
        {
            "datasource_type": "table",
            "catalog": None,
        }
    )
    assert result["catalog"] is None


def test_datasource_schema_rejects_invalid_type() -> None:
    schema = Datasource()
    with pytest.raises(ValidationError) as exc_info:
        schema.load({"datasource_type": "invalid_type"})
    assert "datasource_type" in exc_info.value.messages


def test_datasource_schema_requires_datasource_type() -> None:
    schema = Datasource()
    with pytest.raises(ValidationError) as exc_info:
        schema.load({"database_name": "my_db"})
    assert "datasource_type" in exc_info.value.messages


def test_cache_invalidation_schema_with_uids() -> None:
    schema = CacheInvalidationRequestSchema()
    result = schema.load({"datasource_uids": ["uid1", "uid2"]})
    assert result["datasource_uids"] == ["uid1", "uid2"]


def test_cache_invalidation_schema_with_datasources() -> None:
    schema = CacheInvalidationRequestSchema()
    result = schema.load(
        {
            "datasources": [
                {
                    "database_name": "db1",
                    "datasource_name": "table1",
                    "schema": "public",
                    "datasource_type": "table",
                }
            ]
        }
    )
    assert len(result["datasources"]) == 1
    assert result["datasources"][0]["database_name"] == "db1"


def test_cache_invalidation_schema_with_both_uids_and_datasources() -> None:
    schema = CacheInvalidationRequestSchema()
    result = schema.load(
        {
            "datasource_uids": ["uid1"],
            "datasources": [
                {
                    "datasource_type": "table",
                    "datasource_name": "t1",
                    "database_name": "db1",
                    "schema": "public",
                }
            ],
        }
    )
    assert len(result["datasource_uids"]) == 1
    assert len(result["datasources"]) == 1


def test_cache_invalidation_schema_empty_payload() -> None:
    schema = CacheInvalidationRequestSchema()
    result = schema.load({})
    assert result == {}
