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

from unittest.mock import MagicMock, patch

from superset.sql_validators.postgres import PostgreSQLValidator


def test_postgres_validator_name() -> None:
    assert PostgreSQLValidator.name == "PostgreSQLValidator"


def test_postgres_validator_valid_sql() -> None:
    mock_database = MagicMock()
    with patch(
        "superset.sql_validators.postgres.check_string",
        return_value=(True, None),
    ):
        annotations = PostgreSQLValidator.validate(
            sql="SELECT 1",
            catalog=None,
            schema=None,
            database=mock_database,
        )
    assert annotations == []


def test_postgres_validator_invalid_sql_with_line_number() -> None:
    mock_database = MagicMock()
    with patch(
        "superset.sql_validators.postgres.check_string",
        return_value=(False, 'line 5: syntax error at or near "FORM"'),
    ):
        annotations = PostgreSQLValidator.validate(
            sql="SELECT * FORM my_table",
            catalog=None,
            schema=None,
            database=mock_database,
        )
    assert len(annotations) == 1
    assert annotations[0].line_number == 5
    assert annotations[0].message == 'syntax error at or near "FORM"'
    assert annotations[0].start_column is None
    assert annotations[0].end_column is None


def test_postgres_validator_invalid_sql_without_line_number() -> None:
    mock_database = MagicMock()
    with patch(
        "superset.sql_validators.postgres.check_string",
        return_value=(False, "unexpected end of input"),
    ):
        annotations = PostgreSQLValidator.validate(
            sql="SELECT",
            catalog=None,
            schema=None,
            database=mock_database,
        )
    assert len(annotations) == 1
    assert annotations[0].line_number is None
    assert annotations[0].message == "unexpected end of input"
