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

from superset.temporary_cache.utils import cache_key, SEPARATOR


def test_cache_key_single_arg() -> None:
    assert cache_key("dashboard") == "dashboard"


def test_cache_key_multiple_string_args() -> None:
    result = cache_key("dashboard", "123", "chart")
    assert result == f"dashboard{SEPARATOR}123{SEPARATOR}chart"


def test_cache_key_with_integers() -> None:
    result = cache_key("prefix", 42, 100)
    assert result == f"prefix{SEPARATOR}42{SEPARATOR}100"


def test_cache_key_with_none() -> None:
    result = cache_key("key", None)
    assert result == f"key{SEPARATOR}None"


def test_cache_key_empty_string_arg() -> None:
    result = cache_key("", "value")
    assert result == f"{SEPARATOR}value"


def test_cache_key_separator_is_semicolon() -> None:
    assert SEPARATOR == ";"
