"""Architecture guard for the API routing convention.

See docs/api-routing-convention.md. Every new endpoint belongs under /api/v1;
the legacy roots below are frozen, and the infrastructure paths are exempt by
design because probes and load balancers point at fixed URLs.

Nothing here changes a route. It fails the build when a new one drifts.
"""

import pytest

from app.main import app

VERSION_PREFIX = "/api/v1/"

# Frozen. Adding an entry means deliberately opening a new unversioned root,
# which the convention forbids — version the router instead.
LEGACY_ROOTS = frozenset(
    {
        "/audit",
        "/auth",
        "/dwg",
        "/floors",
        "/incidents",
        "/missions",
        "/notification-preferences",
        "/notifications",
        "/pilots",
        "/roles",
        "/users",
    }
)

# Probe and release endpoints. Versioning these would mean re-pointing
# infrastructure for no benefit.
INFRASTRUCTURE_PATHS = frozenset({"/health", "/health/live", "/health/ready", "/version"})

# Endpoint counts at the time the convention was frozen. The totals move only
# when someone edits this file, which keeps legacy growth visible in review.
LEGACY_ENDPOINT_COUNT = 81
# Two server-paginated list endpoints were deliberately added for Users and
# Pilots so their management pages no longer load every accessible row.
VERSIONED_ENDPOINT_COUNT = 16


def api_paths() -> list[str]:
    return sorted(app.openapi()["paths"])


def root_of(path: str) -> str:
    return "/" + path.split("/")[1]


def classify(path: str) -> str:
    if path in INFRASTRUCTURE_PATHS:
        return "infrastructure"
    if path.startswith(VERSION_PREFIX):
        return "versioned"
    if root_of(path) in LEGACY_ROOTS:
        return "legacy"
    return "unclassified"


def test_no_route_escapes_the_convention():
    """The whole rule in one assertion.

    A new router that is neither versioned nor an existing legacy root lands
    here. The fix is a /api/v1 prefix, not a new entry in LEGACY_ROOTS.
    """
    offenders = [path for path in api_paths() if classify(path) == "unclassified"]
    assert offenders == [], (
        "these paths are neither /api/v1 nor a frozen legacy root: "
        f"{offenders}. Register new endpoints under {VERSION_PREFIX}."
    )


def test_legacy_surface_does_not_grow_silently():
    counts = {"legacy": 0, "versioned": 0, "infrastructure": 0, "unclassified": 0}
    for path in api_paths():
        counts[classify(path)] += 1

    assert counts["legacy"] == LEGACY_ENDPOINT_COUNT, (
        f"legacy endpoints moved {LEGACY_ENDPOINT_COUNT} -> {counts['legacy']}. "
        "Adding under an existing legacy tree is allowed but must be deliberate: "
        "update LEGACY_ENDPOINT_COUNT and say why in the commit."
    )
    assert counts["versioned"] == VERSIONED_ENDPOINT_COUNT, (
        f"versioned endpoints moved {VERSIONED_ENDPOINT_COUNT} -> "
        f"{counts['versioned']}. Growth here is expected — bump the constant."
    )
    assert counts["infrastructure"] == len(INFRASTRUCTURE_PATHS)


def test_every_legacy_root_is_still_in_use():
    """Keeps the allowlist honest: a root nobody serves should be dropped."""
    live_roots = {root_of(path) for path in api_paths() if classify(path) == "legacy"}
    stale = LEGACY_ROOTS - live_roots
    assert stale == set(), f"LEGACY_ROOTS lists roots with no endpoints: {sorted(stale)}"


@pytest.mark.parametrize("path", sorted(INFRASTRUCTURE_PATHS))
def test_infrastructure_paths_stay_where_probes_expect_them(path):
    assert path in api_paths(), f"{path} moved; probes and load balancers point at it"


def test_no_route_ends_in_a_trailing_slash():
    offenders = [path for path in api_paths() if path != "/" and path.endswith("/")]
    assert offenders == [], f"trailing slashes are not canonical: {offenders}"


def test_path_segments_use_kebab_case_and_parameters_use_snake_case():
    bad_segments: list[str] = []
    bad_parameters: list[str] = []
    for path in api_paths():
        for segment in path.split("/"):
            if not segment:
                continue
            if segment.startswith("{") and segment.endswith("}"):
                name = segment[1:-1]
                if name != name.lower() or "-" in name:
                    bad_parameters.append(f"{path} -> {segment}")
                continue
            if "_" in segment or segment != segment.lower():
                bad_segments.append(f"{path} -> {segment}")
    assert bad_segments == [], f"path segments must be lowercase kebab-case: {bad_segments}"
    assert bad_parameters == [], f"path parameters must be snake_case: {bad_parameters}"


def test_nesting_never_exceeds_two_identifiers():
    offenders = [path for path in api_paths() if path.count("{") > 2]
    assert offenders == [], (
        f"three identifiers means the middle one is redundant: {offenders}"
    )


def test_versioned_routers_carry_the_prefix_on_the_router():
    """dashboard and reports are the shape new routers copy."""
    from app.routers.dashboard import router as dashboard_router
    from app.routers.reports import router as reports_router

    assert dashboard_router.prefix == "/api/v1/dashboard"
    assert reports_router.prefix == "/api/v1/reports"


def test_call_routes_are_not_reintroduced_by_this_convention():
    assert [path for path in api_paths() if "call" in path.lower()] == []
