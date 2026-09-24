import inspect
import os

import pytest

from custom_components.epex_spot.EPEXSpot import API_REGISTRY

# Determine the path to the EPEXSpot folder containing all API subdirectories
EPEXSPOT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../custom_components/epex_spot/EPEXSpot")
)


def test_registry_matches_directories():
    """1. Ensure that every API directory has an entry in API_REGISTRY."""
    # Find all subdirectories in EPEXSpot, excluding '__pycache__' and system folders
    all_dirs = [
        d for d in os.listdir(EPEXSPOT_DIR)
        if os.path.isdir(os.path.join(EPEXSPOT_DIR, d)) and not d.startswith("__")
    ]

    # The number of registered classes must exactly match the physical folders
    assert len(API_REGISTRY) == len(all_dirs), (
        f"The registry ({len(API_REGISTRY)} items) does not match the directories on disk ({len(all_dirs)} folders: {all_dirs}). "
        "Did you add a new API but forgot to register it in API_REGISTRY?"
    )


@pytest.mark.parametrize("source_name, api_class", API_REGISTRY.items())
def test_api_class_structure(source_name, api_class):
    """2. Verify that all registered classes define MARKET_AREAS and SUPPORTED_DURATIONS."""

    # Check MARKET_AREAS (must be an iterable collection like a tuple, list, or set)
    assert hasattr(api_class, "MARKET_AREAS"), f"Class {api_class.__name__} is missing 'MARKET_AREAS'"
    assert isinstance(api_class.MARKET_AREAS, (tuple, list, set, dict)), (
        f"MARKET_AREAS in {api_class.__name__} must be a list, tuple, set or dict."
    )

    # Check SUPPORTED_DURATIONS (must be a non-empty tuple or list of integers)
    assert hasattr(api_class, "SUPPORTED_DURATIONS"), f"Class {api_class.__name__} is missing 'SUPPORTED_DURATIONS'"
    assert isinstance(api_class.SUPPORTED_DURATIONS, (tuple, list)), (
        f"SUPPORTED_DURATIONS in {api_class.__name__} must be a tuple or list."
    )
    assert len(api_class.SUPPORTED_DURATIONS) > 0, f"SUPPORTED_DURATIONS in {api_class.__name__} cannot be empty."


@pytest.mark.parametrize("source_name, api_class", API_REGISTRY.items())
def test_api_signature_matches_token_requirement(source_name, api_class):
    """3. Verify that __init__ signature matches the REQUIRES_TOKEN boolean flag."""

    # Retrieve the signature parameters of the class's constructor (__init__)
    init_signature = inspect.signature(api_class.__init__)
    init_parameters = init_signature.parameters

    # Check the state of the REQUIRES_TOKEN flag (defaults to False if not present)
    requires_token = getattr(api_class, "REQUIRES_TOKEN", False)

    if requires_token:
        assert "token" in init_parameters, (
            f"Class {api_class.__name__} has REQUIRES_TOKEN = True, "
            f"but its __init__ method is missing the 'token' parameter! Signature: {init_signature}"
        )
    else:
        assert "token" not in init_parameters, (
            f"Class {api_class.__name__} has REQUIRES_TOKEN = False (or undefined), "
            f"but its __init__ method contains an unrequested 'token' parameter! Signature: {init_signature}"
        )

def test_each_api_has_test_file():
    """4. Ensure that every registered API class has a corresponding test file."""
    # Determine the directory where the API test files are located
    test_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../tests/api_scripts")
    )

    # Get a list of all lowercase test file names in the directory
    test_files = []
    if os.path.exists(test_dir):
        test_files = [
            f.lower() for f in os.listdir(test_dir)
            if f.startswith("test_") and f.endswith(".py")
        ]

    # Loop directly through the classes in the registry
    for api_class in API_REGISTRY.values():
        class_name = api_class.__name__.lower()

        # Check if any of the test files contain the class name
        # E.g., 'test_tibber.py' contains 'tibber'
        # E.g., 'test_entsoe_transparency.py' or 'test_entsoe.py' matches if we check substrings
        has_test_file = any(
            class_name in f or f.replace("test_", "").replace(".py", "") in class_name
            for f in test_files
        )

        assert has_test_file, (
            f"API provider class '{api_class.__name__}' does not seem to have a corresponding test file in {test_dir}! "
            f"Expected a file containing '{class_name}' (e.g., 'test_{class_name}.py')."
        )
