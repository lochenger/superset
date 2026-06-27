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

from superset.sql_validators import get_validator_by_name
from superset.sql_validators.postgres import PostgreSQLValidator
from superset.sql_validators.presto_db import PrestoDBSQLValidator
from superset.sql_validators.sqlite import SQLiteSQLValidator


def test_get_validator_by_name_presto() -> None:
    assert get_validator_by_name("PrestoDBSQLValidator") is PrestoDBSQLValidator


def test_get_validator_by_name_postgres() -> None:
    assert get_validator_by_name("PostgreSQLValidator") is PostgreSQLValidator


def test_get_validator_by_name_sqlite() -> None:
    assert get_validator_by_name("SQLiteSQLValidator") is SQLiteSQLValidator


def test_get_validator_by_name_unknown_returns_none() -> None:
    assert get_validator_by_name("NonExistentValidator") is None


def test_get_validator_by_name_empty_string_returns_none() -> None:
    assert get_validator_by_name("") is None
