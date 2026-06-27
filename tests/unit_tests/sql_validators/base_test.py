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

import pytest

from superset.sql_validators.base import BaseSQLValidator, SQLValidationAnnotation


def test_sql_validation_annotation_stores_fields() -> None:
    annotation = SQLValidationAnnotation(
        message="Syntax error near 'FROM'",
        line_number=3,
        start_column=5,
        end_column=9,
    )
    assert annotation.message == "Syntax error near 'FROM'"
    assert annotation.line_number == 3
    assert annotation.start_column == 5
    assert annotation.end_column == 9


def test_sql_validation_annotation_accepts_none_positions() -> None:
    annotation = SQLValidationAnnotation(
        message="Unknown error",
        line_number=None,
        start_column=None,
        end_column=None,
    )
    assert annotation.line_number is None
    assert annotation.start_column is None
    assert annotation.end_column is None


def test_sql_validation_annotation_to_dict() -> None:
    annotation = SQLValidationAnnotation(
        message="Missing semicolon",
        line_number=10,
        start_column=1,
        end_column=15,
    )
    result = annotation.to_dict()
    assert result == {
        "line_number": 10,
        "start_column": 1,
        "end_column": 15,
        "message": "Missing semicolon",
    }


def test_sql_validation_annotation_to_dict_with_none_values() -> None:
    annotation = SQLValidationAnnotation(
        message="Generic error",
        line_number=None,
        start_column=None,
        end_column=None,
    )
    result = annotation.to_dict()
    assert result == {
        "line_number": None,
        "start_column": None,
        "end_column": None,
        "message": "Generic error",
    }


def test_base_sql_validator_has_name() -> None:
    assert BaseSQLValidator.name == "BaseSQLValidator"


def test_base_sql_validator_validate_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        BaseSQLValidator.validate(
            sql="SELECT 1",
            catalog=None,
            schema=None,
            database=MagicMock(),
        )
