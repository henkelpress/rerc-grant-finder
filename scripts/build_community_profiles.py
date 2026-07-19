#!/usr/bin/env python3
"""Build governed Census community profiles and a compact browser projection."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import tempfile
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SCHEMA_VERSION = "1.0.0"
DEFAULT_ENV_FILE = Path(r"C:\Users\hinkl\.env")
ACS_ENDPOINT = "https://api.census.gov/data/2024/acs/acs5/profile"
ISLAND_ENDPOINTS = {
    "dpas": {
        "state_fips": "60",
        "state_abbreviation": "AS",
        "state_name": "American Samoa",
    },
    "dpgu": {
        "state_fips": "66",
        "state_abbreviation": "GU",
        "state_name": "Guam",
    },
    "dpmp": {
        "state_fips": "69",
        "state_abbreviation": "MP",
        "state_name": "Northern Mariana Islands",
    },
    "dpvi": {
        "state_fips": "78",
        "state_abbreviation": "VI",
        "state_name": "U.S. Virgin Islands",
    },
}
ACS_STATES = {
    "01": ("AL", "Alabama"),
    "02": ("AK", "Alaska"),
    "04": ("AZ", "Arizona"),
    "05": ("AR", "Arkansas"),
    "06": ("CA", "California"),
    "08": ("CO", "Colorado"),
    "09": ("CT", "Connecticut"),
    "10": ("DE", "Delaware"),
    "11": ("DC", "District of Columbia"),
    "12": ("FL", "Florida"),
    "13": ("GA", "Georgia"),
    "15": ("HI", "Hawaii"),
    "16": ("ID", "Idaho"),
    "17": ("IL", "Illinois"),
    "18": ("IN", "Indiana"),
    "19": ("IA", "Iowa"),
    "20": ("KS", "Kansas"),
    "21": ("KY", "Kentucky"),
    "22": ("LA", "Louisiana"),
    "23": ("ME", "Maine"),
    "24": ("MD", "Maryland"),
    "25": ("MA", "Massachusetts"),
    "26": ("MI", "Michigan"),
    "27": ("MN", "Minnesota"),
    "28": ("MS", "Mississippi"),
    "29": ("MO", "Missouri"),
    "30": ("MT", "Montana"),
    "31": ("NE", "Nebraska"),
    "32": ("NV", "Nevada"),
    "33": ("NH", "New Hampshire"),
    "34": ("NJ", "New Jersey"),
    "35": ("NM", "New Mexico"),
    "36": ("NY", "New York"),
    "37": ("NC", "North Carolina"),
    "38": ("ND", "North Dakota"),
    "39": ("OH", "Ohio"),
    "40": ("OK", "Oklahoma"),
    "41": ("OR", "Oregon"),
    "42": ("PA", "Pennsylvania"),
    "44": ("RI", "Rhode Island"),
    "45": ("SC", "South Carolina"),
    "46": ("SD", "South Dakota"),
    "47": ("TN", "Tennessee"),
    "48": ("TX", "Texas"),
    "49": ("UT", "Utah"),
    "50": ("VT", "Vermont"),
    "51": ("VA", "Virginia"),
    "53": ("WA", "Washington"),
    "54": ("WV", "West Virginia"),
    "55": ("WI", "Wisconsin"),
    "56": ("WY", "Wyoming"),
    "72": ("PR", "Puerto Rico"),
}
ALL_STATES = {
    **ACS_STATES,
    **{
        details["state_fips"]: (
            details["state_abbreviation"],
            details["state_name"],
        )
        for details in ISLAND_ENDPOINTS.values()
    },
}
TERRITORY_FIPS = {"60", "66", "69", "72", "78"}

ACS_METRICS = {
    "population": {
        "estimate": "DP05_0001E",
        "margin": "DP05_0001M",
        "unit": "people",
    },
    "median_age": {
        "estimate": "DP05_0018E",
        "margin": "DP05_0018M",
        "unit": "years",
    },
    "median_household_income": {
        "estimate": "DP03_0062E",
        "margin": "DP03_0062M",
        "unit": "2024 inflation-adjusted dollars",
    },
    "poverty_rate": {
        "estimate": "DP03_0128PE",
        "margin": "DP03_0128PM",
        "unit": "percent",
    },
    "broadband_rate": {
        "estimate": "DP02_0154PE",
        "margin": "DP02_0154PM",
        "unit": "percent",
    },
}
METRIC_ORDER = tuple(ACS_METRICS)
SENTINEL_VALUES = {
    "-222222222": "estimate represents a lower-bound interval",
    "-333333333": "estimate represents an upper-bound interval",
    "-555555555": "controlled estimate",
    "-666666666": "estimate could not be computed",
    "-777777777": "estimate is not available",
    "-888888888": "margin of error could not be computed",
    "-999999999": "value is not available or not applicable",
    **{
        str(code): "value omitted because Census returned a documented negative special numeric code"
        for code in range(-9, 0)
    },
}
NUMERIC_TYPES = {"int", "float", "number"}
ISLAND_METRIC_CONTRACTS: dict[str, dict[str, Any]] = {
    "population": {
        "statistic_suffix": "C",
        "required_label_terms": ("total population",),
        "required_concept_terms": (
            "general demographic characteristics",
            "general population",
            "demographic profile",
            "sex and age",
        ),
        "forbidden_label_terms": (
            "percent",
            "male",
            "female",
            "median age",
            "household",
        ),
    },
    "median_age": {
        "statistic_suffix": "C",
        "required_label_terms": ("median age",),
        "required_concept_terms": (
            "general demographic characteristics",
            "general population",
            "demographic profile",
            "sex and age",
        ),
        "forbidden_label_terms": ("percent", "male", "female"),
    },
    "median_household_income": {
        "statistic_suffix": "C",
        "required_path_start": "number",
        "required_denominator_terms": ("households",),
        "required_leaf_terms": ("median household income", "dollars"),
        "required_concept_terms": ("economic", "income"),
        "forbidden_leaf_terms": ("mean household income", "per capita"),
    },
    "poverty_rate": {
        "statistic_suffix": "P",
        "required_variable": "DP3_0151P",
        "required_label_terms": ("percent",),
        "required_label_alternatives": (
            ("below poverty level", "below the poverty level"),
        ),
        "allowed_leaves": (
            "all individuals",
            "all individuals in households",
        ),
        "required_concept_terms": ("economic", "poverty"),
        "forbidden_leaf_terms": (
            "families",
            "family",
            "under",
            "years",
            "age",
        ),
    },
    "broadband_rate": {
        "statistic_suffix": "P",
        "predicate_types": ("float",),
        "required_path_start": "percent",
        "required_label_terms": ("broadband",),
        "required_denominator_terms": ("occupied housing units",),
        "required_leaf_terms": ("with a broadband internet subscription",),
        "required_concept_terms": ("housing",),
        "forbidden_leaf_terms": (
            "without",
            "no internet",
            "dial up",
            "computer only",
        ),
    },
}
GEOGRAPHY_TYPES = ("state", "county", "place", "county subdivision")
RETRYABLE_HTTP_CODES = {408, 425, 429, 500, 502, 503, 504}
ISLAND_OPTIONAL_SEMANTIC_QUALIFIERS = (
    "excluding people in military housing units",
    "excluding persons in military housing units",
    "excluding military housing units",
)


@dataclass(frozen=True)
class IslandMetric:
    estimate: str | None
    margin: str | None
    unit: str
    estimate_metadata: Mapping[str, Any] | None
    margin_metadata: Mapping[str, Any] | None
    selection_score: int | None


class BuildError(RuntimeError):
    """Raised when source coverage or output governance checks fail."""


def census_http_error_message(
    safe_url: str,
    error: HTTPError,
    api_key: str,
) -> str:
    try:
        body_bytes = error.read(4096)
    except Exception:
        body_bytes = b""
    body = body_bytes.decode("utf-8", errors="replace")
    if api_key:
        body = body.replace(api_key, "[REDACTED]")
    body = re.sub(
        r"(?i)([?&]key=)[^&\s\"']+",
        r"\1[REDACTED]",
        body,
    )
    body = " ".join(body.split())[:1000] or "(empty response body)"
    return (
        f"Census request failed (HTTP {error.code}); "
        f"url={safe_url}; body={body!r}"
    )


class CensusClient:
    def __init__(
        self,
        api_key: str,
        timeout_seconds: float,
        retries: int,
        backoff_seconds: float,
    ) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._retries = retries
        self._backoff_seconds = backoff_seconds

    def get_json(
        self,
        endpoint: str,
        parameters: Sequence[tuple[str, str]] = (),
    ) -> tuple[Any, str]:
        safe_query = urlencode(parameters)
        safe_url = f"{endpoint}?{safe_query}" if safe_query else endpoint
        keyed_parameters = [*parameters, ("key", self._api_key)]
        request_url = f"{endpoint}?{urlencode(keyed_parameters)}"
        request = Request(
            request_url,
            headers={
                "Accept": "application/json",
                "User-Agent": "RERC-community-profile-builder/1.0",
            },
        )

        for attempt in range(self._retries + 1):
            try:
                with urlopen(request, timeout=self._timeout_seconds) as response:
                    payload = response.read()
                try:
                    return json.loads(payload.decode("utf-8")), safe_url
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise BuildError(
                        f"Census returned invalid JSON for {endpoint}"
                    ) from exc
            except HTTPError as exc:
                if exc.code not in RETRYABLE_HTTP_CODES or attempt >= self._retries:
                    raise BuildError(
                        census_http_error_message(safe_url, exc, self._api_key)
                    ) from None
            except (TimeoutError, URLError) as exc:
                if attempt >= self._retries:
                    reason = type(getattr(exc, "reason", exc)).__name__
                    raise BuildError(
                        f"Census request failed for {endpoint} ({reason})"
                    ) from None

            delay = self._backoff_seconds * (2**attempt)
            time.sleep(min(delay, 8.0))

        raise AssertionError("retry loop exited unexpectedly")

    def get_table(
        self,
        endpoint: str,
        variables: Sequence[str],
        geography_parameters: Sequence[tuple[str, str]],
    ) -> tuple[list[dict[str, str]], str]:
        parameters = [
            ("get", ",".join(("NAME", *variables))),
            *geography_parameters,
        ]
        payload, safe_url = self.get_json(endpoint, parameters)
        if not isinstance(payload, list) or len(payload) < 2:
            raise BuildError(f"Census returned no rows for {safe_url}")
        headers = payload[0]
        if not isinstance(headers, list) or len(headers) != len(set(headers)):
            raise BuildError(f"Census returned invalid headers for {safe_url}")
        rows: list[dict[str, str]] = []
        for row_number, row in enumerate(payload[1:], start=2):
            if not isinstance(row, list) or len(row) != len(headers):
                raise BuildError(
                    f"Census row {row_number} has the wrong width for {safe_url}"
                )
            rows.append(dict(zip(headers, row)))
        return rows, safe_url


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build governed U.S. Census community profiles and a bounded "
            "window.RERC_COMMUNITY_PROFILES browser projection."
        )
    )
    parser.add_argument(
        "--castle-output",
        type=Path,
        help="Directory for governed source JSON and metadata JSON.",
    )
    parser.add_argument(
        "--site-output",
        type=Path,
        help="Destination .js file for the compact browser projection.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Per-request timeout in seconds (default: 60).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=4,
        help="Retry count for transient Census failures (default: 4).",
    )
    parser.add_argument(
        "--backoff",
        type=float,
        default=0.75,
        help="Initial retry backoff in seconds (default: 0.75).",
    )
    parser.add_argument(
        "--max-browser-records",
        type=int,
        default=50_000,
        help="Fail if the browser projection exceeds this record count.",
    )
    parser.add_argument(
        "--max-browser-bytes",
        type=int,
        default=20_000_000,
        help="Fail if the browser projection exceeds this UTF-8 byte size.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run network-free metadata and planner-schema regression tests.",
    )
    parser.add_argument(
        "--generated-at",
        help=(
            "Optional ISO-8601 UTC timestamp for reproducible builds. "
            "Defaults to the current UTC time."
        ),
    )
    args = parser.parse_args()
    if args.self_test:
        return args
    if args.castle_output is None:
        parser.error("--castle-output is required unless --self-test is used")
    if args.site_output is None:
        parser.error("--site-output is required unless --self-test is used")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    if args.retries < 0 or args.retries > 8:
        parser.error("--retries must be between 0 and 8")
    if args.backoff < 0 or args.backoff > 10:
        parser.error("--backoff must be between 0 and 10")
    if args.max_browser_records <= 0 or args.max_browser_bytes <= 0:
        parser.error("browser projection limits must be greater than zero")
    if args.site_output.suffix.lower() != ".js":
        parser.error("--site-output must be a .js file")
    return args


def read_env_value(path: Path, name: str) -> str:
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise BuildError(f"Could not read required environment file: {path}") from exc

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() != name:
            continue
        value = value.strip()
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
        ):
            value = value[1:-1]
        if not value:
            break
        return value
    raise BuildError(f"{name} is missing or empty in {path}")


def generated_timestamp(value: str | None) -> str:
    if value:
        candidate = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError as exc:
            raise BuildError("--generated-at must be a valid ISO-8601 timestamp") from exc
        if parsed.tzinfo is None:
            raise BuildError("--generated-at must include a timezone")
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", ascii_text.casefold()).split())


def lookup_keys(
    name: str,
    state_fips: str,
    geography_type: str,
    geoid: str,
) -> list[str]:
    state_abbreviation, state_name = ALL_STATES[state_fips]
    candidates = (
        normalize_text(name),
        normalize_text(f"{name} {state_abbreviation}"),
        normalize_text(f"{name} {state_name}"),
        normalize_text(f"{name} {geography_type} {state_abbreviation}"),
        f"geoid {geoid}",
    )
    keys = list(dict.fromkeys(key for key in candidates if key))
    if len(keys) != len(set(keys)):
        raise BuildError(f"Duplicate normalized lookup key for {name}")
    return keys


def contextual_error(message: str, context: str = "") -> BuildError:
    return BuildError(f"{message} [{context}]" if context else message)


def parse_number(
    raw_value: Any,
    metric_name: str,
    *,
    integer: bool = False,
    context: str = "",
) -> tuple[int | float | None, str | None]:
    if raw_value is None:
        return None, "value is missing"
    text = str(raw_value).strip()
    if not text or text.lower() in {"null", "none", "nan"}:
        return None, "value is missing"
    try:
        value = float(text.replace(",", ""))
    except ValueError as exc:
        raise contextual_error(
            f"{metric_name} contains a nonnumeric value",
            context,
        ) from exc
    if not math.isfinite(value):
        raise contextual_error(
            f"{metric_name} contains a non-finite value",
            context,
        )
    if value.is_integer():
        sentinel_note = SENTINEL_VALUES.get(str(int(value)))
        if sentinel_note:
            return None, sentinel_note
    if value <= -100_000_000:
        return (
            None,
            "value omitted because Census returned an unrecognized special numeric code",
        )
    if integer:
        if not value.is_integer():
            raise contextual_error(
                f"{metric_name} must be a whole number",
                context,
            )
        return int(value), None
    return value, None


def validate_metric_range(
    metric_name: str,
    value: int | float | None,
    *,
    context: str = "",
) -> None:
    if value is None:
        return
    if metric_name == "population" and value < 0:
        raise contextual_error("Population cannot be negative", context)
    if metric_name == "median_age" and not 0 <= value <= 120:
        raise contextual_error("Median age is outside the accepted range", context)
    if metric_name == "median_household_income" and value < 0:
        raise contextual_error("Median household income cannot be negative", context)
    if metric_name in {"poverty_rate", "broadband_rate"} and not 0 <= value <= 100:
        raise contextual_error(
            f"{metric_name} must be between 0 and 100",
            context,
        )

def variable_metadata(payload: Any, endpoint: str) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("variables"), dict):
        raise BuildError(f"Census returned invalid variable metadata for {endpoint}")
    result: dict[str, dict[str, Any]] = {}
    for raw_name, details in payload["variables"].items():
        if not isinstance(details, dict):
            continue
        name = str(raw_name).strip().upper()
        if not name:
            continue
        if name in result and result[name] != details:
            raise BuildError(
                f"Census returned conflicting metadata for variable {name}"
            )
        result[name] = dict(details)
    return result


def merge_variable_metadata(
    base: dict[str, dict[str, Any]],
    additional: Mapping[str, Mapping[str, Any]],
) -> None:
    for name, details in additional.items():
        if name in base:
            base[name] = {**base[name], **dict(details)}
        else:
            base[name] = dict(details)


def geography_metadata(payload: Any, endpoint: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("fips"), list):
        raise BuildError(f"Census returned invalid geography metadata for {endpoint}")
    return [dict(item) for item in payload["fips"] if isinstance(item, dict)]


def variable_label(details: Mapping[str, Any]) -> str:
    return str(details.get("label") or "")


def variable_concept(details: Mapping[str, Any]) -> str:
    return str(details.get("concept") or "")


def variable_label_path(details: Mapping[str, Any]) -> list[str]:
    return [
        normalized
        for segment in variable_label(details).split("!!")
        if (normalized := normalize_text(segment))
    ]


def island_semantic_label_path(details: Mapping[str, Any]) -> list[str]:
    result: list[str] = []
    for segment in variable_label_path(details):
        cleaned = segment
        for qualifier in ISLAND_OPTIONAL_SEMANTIC_QUALIFIERS:
            cleaned = cleaned.replace(qualifier, " ")
        cleaned = normalize_text(cleaned)
        if cleaned:
            result.append(cleaned)
    return result


def is_numeric_variable(name: str, details: Mapping[str, Any]) -> bool:
    label = normalize_text(variable_label(details))
    predicate_type = str(details.get("predicateType") or "").casefold()
    if "annotation" in label or name.endswith(("A", "EA", "MA")):
        return False
    if predicate_type and predicate_type not in NUMERIC_TYPES:
        return False
    return name not in {"NAME", "GEO_ID"}


def is_queryable_variable(details: Mapping[str, Any]) -> bool:
    # Census profile metadata commonly marks retrievable data variables as
    # predicateOnly=true. Presence in the dataset metadata, not that flag,
    # determines whether the builder may request the variable.
    return bool(details)


def island_metric_contract_errors(
    metric_name: str,
    name: str,
    details: Mapping[str, Any],
) -> list[str]:
    contract = ISLAND_METRIC_CONTRACTS[metric_name]
    label = normalize_text(variable_label(details))
    semantic_label_path = island_semantic_label_path(details)
    leaf = semantic_label_path[-1] if semantic_label_path else ""
    concept = normalize_text(variable_concept(details))
    predicate_type = str(details.get("predicateType") or "").casefold()
    errors: list[str] = []

    if not label:
        errors.append("metadata label is empty")
    if not concept:
        errors.append("metadata concept is empty")
    if predicate_type not in NUMERIC_TYPES:
        errors.append(
            f"predicateType must be numeric, not {predicate_type or '(missing)'}"
        )
    allowed_predicate_types = contract.get("predicate_types", ())
    if allowed_predicate_types and predicate_type not in allowed_predicate_types:
        errors.append(
            "predicateType must be one of "
            + ", ".join(repr(value) for value in allowed_predicate_types)
        )
    if "annotation" in label or "margin of error" in label:
        errors.append("variable is an annotation or margin, not an estimate")

    expected_suffix = str(contract["statistic_suffix"])
    if not name.endswith(expected_suffix):
        statistic = "percent" if expected_suffix == "P" else "count/value"
        errors.append(
            f"{statistic} variable must use the {expected_suffix} statistic suffix"
        )

    required_variable = contract.get("required_variable")
    if required_variable and name != required_variable:
        errors.append(f"variable must be {required_variable}")

    for term in contract.get("required_label_terms", ()):
        if term not in label:
            errors.append(f"label is missing required term {term!r}")
    required_path_start = contract.get("required_path_start")
    if required_path_start and (
        not semantic_label_path
        or semantic_label_path[0] != required_path_start
    ):
        errors.append(f"label path must start with {required_path_start!r}")
    denominator_path = semantic_label_path[1:-1]
    for term in contract.get("required_denominator_terms", ()):
        if not any(term in segment for segment in denominator_path):
            errors.append(f"label denominator is missing required term {term!r}")
    for alternatives in contract.get("required_label_alternatives", ()):
        if not any(term in label for term in alternatives):
            errors.append(
                "label is missing one of "
                + ", ".join(repr(term) for term in alternatives)
            )
    for term in contract.get("forbidden_label_terms", ()):
        if term in label:
            errors.append(f"label contains incompatible term {term!r}")
    for term in contract.get("required_leaf_terms", ()):
        if term not in leaf:
            errors.append(f"label leaf is missing required term {term!r}")
    allowed_leaves = contract.get("allowed_leaves", ())
    if allowed_leaves and leaf not in allowed_leaves:
        errors.append(
            "label leaf must exactly match one of "
            + ", ".join(repr(value) for value in allowed_leaves)
        )
    for term in contract.get("forbidden_leaf_terms", ()):
        if term in leaf:
            errors.append(f"label leaf contains incompatible term {term!r}")

    expected_concepts = contract.get("required_concept_terms", ())
    if expected_concepts and not any(term in concept for term in expected_concepts):
        errors.append(
            "concept does not match expected subject: "
            + ", ".join(repr(term) for term in expected_concepts)
        )
    return errors


def island_metric_cross_endpoint_signature(
    metric_name: str,
    details: Mapping[str, Any],
) -> str:
    label_path = island_semantic_label_path(details)
    if metric_name == "poverty_rate" and label_path:
        label_path[-1] = "all individuals"
    if metric_name != "broadband_rate":
        return " | ".join(label_path)
    leaf = label_path[-1] if label_path else ""
    return " | ".join(("percent", "occupied housing units", leaf, "housing"))


def island_metric_score(
    metric_name: str,
    name: str,
    details: Mapping[str, Any],
) -> int | None:
    if island_metric_contract_errors(metric_name, name, details):
        return None
    label = normalize_text(variable_label(details))
    concept = normalize_text(variable_concept(details))
    text = f"{label} {concept}"
    if "margin of error" in label:
        return None

    if metric_name == "population":
        if "total population" not in label:
            return None
        score = 120
        if label.endswith("total population"):
            score += 40
        if any(term in label for term in ("percent", "male", "female", "household")):
            score -= 90
        return score

    if metric_name == "median_age":
        if "median age" not in label:
            return None
        score = 130
        if "both sexes" in text or "total population" in text:
            score += 30
        if "male" in label or "female" in label:
            score -= 50
        return score

    if metric_name == "median_household_income":
        if "median household income" not in label:
            return None
        score = 160
        if "dollar" in text:
            score += 10
        if "mean" in label:
            score -= 120
        return score

    if metric_name == "poverty_rate":
        return 220

    if metric_name == "broadband_rate":
        if "broadband" not in text or "percent" not in label:
            return None
        score = 150
        if "internet subscription" in text:
            score += 30
        if "total households" in label:
            score += 20
        if "device" in label and "subscription" not in label:
            score -= 80
        return score

    raise AssertionError(f"Unknown metric: {metric_name}")


def compact_variable_details(
    name: str,
    details: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if details is None:
        return None
    return {
        "name": name,
        "label": variable_label(details),
        "concept": variable_concept(details),
        "predicate_type": details.get("predicateType"),
        "group": details.get("group"),
    }


def label_without_statistic(details: Mapping[str, Any]) -> str:
    label = normalize_text(variable_label(details))
    for prefix in (
        "estimate ",
        "percent ",
        "number ",
        "margin of error ",
    ):
        if label.startswith(prefix):
            label = label[len(prefix) :]
    return label


def find_margin_variable(
    estimate_name: str,
    estimate_details: Mapping[str, Any],
    variables: Mapping[str, Mapping[str, Any]],
) -> tuple[str | None, Mapping[str, Any] | None]:
    conventional_names: list[str] = []
    if estimate_name.endswith("PE"):
        conventional_names.append(f"{estimate_name[:-2]}PM")
    if estimate_name.endswith("E"):
        conventional_names.append(f"{estimate_name[:-1]}M")
    for name in conventional_names:
        details = variables.get(name)
        if details is not None and is_queryable_variable(details):
            return name, details

    target = label_without_statistic(estimate_details)
    candidates: list[tuple[str, Mapping[str, Any]]] = []
    for name, details in variables.items():
        label = normalize_text(variable_label(details))
        if "margin of error" not in label:
            continue
        if not is_queryable_variable(details):
            continue
        if label_without_statistic(details) == target:
            candidates.append((name, details))
    if not candidates:
        return None, None
    candidates.sort(key=lambda item: item[0])
    return candidates[0]


def discover_island_metrics(
    variables: Mapping[str, Mapping[str, Any]],
    endpoint_name: str,
) -> dict[str, IslandMetric]:
    units = {
        "population": "people",
        "median_age": "years",
        "median_household_income": "nominal dollars reported by the 2020 source",
        "poverty_rate": "percent",
        "broadband_rate": "percent",
    }
    discovered: dict[str, IslandMetric] = {}
    for metric_name in METRIC_ORDER:
        candidates: list[tuple[int, str, Mapping[str, Any]]] = []
        for variable_name, details in variables.items():
            score = island_metric_score(metric_name, variable_name, details)
            if score is not None:
                candidates.append((score, variable_name, details))
        candidates.sort(key=lambda item: (-item[0], item[1]))
        if not candidates:
            contract = ISLAND_METRIC_CONTRACTS[metric_name]
            required_name = contract.get("required_variable")
            detail = ""
            if required_name and required_name in variables:
                required_details = variables[required_name]
                reasons = island_metric_contract_errors(
                    metric_name,
                    required_name,
                    required_details,
                )
                detail = (
                    f"; {required_name} label={variable_label(required_details)!r}, "
                    f"concept={variable_concept(required_details)!r}, "
                    f"predicateType={required_details.get('predicateType')!r}, "
                    f"errors={reasons!r}"
                )
            elif required_name:
                detail = f"; required variable {required_name} is absent"
            raise BuildError(
                f"Could not discover a semantically valid {metric_name} "
                f"variable for {endpoint_name}{detail}"
            )
        score, estimate_name, estimate_details = candidates[0]
        semantic_errors = island_metric_contract_errors(
            metric_name,
            estimate_name,
            estimate_details,
        )
        if semantic_errors:
            raise BuildError(
                f"Invalid Island Areas mapping for {endpoint_name} "
                f"{metric_name}: variable={estimate_name}, "
                f"label={variable_label(estimate_details)!r}, "
                f"concept={variable_concept(estimate_details)!r}, "
                f"predicateType={estimate_details.get('predicateType')!r}, "
                f"errors={semantic_errors!r}"
            )
        margin_name, margin_details = find_margin_variable(
            estimate_name, estimate_details, variables
        )
        discovered[metric_name] = IslandMetric(
            estimate=estimate_name,
            margin=margin_name,
            unit=units[metric_name],
            estimate_metadata=estimate_details,
            margin_metadata=margin_details,
            selection_score=score,
        )
    return discovered


def metric_value_context(
    metric_name: str,
    variable_name: str | None,
    raw_value: Any,
    geography_context: Mapping[str, Any] | None,
) -> str:
    parts = [
        f"metric={metric_name}",
        f"variable={variable_name or '(none)'}",
        f"value={raw_value!r}",
    ]
    if geography_context:
        for field in (
            "source_id",
            "geography_type",
            "geoid",
            "state_fips",
            "name",
        ):
            value = geography_context.get(field)
            if value not in {None, ""}:
                parts.append(f"{field}={value!r}")
    return "; ".join(parts)


def build_metric_values(
    row: Mapping[str, Any],
    metric_definitions: Mapping[str, Mapping[str, Any]],
    *,
    geography_context: Mapping[str, Any] | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]]]:
    metrics: dict[str, dict[str, Any]] = {}
    notes = {"margin": [], "suppression": [], "coverage": []}
    for metric_name in METRIC_ORDER:
        definition = metric_definitions[metric_name]
        estimate_variable = definition.get("estimate")
        margin_variable = definition.get("margin")
        integer = metric_name == "population"

        if estimate_variable is None:
            value = None
            value_note = None
            notes["coverage"].append(f"{metric_name}: not available in this source")
        else:
            raw_estimate = row.get(str(estimate_variable))
            estimate_context = metric_value_context(
                metric_name,
                str(estimate_variable),
                raw_estimate,
                geography_context,
            )
            value, value_note = parse_number(
                raw_estimate,
                metric_name,
                integer=integer,
                context=estimate_context,
            )
            if value_note:
                notes["suppression"].append(f"{metric_name}: {value_note}")
            validate_metric_range(
                metric_name,
                value,
                context=estimate_context,
            )

        margin: int | float | None = None
        if margin_variable is None:
            notes["margin"].append(f"{metric_name}: margin of error not published")
        else:
            raw_margin = row.get(str(margin_variable))
            margin_context = metric_value_context(
                f"{metric_name} margin of error",
                str(margin_variable),
                raw_margin,
                geography_context,
            )
            margin, margin_note = parse_number(
                raw_margin,
                f"{metric_name} margin of error",
                integer=integer,
                context=margin_context,
            )
            if margin_note:
                notes["margin"].append(f"{metric_name}: {margin_note}")
            if margin is not None and margin < 0:
                raise contextual_error(
                    f"{metric_name} margin of error cannot be negative",
                    margin_context,
                )

        metrics[metric_name] = {
            "value": value,
            "margin_of_error": margin,
            "unit": definition["unit"],
            "estimate_variable": estimate_variable,
            "margin_variable": margin_variable,
        }
    return metrics, notes

def make_profile(
    *,
    row: Mapping[str, Any],
    geography_type: str,
    geoid: str,
    state_fips: str,
    source_id: str,
    source_url: str,
    source_vintage: str,
    generated_at: str,
    metric_definitions: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if state_fips not in ALL_STATES:
        raise BuildError(f"Unexpected state or territory code: {state_fips}")
    name = str(row.get("NAME") or "").strip()
    if not name:
        raise BuildError(f"Missing NAME for {geography_type} GEOID {geoid}")
    state_abbreviation, state_name = ALL_STATES[state_fips]
    metrics, notes = build_metric_values(
        row,
        metric_definitions,
        geography_context={
            "source_id": source_id,
            "geography_type": geography_type.replace(" ", "_"),
            "geoid": geoid,
            "state_fips": state_fips,
            "name": name,
        },
    )
    profile_id = f"us:{geography_type.replace(' ', '_')}:{geoid}"
    return {
        "profile_id": profile_id,
        "name": name,
        "lookup_keys": lookup_keys(name, state_fips, geography_type, geoid),
        "geoid": geoid,
        "geography_type": geography_type.replace(" ", "_"),
        "state_fips": state_fips,
        "state_abbreviation": state_abbreviation,
        "state_name": state_name,
        "is_territory": state_fips in TERRITORY_FIPS,
        "metrics": metrics,
        "notes": notes,
        "source_id": source_id,
        "source_url": source_url,
        "vintage": source_vintage,
        "generated_at": generated_at,
        "schema_version": SCHEMA_VERSION,
    }


def acs_metric_definitions(
    variables: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    definitions: dict[str, dict[str, Any]] = {}
    missing_estimates: list[str] = []
    for metric_name, configured in ACS_METRICS.items():
        estimate_name = configured["estimate"]
        estimate_details = variables.get(estimate_name)
        if estimate_details is None or not is_queryable_variable(estimate_details):
            missing_estimates.append(estimate_name)
            continue
        margin_name, _ = find_margin_variable(
            estimate_name,
            estimate_details,
            variables,
        )
        definitions[metric_name] = {
            "estimate": estimate_name,
            "margin": margin_name,
            "preferred_margin": configured["margin"],
            "unit": configured["unit"],
        }
    if missing_estimates:
        raise BuildError(
            "ACS metadata is missing required estimate variables: "
            f"{', '.join(sorted(missing_estimates))}"
        )
    return definitions


def load_acs_variable_metadata(
    client: CensusClient,
) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    metadata_payload, metadata_url = client.get_json(
        f"{ACS_ENDPOINT}/variables.json"
    )
    variables = variable_metadata(metadata_payload, ACS_ENDPOINT)
    metadata_urls = [metadata_url]
    metadata_notes: list[str] = []
    configured_names = {
        code
        for details in ACS_METRICS.values()
        for code in (details["estimate"], details["margin"])
    }
    missing_names = configured_names - set(variables)
    missing_groups = sorted(name.split("_", 1)[0] for name in missing_names)
    for group in dict.fromkeys(missing_groups):
        group_endpoint = f"{ACS_ENDPOINT}/groups/{group}.json"
        try:
            group_payload, group_url = client.get_json(group_endpoint)
            group_variables = variable_metadata(group_payload, group_endpoint)
        except BuildError as exc:
            metadata_notes.append(
                f"{group}: group metadata fallback was unavailable ({exc})"
            )
            continue
        merge_variable_metadata(variables, group_variables)
        metadata_urls.append(group_url)
    return variables, metadata_urls, metadata_notes


def acs_requested_variables(
    metric_definitions: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    return list(
        dict.fromkeys(
            code
            for metric_name in METRIC_ORDER
            for code in (
                metric_definitions[metric_name]["estimate"],
                metric_definitions[metric_name]["margin"],
            )
            if code is not None
        )
    )


def build_acs_profiles(
    client: CensusClient,
    generated_at: str,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    variables, metadata_urls, metadata_notes = load_acs_variable_metadata(client)
    metric_definitions = acs_metric_definitions(variables)
    for metric_name, details in metric_definitions.items():
        if details["margin"] is None:
            metadata_notes.append(
                f"{metric_name}: preferred margin variable "
                f"{details['preferred_margin']} was not available and was "
                "omitted from Census data queries"
            )
    profiles: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []
    geography_queries = {
        "state": [("for", "state:*")],
        "county": [("for", "county:*"), ("in", "state:*")],
        "place": [("for", "place:*"), ("in", "state:*")],
    }
    requested_variables = acs_requested_variables(metric_definitions)
    for geography_type, geography_parameters in geography_queries.items():
        rows, source_url = client.get_table(
            ACS_ENDPOINT,
            requested_variables,
            geography_parameters,
        )
        queries.append(
            {
                "geography_type": geography_type,
                "source_url": source_url,
                "row_count": len(rows),
            }
        )
        for row in rows:
            state_fips = str(row.get("state") or "")
            if state_fips not in ACS_STATES:
                raise BuildError(
                    f"ACS returned unexpected state code {state_fips or '(blank)'}"
                )
            if geography_type == "state":
                geoid = state_fips
            elif geography_type == "county":
                county = str(row.get("county") or "")
                if not re.fullmatch(r"\d{3}", county):
                    raise BuildError("ACS county row has an invalid county code")
                geoid = f"{state_fips}{county}"
            else:
                place = str(row.get("place") or "")
                if not re.fullmatch(r"\d{5}", place):
                    raise BuildError("ACS place row has an invalid place code")
                geoid = f"{state_fips}{place}"
            profiles.append(
                make_profile(
                    row=row,
                    geography_type=geography_type,
                    geoid=geoid,
                    state_fips=state_fips,
                    source_id="acs_2024_5yr_profile",
                    source_url=source_url,
                    source_vintage="2024 ACS 5-year Data Profiles",
                    generated_at=generated_at,
                    metric_definitions=metric_definitions,
                )
            )

    state_codes = {
        profile["state_fips"]
        for profile in profiles
        if profile["geography_type"] == "state"
    }
    if state_codes != set(ACS_STATES):
        missing_states = sorted(set(ACS_STATES) - state_codes)
        unexpected_states = sorted(state_codes - set(ACS_STATES))
        raise BuildError(
            "ACS state coverage mismatch; "
            f"missing={missing_states}, unexpected={unexpected_states}"
        )
    state_count = sum(
        profile["geography_type"] == "state" for profile in profiles
    )
    if state_count != len(ACS_STATES):
        raise BuildError(
            f"ACS state output count must be {len(ACS_STATES)}, got {state_count}"
        )

    source_metadata = {
        "source_id": "acs_2024_5yr_profile",
        "title": "2024 ACS 5-year Data Profiles",
        "publisher": "U.S. Census Bureau",
        "vintage": "2024",
        "dataset_url": ACS_ENDPOINT,
        "variables_metadata_urls": metadata_urls,
        "metadata_notes": metadata_notes,
        "confidence_level": (
            "Published ACS margins of error use a 90 percent confidence level."
        ),
        "geographic_coverage": (
            "All 50 states, the District of Columbia, and Puerto Rico; "
            "state, county, and place geographies."
        ),
        "use_constraints": (
            "Public statistical estimates. Review margins of error, suppression "
            "notes, source definitions, and current Census guidance before use."
        ),
        "public_claim_limit": (
            "Planning and screening use only; not a determination of grant "
            "eligibility or a substitute for current program rules."
        ),
        "variables": {
            metric_name: {
                "estimate": compact_variable_details(
                    details["estimate"], variables[details["estimate"]]
                ),
                "margin": compact_variable_details(
                    details["margin"],
                    variables.get(details["margin"])
                    if details["margin"] is not None
                    else None,
                )
                if details["margin"] is not None
                else None,
                "preferred_margin_variable": details["preferred_margin"],
                "unit": details["unit"],
            }
            for metric_name, details in metric_definitions.items()
        },
    }
    return profiles, source_metadata, queries


def available_island_geographies(
    entries: Iterable[Mapping[str, Any]],
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for entry in entries:
        name = str(entry.get("name") or "").strip().casefold()
        if name not in {"state", "place", "county subdivision"}:
            continue
        raw_requires = entry.get("requires") or []
        if not isinstance(raw_requires, list):
            raise BuildError(f"Invalid geography requires metadata for {name}")
        requires = [str(value).strip().casefold() for value in raw_requires]
        result.setdefault(name, requires)
    if "state" not in result:
        raise BuildError("Island Areas geography metadata does not expose state")
    return result


def geography_parameters(
    geography_type: str,
    requirements: Sequence[str],
    state_fips: str,
) -> list[tuple[str, str]]:
    if not re.fullmatch(r"\d{2}", state_fips):
        raise BuildError(f"Invalid Island Areas state FIPS: {state_fips!r}")
    parameters = [("for", f"{geography_type}:*")]
    unique_requirements = set(requirements)
    unsupported = unique_requirements - {"state", "county"}
    if unsupported:
        requirement = sorted(unsupported)[0]
        raise BuildError(
            f"Unsupported Island Areas geography requirement: {requirement}"
        )
    for requirement in ("state", "county"):
        if requirement not in unique_requirements:
            continue
        value = state_fips if requirement == "state" else "*"
        parameters.append(("in", f"{requirement}:{value}"))
    return parameters


def island_geoid(
    row: Mapping[str, Any],
    geography_type: str,
    expected_state_fips: str,
) -> str:
    state_fips = str(row.get("state") or "")
    if state_fips != expected_state_fips:
        raise BuildError(
            f"Island Areas endpoint returned state {state_fips or '(blank)'}; "
            f"expected {expected_state_fips}"
        )
    if geography_type == "state":
        return state_fips
    if geography_type == "place":
        place = str(row.get("place") or "")
        if not re.fullmatch(r"\d{5}", place):
            raise BuildError("Island Areas place row has an invalid place code")
        return f"{state_fips}{place}"
    county = str(row.get("county") or "")
    subdivision = str(row.get("county subdivision") or "")
    if not re.fullmatch(r"\d{3}", county):
        raise BuildError(
            "Island Areas county-subdivision row has an invalid county code"
        )
    if not re.fullmatch(r"\d{5}", subdivision):
        raise BuildError(
            "Island Areas county-subdivision row has an invalid subdivision code"
        )
    return f"{state_fips}{county}{subdivision}"


def build_island_profiles(
    client: CensusClient,
    generated_at: str,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[str],
]:
    profiles: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []
    coverage_notes: list[str] = []
    canonical_metric_labels: dict[str, tuple[str, str]] = {}

    for endpoint_name, territory in ISLAND_ENDPOINTS.items():
        endpoint = f"https://api.census.gov/data/2020/dec/{endpoint_name}"
        variables_payload, variables_url = client.get_json(
            f"{endpoint}/variables.json"
        )
        geographies_payload, geographies_url = client.get_json(
            f"{endpoint}/geography.json"
        )
        variables = variable_metadata(variables_payload, endpoint)
        geographies = geography_metadata(geographies_payload, endpoint)
        discovered = discover_island_metrics(variables, endpoint_name)
        for metric_name, metric in discovered.items():
            if metric.estimate_metadata is None:
                raise BuildError(
                    f"{endpoint_name} has no metadata for selected {metric_name}"
                )
            semantic_signature = island_metric_cross_endpoint_signature(
                metric_name,
                metric.estimate_metadata,
            )
            prior = canonical_metric_labels.get(metric_name)
            if prior is None:
                canonical_metric_labels[metric_name] = (
                    endpoint_name,
                    semantic_signature,
                )
            elif semantic_signature != prior[1]:
                raise BuildError(
                    "Island Areas metric semantics are inconsistent across endpoints: "
                    f"metric={metric_name}, first_endpoint={prior[0]}, "
                    f"first_signature={prior[1]!r}, endpoint={endpoint_name}, "
                    f"signature={semantic_signature!r}"
                )
        available_geographies = available_island_geographies(geographies)

        metric_definitions = {
            metric_name: {
                "estimate": metric.estimate,
                "margin": metric.margin,
                "unit": metric.unit,
            }
            for metric_name, metric in discovered.items()
        }
        requested_variables = list(
            dict.fromkeys(
                variable
                for metric in discovered.values()
                for variable in (metric.estimate, metric.margin)
                if variable is not None
            )
        )

        endpoint_geography_counts: dict[str, int] = {}
        for geography_type in ("state", "place", "county subdivision"):
            if geography_type not in available_geographies:
                if geography_type != "state":
                    coverage_notes.append(
                        f"{endpoint_name}: {geography_type} is not available "
                        "in endpoint geography metadata"
                    )
                continue
            parameters = geography_parameters(
                geography_type,
                available_geographies[geography_type],
                territory["state_fips"],
            )
            rows, source_url = client.get_table(
                endpoint,
                requested_variables,
                parameters,
            )
            endpoint_geography_counts[geography_type.replace(" ", "_")] = len(rows)
            queries.append(
                {
                    "source_id": f"island_areas_2020_{endpoint_name}",
                    "geography_type": geography_type.replace(" ", "_"),
                    "source_url": source_url,
                    "row_count": len(rows),
                }
            )
            for row in rows:
                state_fips = str(row.get("state") or "")
                geoid = island_geoid(
                    row,
                    geography_type,
                    territory["state_fips"],
                )
                profiles.append(
                    make_profile(
                        row=row,
                        geography_type=geography_type,
                        geoid=geoid,
                        state_fips=state_fips,
                        source_id=f"island_areas_2020_{endpoint_name}",
                        source_url=source_url,
                        source_vintage="2020 Island Areas Demographic Profile",
                        generated_at=generated_at,
                        metric_definitions=metric_definitions,
                    )
                )

        if endpoint_geography_counts.get("state") != 1:
            raise BuildError(
                f"{endpoint_name} must produce exactly one state profile"
            )
        sources.append(
            {
                "source_id": f"island_areas_2020_{endpoint_name}",
                "title": (
                    "2020 Island Areas Demographic Profile: "
                    f"{territory['state_name']}"
                ),
                "publisher": "U.S. Census Bureau",
                "vintage": "2020",
                "dataset_url": endpoint,
                "variables_metadata_url": variables_url,
                "geographies_metadata_url": geographies_url,
                "geographic_coverage": {
                    "state_fips": territory["state_fips"],
                    "state_name": territory["state_name"],
                    "available_geographies": sorted(
                        geography.replace(" ", "_")
                        for geography in available_geographies
                    ),
                    "output_counts": endpoint_geography_counts,
                },
                "variable_discovery_method": (
                    "Estimate variables are selected deterministically from "
                    "endpoint variable labels, concepts, predicate types, and "
                    "metric-specific statistic contracts. Count/value variables "
                    "must use the C suffix and rates must use the P suffix. "
                    "Poverty additionally requires metadata-confirmed DP3_0151P. "
                    "Variable names are not assumed to match ACS."
                ),
                "variables": {
                    metric_name: {
                        "estimate": compact_variable_details(
                            metric.estimate,
                            metric.estimate_metadata,
                        )
                        if metric.estimate
                        else None,
                        "margin": compact_variable_details(
                            metric.margin,
                            metric.margin_metadata,
                        )
                        if metric.margin
                        else None,
                        "selection_score": metric.selection_score,
                        "semantic_contract": {
                            "status": "passed",
                            "statistic_suffix": ISLAND_METRIC_CONTRACTS[
                                metric_name
                            ]["statistic_suffix"],
                        },
                        "unit": metric.unit,
                    }
                    for metric_name, metric in discovered.items()
                },
                "use_constraints": (
                    "Public Island Areas statistical profile data. Definitions "
                    "and universe may differ from ACS; compare vintages cautiously."
                ),
                "public_claim_limit": (
                    "Planning and screening use only; not a determination of "
                    "grant eligibility or a substitute for current program rules."
                ),
            }
        )

    state_codes = {
        profile["state_fips"]
        for profile in profiles
        if profile["geography_type"] == "state"
    }
    expected_codes = {
        territory["state_fips"] for territory in ISLAND_ENDPOINTS.values()
    }
    if state_codes != expected_codes:
        raise BuildError(
            "Island Areas state coverage mismatch; "
            f"expected={sorted(expected_codes)}, actual={sorted(state_codes)}"
        )
    return profiles, sources, queries, coverage_notes


def output_counts(profiles: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_source = Counter(str(profile["source_id"]) for profile in profiles)
    by_geography = Counter(
        str(profile["geography_type"]) for profile in profiles
    )
    by_state = Counter(str(profile["state_fips"]) for profile in profiles)
    return {
        "total": len(profiles),
        "by_source": dict(sorted(by_source.items())),
        "by_geography_type": dict(sorted(by_geography.items())),
        "by_state_fips": dict(sorted(by_state.items())),
    }


def validate_profiles(
    profiles: Sequence[Mapping[str, Any]],
    counts: Mapping[str, Any],
) -> None:
    profile_ids = [str(profile["profile_id"]) for profile in profiles]
    duplicate_ids = sorted(
        profile_id
        for profile_id, count in Counter(profile_ids).items()
        if count > 1
    )
    if duplicate_ids:
        raise BuildError(
            f"Duplicate profile keys found: {', '.join(duplicate_ids[:10])}"
        )

    for profile in profiles:
        keys = profile.get("lookup_keys")
        if not isinstance(keys, list) or not keys or len(keys) != len(set(keys)):
            raise BuildError(
                f"Invalid or duplicate lookup keys for {profile['profile_id']}"
            )
        if str(profile["state_fips"]) not in ALL_STATES:
            raise BuildError(
                f"Unknown state code in {profile['profile_id']}"
            )
        for metric_name, metric in profile["metrics"].items():
            for field_name in ("value", "margin_of_error"):
                value = metric[field_name]
                if value is not None and (
                    not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    or value <= -100_000_000
                ):
                    raise BuildError(
                        f"Invalid numeric value in {profile['profile_id']} "
                        f"{metric_name}.{field_name}"
                    )

    actual_territories = {
        str(profile["state_fips"])
        for profile in profiles
        if profile.get("is_territory")
    }
    if actual_territories != TERRITORY_FIPS:
        raise BuildError(
            "Territory coverage mismatch; "
            f"expected={sorted(TERRITORY_FIPS)}, "
            f"actual={sorted(actual_territories)}"
        )
    state_profile_codes = {
        str(profile["state_fips"])
        for profile in profiles
        if profile["geography_type"] == "state"
    }
    if state_profile_codes != set(ALL_STATES):
        raise BuildError(
            "State-level output does not cover exactly the 50 states, DC, "
            "Puerto Rico, American Samoa, Guam, Northern Mariana Islands, "
            "and U.S. Virgin Islands"
        )

    if counts["total"] != len(profiles):
        raise BuildError("Total output count does not match profile records")
    for count_name in ("by_source", "by_geography_type", "by_state_fips"):
        values = counts[count_name]
        if sum(values.values()) != len(profiles):
            raise BuildError(f"{count_name} does not sum to the total output count")


def field_dictionary() -> list[dict[str, str]]:
    return [
        {
            "field": "profile_id",
            "alias": "Stable Profile ID",
            "description": "Stable U.S. geography key built from geography type and GEOID.",
            "unit_or_domain": "text",
            "null_meaning": "Not permitted",
        },
        {
            "field": "name",
            "alias": "Census Geography Name",
            "description": "Official geography name returned by the source endpoint.",
            "unit_or_domain": "text",
            "null_meaning": "Not permitted",
        },
        {
            "field": "lookup_keys",
            "alias": "Normalized Lookup Keys",
            "description": "ASCII-normalized search keys for name, state, type, and GEOID.",
            "unit_or_domain": "array of text",
            "null_meaning": "Not permitted",
        },
        {
            "field": "geoid",
            "alias": "Census GEOID",
            "description": "Concatenated Census geographic identifier for the record.",
            "unit_or_domain": "text",
            "null_meaning": "Not permitted",
        },
        {
            "field": "geography_type",
            "alias": "Geography Type",
            "description": "State, county, place, or county subdivision.",
            "unit_or_domain": "state|county|place|county_subdivision",
            "null_meaning": "Not permitted",
        },
        {
            "field": "state_fips",
            "alias": "State or Territory FIPS",
            "description": "Two-digit Census state or territory code.",
            "unit_or_domain": "two-digit text",
            "null_meaning": "Not permitted",
        },
        {
            "field": "state_abbreviation",
            "alias": "State or Territory Abbreviation",
            "description": "USPS abbreviation for the state or territory.",
            "unit_or_domain": "two-character text",
            "null_meaning": "Not permitted",
        },
        {
            "field": "state_name",
            "alias": "State or Territory Name",
            "description": "Plain-language state or territory name.",
            "unit_or_domain": "text",
            "null_meaning": "Not permitted",
        },
        {
            "field": "metrics",
            "alias": "Community Profile Metrics",
            "description": (
                "Population, median age, median household income, poverty rate, "
                "and broadband rate with source variables, units, and available "
                "margins of error."
            ),
            "unit_or_domain": "object",
            "null_meaning": "Individual source values may be unavailable or suppressed",
        },
        {
            "field": "notes",
            "alias": "Data Quality Notes",
            "description": "Margin, suppression, and source coverage notes.",
            "unit_or_domain": "object of text arrays",
            "null_meaning": "Empty arrays mean no record-specific note",
        },
        {
            "field": "source_url",
            "alias": "Census Source URL",
            "description": "Reproducible Census API query URL with no API key.",
            "unit_or_domain": "HTTPS URL",
            "null_meaning": "Not permitted",
        },
        {
            "field": "vintage",
            "alias": "Source Vintage",
            "description": "Published Census dataset and reference vintage.",
            "unit_or_domain": "text",
            "null_meaning": "Not permitted",
        },
    ]


def browser_projection(
    profiles: Sequence[Mapping[str, Any]],
    sources: Sequence[Mapping[str, Any]],
    counts: Mapping[str, Any],
    generated_at: str,
) -> list[dict[str, Any]]:
    source_index = {
        str(source["source_id"]): {
            "title": source["title"],
            "vintage": source["vintage"],
            "url": source["dataset_url"],
        }
        for source in sources
    }
    compact_profiles: list[dict[str, Any]] = []
    for profile in profiles:
        metrics = profile["metrics"]
        notes = [
            note
            for note_group in profile["notes"].values()
            for note in note_group
        ]
        geography_type = profile["geography_type"]
        place_type = {
            "place": "town_or_city",
            "county": "county_or_region",
            "county_subdivision": "county_or_region",
            "state": "statewide_or_multi_community",
        }.get(geography_type, "")
        source = source_index[str(profile["source_id"])]
        projected = {
            "id": profile["profile_id"],
            "community": profile["name"],
            "name": profile["name"],
            "geoid": profile["geoid"],
            "state": profile["state_name"],
            "stateCode": profile["state_name"],
            "placeType": place_type,
            "source": source["title"],
            "vintage": profile["vintage"],
            "coverageNote": " | ".join(notes)[:800],
        }
        for public_name, metric_name in (
            ("population", "population"),
            ("medianHouseholdIncome", "median_household_income"),
            ("povertyRate", "poverty_rate"),
            ("broadbandRate", "broadband_rate"),
        ):
            value = metrics[metric_name]["value"]
            if value is not None:
                projected[public_name] = value
        compact_profiles.append(projected)
    return compact_profiles

def json_text(value: Any, *, compact: bool = False) -> str:
    if compact:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )


def safe_javascript_json(value: Any) -> str:
    serialized = json_text(value, compact=True)
    return (
        serialized.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def assert_no_secret(serialized_outputs: Iterable[str], api_key: str) -> None:
    if not api_key:
        raise BuildError("Census API key is empty")
    for serialized in serialized_outputs:
        if api_key in serialized:
            raise BuildError("Secret material was detected in serialized output")
        if re.search(r"[?&]key=", serialized, flags=re.IGNORECASE):
            raise BuildError("A Census API key parameter was detected in output")


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.replace(temporary_path, path)
    except Exception:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def run_offline_self_tests() -> None:
    estimate_metadata = {
        details["estimate"].lower(): {
            "label": f"Estimate!!{metric_name}",
            "concept": metric_name,
            "predicateType": "float",
            "predicateOnly": True,
            "group": details["estimate"].split("_", 1)[0],
        }
        for metric_name, details in ACS_METRICS.items()
    }
    variables = variable_metadata(
        {"variables": estimate_metadata},
        "offline estimate-only fixture",
    )
    definitions = acs_metric_definitions(variables)
    expected_estimates = [
        ACS_METRICS[metric_name]["estimate"] for metric_name in METRIC_ORDER
    ]
    if acs_requested_variables(definitions) != expected_estimates:
        raise BuildError("self-test failed: estimate-only request variables")
    if any(definition["margin"] is not None for definition in definitions.values()):
        raise BuildError("self-test failed: absent margins were selected")

    margin_metadata = {
        details["margin"]: {
            "label": f"Margin of Error!!{metric_name}",
            "concept": metric_name,
            "predicateType": "float",
            "predicateOnly": True,
            "group": details["estimate"].split("_", 1)[0],
        }
        for metric_name, details in ACS_METRICS.items()
    }
    merge_variable_metadata(variables, margin_metadata)
    definitions_with_margins = acs_metric_definitions(variables)
    expected_with_margins = [
        code
        for metric_name in METRIC_ORDER
        for code in (
            ACS_METRICS[metric_name]["estimate"],
            ACS_METRICS[metric_name]["margin"],
        )
    ]
    if acs_requested_variables(definitions_with_margins) != expected_with_margins:
        raise BuildError("self-test failed: available margins were not selected")

    for endpoint_name, territory in ISLAND_ENDPOINTS.items():
        state_fips = territory["state_fips"]
        expected_query_shapes = {
            "state": [("for", "state:*")],
            "place": [
                ("for", "place:*"),
                ("in", f"state:{state_fips}"),
            ],
            "county subdivision": [
                ("for", "county subdivision:*"),
                ("in", f"state:{state_fips}"),
                ("in", "county:*"),
            ],
        }
        actual_query_shapes = {
            "state": geography_parameters("state", [], state_fips),
            "place": geography_parameters("place", ["state"], state_fips),
            "county subdivision": geography_parameters(
                "county subdivision",
                ["county", "state"],
                state_fips,
            ),
        }
        if actual_query_shapes != expected_query_shapes:
            raise BuildError(
                f"self-test failed: {endpoint_name} Island query shape"
            )

    class OfflineHTTPError:
        code = 400

        @staticmethod
        def read(limit: int) -> bytes:
            if limit != 4096:
                raise BuildError("self-test failed: unbounded HTTP error read")
            return (
                b"wildcard not allowed for 'state' in geography hierarchy "
                b"?key=offline-test-secret"
            )

    safe_error_url = (
        "https://api.census.gov/data/2020/dec/dpas?"
        "for=county+subdivision%3A%2A&in=state%3A60&in=county%3A%2A"
    )
    http_error_message = census_http_error_message(
        safe_error_url,
        OfflineHTTPError(),  # type: ignore[arg-type]
        "offline-test-secret",
    )
    if (
        safe_error_url not in http_error_message
        or "wildcard not allowed" not in http_error_message
        or "offline-test-secret" in http_error_message
        or "key=" in safe_error_url.casefold()
    ):
        raise BuildError("self-test failed: safe HTTP error diagnostics")

    profile = {
        "profile_id": "us:place:0100001",
        "name": "Example place, Alabama",
        "geoid": "0100001",
        "geography_type": "place",
        "state_name": "Alabama",
        "source_id": "acs_2024_5yr_profile",
        "vintage": "2024 ACS 5-year Data Profiles",
        "notes": {"margin": [], "suppression": [], "coverage": []},
        "metrics": {
            "population": {"value": 1000},
            "median_age": {"value": 40.5},
            "median_household_income": {"value": 55000},
            "poverty_rate": {"value": 12.5},
            "broadband_rate": {"value": 81.2},
        },
    }
    source = {
        "source_id": "acs_2024_5yr_profile",
        "title": "2024 ACS 5-year Data Profiles",
        "vintage": "2024",
        "dataset_url": ACS_ENDPOINT,
    }
    projected = browser_projection([profile], [source], {}, "offline")
    if not isinstance(projected, list) or len(projected) != 1:
        raise BuildError("self-test failed: planner projection must be an array")
    record = projected[0]
    expected_public_values = {
        "community": "Example place, Alabama",
        "name": "Example place, Alabama",
        "geoid": "0100001",
        "state": "Alabama",
        "stateCode": "Alabama",
        "placeType": "town_or_city",
        "population": 1000,
        "medianHouseholdIncome": 55000,
        "povertyRate": 12.5,
        "broadbandRate": 81.2,
        "source": "2024 ACS 5-year Data Profiles",
    }
    if any(record.get(key) != value for key, value in expected_public_values.items()):
        raise BuildError("self-test failed: planner public field contract")
    if not safe_javascript_json(projected).startswith("["):
        raise BuildError("self-test failed: browser assignment must contain an array")

    null_profile = dict(profile)
    null_profile["metrics"] = {
        key: dict(value) for key, value in profile["metrics"].items()
    }
    null_profile["metrics"]["broadband_rate"]["value"] = None
    null_projected = browser_projection([null_profile], [source], {}, "offline")
    if "broadbandRate" in null_projected[0]:
        raise BuildError("self-test failed: null metric must be omitted")

    for metric_name in METRIC_ORDER:
        for sentinel_code, expected_note in SENTINEL_VALUES.items():
            formatted_values = (
                sentinel_code,
                f"{sentinel_code}.0",
                f"{int(sentinel_code):,}.0",
                f"{sentinel_code}e0",
            )
            for formatted_value in formatted_values:
                parsed, note = parse_number(
                    formatted_value,
                    metric_name,
                    integer=metric_name == "population",
                )
                if parsed is not None or parsed == 0 or note != expected_note:
                    raise BuildError(
                        "self-test failed: documented Census sentinel normalization"
                    )
    unknown_value, unknown_note = parse_number(
        "-444444444.0",
        "median_age",
    )
    if unknown_value is not None or "unrecognized special numeric code" not in str(
        unknown_note
    ):
        raise BuildError("self-test failed: defensive unknown sentinel omission")

    sentinel_definitions = {
        metric_name: {
            "estimate": f"TEST_{index}",
            "margin": None,
            "unit": ACS_METRICS[metric_name]["unit"],
        }
        for index, metric_name in enumerate(METRIC_ORDER)
    }
    sentinel_row = {
        definition["estimate"]: "-666,666,666.0"
        for definition in sentinel_definitions.values()
    }
    sentinel_metrics, sentinel_notes = build_metric_values(
        sentinel_row,
        sentinel_definitions,
    )
    if any(metric["value"] is not None for metric in sentinel_metrics.values()):
        raise BuildError("self-test failed: sentinel mapped to a metric value")
    if len(sentinel_notes["suppression"]) != len(METRIC_ORDER):
        raise BuildError("self-test failed: sentinel omission notes were not retained")
    sentinel_profile = dict(profile)
    sentinel_profile["metrics"] = sentinel_metrics
    sentinel_profile["notes"] = sentinel_notes
    sentinel_projected = browser_projection(
        [sentinel_profile],
        [source],
        {},
        "offline",
    )[0]
    public_metric_fields = {
        "population",
        "medianHouseholdIncome",
        "povertyRate",
        "broadbandRate",
    }
    if public_metric_fields.intersection(sentinel_projected):
        raise BuildError("self-test failed: sentinel leaked into public projection")
    if "estimate could not be computed" not in sentinel_projected["coverageNote"]:
        raise BuildError("self-test failed: public omission note was not retained")

    for metric_name in METRIC_ORDER:
        for small_code in ("-1", "-2.0", "-9e0"):
            parsed, note = parse_number(
                small_code,
                metric_name,
                integer=metric_name == "population",
            )
            if parsed is not None or "negative special numeric code" not in str(note):
                raise BuildError("self-test failed: small special numeric code")

    invalid_definitions = {
        metric_name: {
            "estimate": f"RANGE_{index}",
            "margin": None,
            "unit": ACS_METRICS[metric_name]["unit"],
        }
        for index, metric_name in enumerate(METRIC_ORDER)
    }
    invalid_row = {
        invalid_definitions["poverty_rate"]["estimate"]: "101.25",
    }
    invalid_row["NAME"] = "Example place, Alabama"
    try:
        make_profile(
            row=invalid_row,
            geography_type="place",
            geoid="0100001",
            state_fips="01",
            source_id="acs_2024_5yr_profile",
            source_url="https://api.census.gov/mock",
            source_vintage="2024 ACS 5-year Data Profiles",
            generated_at="offline",
            metric_definitions=invalid_definitions,
        )
    except BuildError as exc:
        error_text = str(exc)
        required_context = (
            "poverty_rate must be between 0 and 100",
            "variable=RANGE_3",
            "value='101.25'",
            "source_id='acs_2024_5yr_profile'",
            "geography_type='place'",
            "geoid='0100001'",
            "state_fips='01'",
            "name='Example place, Alabama'",
        )
        if any(fragment not in error_text for fragment in required_context):
            raise BuildError("self-test failed: validation error context") from exc
    else:
        raise BuildError("self-test failed: valid percentage range was weakened")

    island_fixture = {
        "DP1_0001C": {
            "label": "Number!!SEX AND AGE!!Total population",
            "concept": "GENERAL DEMOGRAPHIC CHARACTERISTICS",
            "predicateType": "int",
        },
        "DP1_0064C": {
            "label": "Number!!SEX AND AGE!!Total population!!Median age (years)",
            "concept": "GENERAL DEMOGRAPHIC CHARACTERISTICS",
            "predicateType": "float",
        },
        "DP3_0062C": {
            "label": (
                "Number!!INCOME IN 2019!!Households!!"
                "Median household income (dollars)"
            ),
            "concept": "Selected Economic Characteristics",
            "predicateType": "int",
        },
        "DP3_0139C": {
            "label": "POVERTY STATUS!!Families!!Below poverty level",
            "concept": "Selected Economic Characteristics",
            "predicateType": "int",
        },
        "DP3_0139P": {
            "label": (
                "Percent!!NUMBER AND PERCENTAGE OF FAMILIES AND PEOPLE WITH "
                "INCOME IN 2019 BELOW POVERTY LEVEL!!Families"
            ),
            "concept": "Selected Economic Characteristics",
            "predicateType": "float",
        },
        "DP3_0151P": {
            "label": (
                "Percent!!NUMBER AND PERCENTAGE OF FAMILIES AND PEOPLE WITH "
                "INCOME IN 2019 BELOW POVERTY LEVEL!!All Individuals in households"
            ),
            "concept": "Selected Economic Characteristics",
            "predicateType": "float",
        },
        "DP2_0153P": {
            "label": (
                "Percent!!COMPUTERS AND INTERNET USE!!Total households!!"
                "With a broadband Internet subscription"
            ),
            "concept": "Selected Social Characteristics",
            "predicateType": "float",
        },
    }
    expected_island_variables = {
        "population": "DP1_0001C",
        "median_age": "DP1_0064C",
        "median_household_income": "DP3_0062C",
        "poverty_rate": "DP3_0151P",
    }
    island_endpoint_fixtures = {
        endpoint_name: {
            variable_name: dict(details)
            for variable_name, details in island_fixture.items()
        }
        for endpoint_name in ISLAND_ENDPOINTS
    }
    island_endpoint_fixtures["dpgu"]["DP3_0062C"] = {
        "label": (
            "Number!!INCOME IN 2019!!Households "
            "(excluding people in military housing units)!!"
            "Median household income (dollars)"
        ),
        "concept": "Selected Economic Characteristics",
        "predicateType": "int",
    }
    island_endpoint_fixtures["dpgu"]["DP3_0151P"] = {
        "label": (
            "Percent!!NUMBER AND PERCENTAGE OF FAMILIES AND PEOPLE WITH "
            "INCOME IN 2019 BELOW POVERTY LEVEL!!"
            "All Individuals in households "
            "(excluding people in military housing units)"
        ),
        "concept": "Selected Economic Characteristics",
        "predicateType": "float",
    }
    island_endpoint_fixtures["dpmp"]["DP3_0151P"] = {
        "label": (
            "Percent!!NUMBER AND PERCENTAGE OF FAMILIES AND PEOPLE WITH "
            "INCOME IN 2019 BELOW POVERTY LEVEL!!All Individuals"
        ),
        "concept": "Selected Economic Characteristics",
        "predicateType": "float",
    }
    broadband_endpoint_metadata = {
        "dpas": (
            "DP4_0091P",
            {
                "label": (
                    "Percent!!COMPUTER AND INTERNET USE!!Occupied housing units!!"
                    "With a broadband Internet subscription"
                ),
                "concept": "SELECTED HOUSING CHARACTERISTICS",
                "predicateType": "float",
            },
        ),
        "dpgu": (
            "DP4_0090P",
            {
                "label": (
                    "Percent!!COMPUTER AND INTERNET USE!!Occupied housing units "
                    "(excluding military housing units)!!"
                    "With a broadband Internet subscription"
                ),
                "concept": "SELECTED HOUSING CHARACTERISTICS",
                "predicateType": "float",
            },
        ),
        "dpmp": (
            "DP4_9001P",
            {
                "label": (
                    "Percent!!COMPUTER AND INTERNET USE!!Occupied housing units!!"
                    "With a broadband Internet subscription"
                ),
                "concept": "SELECTED HOUSING CHARACTERISTICS",
                "predicateType": "float",
            },
        ),
        "dpvi": (
            "DP4_9002P",
            {
                "label": (
                    "Percent!!COMPUTER AND INTERNET USE!!Occupied housing units!!"
                    "With a broadband Internet subscription"
                ),
                "concept": "SELECTED HOUSING CHARACTERISTICS",
                "predicateType": "float",
            },
        ),
    }
    for endpoint_name, (variable_name, details) in broadband_endpoint_metadata.items():
        island_endpoint_fixtures[endpoint_name][variable_name] = details
    discovered_by_endpoint = {
        endpoint_name: discover_island_metrics(fixture, endpoint_name)
        for endpoint_name, fixture in island_endpoint_fixtures.items()
    }
    for endpoint_name, island_metrics in discovered_by_endpoint.items():
        actual_island_variables = {
            metric_name: metric.estimate
            for metric_name, metric in island_metrics.items()
        }
        expected_for_endpoint = {
            **expected_island_variables,
            "broadband_rate": broadband_endpoint_metadata[endpoint_name][0],
        }
        if actual_island_variables != expected_for_endpoint:
            raise BuildError(
                f"self-test failed: {endpoint_name} Island Areas semantic mapping"
            )
        population_metadata = island_metrics["population"].estimate_metadata
        if (
            population_metadata is None
            or variable_label(population_metadata)
            != "Number!!SEX AND AGE!!Total population"
            or variable_concept(population_metadata)
            != "GENERAL DEMOGRAPHIC CHARACTERISTICS"
            or population_metadata.get("predicateType") != "int"
        ):
            raise BuildError(
                f"self-test failed: {endpoint_name} exact population metadata"
            )
    if (
        island_endpoint_fixtures["dpas"]["DP4_0091P"]
        != broadband_endpoint_metadata["dpas"][1]
        or island_endpoint_fixtures["dpgu"]["DP4_0090P"]
        != broadband_endpoint_metadata["dpgu"][1]
    ):
        raise BuildError("self-test failed: exact dpas/dpgu broadband metadata")
    broadband_signatures = {
        island_metric_cross_endpoint_signature(
            "broadband_rate",
            metrics["broadband_rate"].estimate_metadata or {},
        )
        for metrics in discovered_by_endpoint.values()
    }
    if len(broadband_signatures) != 1:
        raise BuildError(
            "self-test failed: broadband semantic signatures differ by endpoint"
        )
    median_income_signatures = {
        island_metric_cross_endpoint_signature(
            "median_household_income",
            metrics["median_household_income"].estimate_metadata or {},
        )
        for metrics in discovered_by_endpoint.values()
    }
    if len(median_income_signatures) != 1:
        raise BuildError(
            "self-test failed: optional military-housing qualifier was not normalized"
        )
    if variable_label(
        island_endpoint_fixtures["dpgu"]["DP3_0062C"]
    ) != (
        "Number!!INCOME IN 2019!!Households "
        "(excluding people in military housing units)!!"
        "Median household income (dollars)"
    ):
        raise BuildError("self-test failed: exact dpgu median-income fixture")
    wrong_income_leaf_errors = island_metric_contract_errors(
        "median_household_income",
        "DP3_0063C",
        {
            "label": (
                "Number!!INCOME IN 2019!!Households!!"
                "Mean household income (dollars)"
            ),
            "concept": "Selected Economic Characteristics",
            "predicateType": "int",
        },
    )
    if not any("label leaf" in error for error in wrong_income_leaf_errors):
        raise BuildError(
            "self-test failed: wrong household-income leaf was not rejected"
        )
    poverty_signatures = {
        island_metric_cross_endpoint_signature(
            "poverty_rate",
            metrics["poverty_rate"].estimate_metadata or {},
        )
        for metrics in discovered_by_endpoint.values()
    }
    if len(poverty_signatures) != 1:
        raise BuildError(
            "self-test failed: documented poverty leaves were not normalized"
        )
    if variable_label(
        island_endpoint_fixtures["dpmp"]["DP3_0151P"]
    ) != (
        "Percent!!NUMBER AND PERCENTAGE OF FAMILIES AND PEOPLE WITH "
        "INCOME IN 2019 BELOW POVERTY LEVEL!!All Individuals"
    ):
        raise BuildError("self-test failed: exact dpmp poverty fixture")
    guam_poverty_details = island_endpoint_fixtures["dpgu"]["DP3_0151P"]
    if (
        variable_label(guam_poverty_details)
        != (
            "Percent!!NUMBER AND PERCENTAGE OF FAMILIES AND PEOPLE WITH "
            "INCOME IN 2019 BELOW POVERTY LEVEL!!"
            "All Individuals in households "
            "(excluding people in military housing units)"
        )
        or island_semantic_label_path(guam_poverty_details)[-1]
        != "all individuals in households"
    ):
        raise BuildError("self-test failed: exact Guam poverty fixture")
    island_metrics = discovered_by_endpoint["dpas"]
    if island_metrics["poverty_rate"].estimate == "DP3_0139C":
        raise BuildError("self-test failed: family count selected as poverty rate")
    family_leaf_errors = island_metric_contract_errors(
        "poverty_rate",
        "DP3_0139P",
        island_fixture["DP3_0139P"],
    )
    if not any(
        "leaf contains incompatible term 'families'" in error
        for error in family_leaf_errors
    ):
        raise BuildError(
            "self-test failed: family-only poverty leaf was not rejected"
        )
    for invalid_leaf in (
        "Families with related children under 18 years",
        "All Individuals under 18 years",
        (
            "All Individuals under 18 years "
            "(excluding people in military housing units)"
        ),
    ):
        invalid_leaf_errors = island_metric_contract_errors(
            "poverty_rate",
            "DP3_0151P",
            {
                "label": (
                    "Percent!!NUMBER AND PERCENTAGE OF FAMILIES AND PEOPLE WITH "
                    f"INCOME IN 2019 BELOW POVERTY LEVEL!!{invalid_leaf}"
                ),
                "concept": "Selected Economic Characteristics",
                "predicateType": "float",
            },
        )
        if not any(
            "label leaf must exactly match" in error
            for error in invalid_leaf_errors
        ):
            raise BuildError(
                f"self-test failed: poverty subgroup leaf accepted: {invalid_leaf}"
            )

    wrong_population_measure = dict(island_fixture)
    wrong_population_measure["DP1_0001C"] = {
        "label": "Number!!HOUSEHOLDS BY TYPE!!Total households",
        "concept": "GENERAL DEMOGRAPHIC CHARACTERISTICS",
        "predicateType": "int",
    }
    try:
        discover_island_metrics(
            wrong_population_measure,
            "offline-wrong-population-measure",
        )
    except BuildError as exc:
        if "population" not in str(exc):
            raise BuildError(
                "self-test failed: wrong population measure lacked context"
            ) from exc
    else:
        raise BuildError(
            "self-test failed: household count accepted as population"
        )

    mislabeled_required_poverty = dict(island_fixture)
    mislabeled_required_poverty["DP3_0151P"] = {
        "label": "POVERTY STATUS!!Families!!Below poverty level!!Number",
        "concept": "Selected Economic Characteristics",
        "predicateType": "int",
    }
    try:
        discover_island_metrics(
            mislabeled_required_poverty,
            "offline-mislabeled-required-poverty",
        )
    except BuildError as exc:
        mismatch_text = str(exc)
        if (
            "DP3_0151P" not in mismatch_text
            or "label=" not in mismatch_text
            or "errors=" not in mismatch_text
        ):
            raise BuildError(
                "self-test failed: required poverty metadata mismatch lacked context"
            ) from exc
    else:
        raise BuildError(
            "self-test failed: poverty ID accepted without semantic metadata"
        )

    count_as_percent = dict(island_fixture)
    count_as_percent.pop("DP3_0151P")
    count_as_percent["DP3_0139C"] = {
        "label": (
            "Percent!!POVERTY STATUS!!All Individuals in households!!"
            "Below poverty level"
        ),
        "concept": "Selected Economic Characteristics",
        "predicateType": "int",
    }
    try:
        discover_island_metrics(count_as_percent, "offline-count-mismatch")
    except BuildError as exc:
        mismatch_text = str(exc)
        if (
            "poverty_rate" not in mismatch_text
            or "DP3_0151P" not in mismatch_text
        ):
            raise BuildError(
                "self-test failed: poverty count mismatch lacked context"
            ) from exc
    else:
        raise BuildError("self-test failed: count accepted as poverty percent")

    broadband_count = {
        name: dict(details)
        for name, details in island_endpoint_fixtures["dpas"].items()
    }
    broadband_count.pop("DP4_0091P")
    broadband_count["DP4_0091C"] = {
        "label": (
            "Percent!!COMPUTER AND INTERNET USE!!Occupied housing units!!"
            "With a broadband Internet subscription"
        ),
        "concept": "SELECTED HOUSING CHARACTERISTICS",
        "predicateType": "int",
    }
    try:
        discover_island_metrics(broadband_count, "offline-broadband-mismatch")
    except BuildError as exc:
        if "broadband_rate" not in str(exc):
            raise BuildError(
                "self-test failed: broadband type mismatch lacked context"
            ) from exc
    else:
        raise BuildError("self-test failed: count accepted as broadband percent")
    unrelated_broadband_errors = island_metric_contract_errors(
        "broadband_rate",
        "DP4_0088P",
        {
            "label": (
                "Percent!!COMPUTER AND INTERNET USE!!Occupied housing units!!"
                "Without an Internet subscription"
            ),
            "concept": "SELECTED HOUSING CHARACTERISTICS",
            "predicateType": "float",
        },
    )
    if not any("label leaf" in error for error in unrelated_broadband_errors):
        raise BuildError(
            "self-test failed: unrelated Internet field was not rejected by leaf"
        )

    print("PREDICATE_ONLY_METADATA_OK")
    print("OPTIONAL_MARGIN_QUERY_OK")
    print("PLANNER_PUBLIC_SCHEMA_OK")
    print("NULL_METRIC_OMISSION_OK")
    print("CENSUS_SENTINEL_OMISSION_OK")
    print("CENSUS_SMALL_SPECIAL_VALUE_OK")
    print("VALIDATION_CONTEXT_OK")
    print("ISLAND_METRIC_SEMANTICS_OK")
    print("ISLAND_POVERTY_MAPPING_OK")
    print("ISLAND_COUNT_PERCENT_REJECTION_OK")
    print("ISLAND_FOUR_ENDPOINT_METADATA_PATTERNS_OK")
    print("ISLAND_POVERTY_LEAF_PATH_OK")
    print("ISLAND_BROADBAND_HOUSING_PROFILE_OK")
    print("ISLAND_QUERY_SHAPES_OK")
    print("SAFE_HTTP_ERROR_CONTEXT_OK")
    print("ISLAND_MEDIAN_INCOME_QUALIFIER_NORMALIZATION_OK")
    print("ISLAND_POVERTY_EQUIVALENT_LEAVES_OK")
    print("ISLAND_GUAM_POVERTY_QUALIFIER_NORMALIZATION_OK")


def main() -> int:
    args = parse_args()
    if args.self_test:
        run_offline_self_tests()
        return 0
    generated_at = generated_timestamp(args.generated_at)
    api_key = read_env_value(args.env_file, "CENSUS_API_KEY")
    client = CensusClient(
        api_key=api_key,
        timeout_seconds=args.timeout,
        retries=args.retries,
        backoff_seconds=args.backoff,
    )

    acs_profiles, acs_source, acs_queries = build_acs_profiles(
        client, generated_at
    )
    island_profiles, island_sources, island_queries, coverage_notes = (
        build_island_profiles(client, generated_at)
    )
    profiles = sorted(
        [*acs_profiles, *island_profiles],
        key=lambda profile: (
            profile["state_fips"],
            profile["geography_type"],
            profile["geoid"],
            profile["name"],
        ),
    )
    counts = output_counts(profiles)
    validate_profiles(profiles, counts)

    sources = [acs_source, *island_sources]
    governed_dataset = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "title": "RERC U.S. Census Community Profiles",
        "summary": (
            "Governed community profile records for the 50 states, District of "
            "Columbia, Puerto Rico, American Samoa, Guam, Northern Mariana "
            "Islands, and U.S. Virgin Islands."
        ),
        "records": profiles,
    }
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "dataset_title": "RERC U.S. Census Community Profiles",
        "publisher": "RERC Community Explorer data pipeline",
        "source_authority": "U.S. Census Bureau",
        "source_license": (
            "U.S. Census Bureau public data; see source dataset documentation "
            "and Census terms of service."
        ),
        "update_cadence": (
            "Rebuild when the selected ACS vintage changes or Island Areas "
            "profile data are superseded."
        ),
        "spatial_extent": (
            "United States, District of Columbia, Puerto Rico, American Samoa, "
            "Guam, Northern Mariana Islands, and U.S. Virgin Islands."
        ),
        "crs": (
            "Not applicable: tabular profiles keyed to Census GEOIDs; no "
            "coordinates or geometries are published by this builder."
        ),
        "temporal_resolution": (
            "2024 ACS 5-year estimates and 2020 Island Areas profiles."
        ),
        "known_limitations": [
            "ACS and Island Areas profiles use different programs and vintages.",
            "Island Areas variables are selected from each endpoint's current metadata.",
            "A null metric means unavailable, suppressed, or not computable; inspect notes.",
            "Documented Census special numeric values are omitted and retained as record notes.",
            "Profiles support planning screens, not grant eligibility determinations.",
            *coverage_notes,
        ],
        "public_claim_limit": (
            "Use for community context and screening only. Cite source vintage "
            "and review current Census definitions before public claims."
        ),
        "source_lineage": sources,
        "queries": [*acs_queries, *island_queries],
        "field_dictionary": field_dictionary(),
        "output_counts": counts,
        "validation": {
            "profile_keys_unique": True,
            "lookup_keys_unique_within_profile": True,
            "numeric_sentinels_removed_and_not_published": True,
            "state_level_coverage_exact": sorted(ALL_STATES),
            "territory_coverage_exact": sorted(TERRITORY_FIPS),
            "output_counts_reconciled": True,
            "secret_material_published": False,
        },
        "output_files": {
            "governed_dataset": "rerc_community_profiles.source.json",
            "metadata": "rerc_community_profiles.metadata.json",
            "browser_projection": args.site_output.name,
        },
    }
    browser_data = browser_projection(
        profiles,
        sources,
        counts,
        generated_at,
    )
    if len(browser_data) > args.max_browser_records:
        raise BuildError(
            f"Browser projection has {len(browser_data)} records; "
            f"limit is {args.max_browser_records}"
        )

    governed_text = json_text(governed_dataset)
    metadata_text = json_text(metadata)
    browser_text = (
        "window.RERC_COMMUNITY_PROFILES="
        f"{safe_javascript_json(browser_data)};\n"
    )
    browser_size = len(browser_text.encode("utf-8"))
    if browser_size > args.max_browser_bytes:
        raise BuildError(
            f"Browser projection is {browser_size} bytes; "
            f"limit is {args.max_browser_bytes}"
        )
    assert_no_secret(
        (governed_text, metadata_text, browser_text),
        api_key,
    )

    governed_path = args.castle_output / "rerc_community_profiles.source.json"
    metadata_path = args.castle_output / "rerc_community_profiles.metadata.json"
    atomic_write_text(governed_path, governed_text)
    atomic_write_text(metadata_path, metadata_text)
    atomic_write_text(args.site_output, browser_text)

    print(f"Built {counts['total']} governed community profiles.")
    print(f"Governed dataset: {governed_path}")
    print(f"Metadata: {metadata_path}")
    print(f"Browser projection: {args.site_output} ({browser_size} bytes)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        raise SystemExit(f"ERROR: {exc}") from None
