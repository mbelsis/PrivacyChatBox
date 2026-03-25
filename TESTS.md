# Tests

## Purpose

This repository now includes an automated `pytest` suite focused on the highest-risk application logic.

The main goals of the suite are:

- catch regressions in security-sensitive behavior
- validate business logic without requiring a full Streamlit UI session
- verify access control, privacy scanning, and migration behavior
- keep extracted page logic testable as pure functions

The tests are intentionally concentrated on logic that has historically produced bugs:

- authentication and session handling
- conversation ownership and deletion
- privacy scanning and anonymization
- provider preflight checks and settings handling
- PDF export escaping and authorization
- migration commit behavior
- admin/history/analytics/settings/chat helper logic

## Where The Tests Are

All automated tests live under [`tests/`](/C:/Users/mbelsis/Documents/GitHub/PrivacyChatBox/tests).

Current layout:

- [`tests/conftest.py`](/C:/Users/mbelsis/Documents/GitHub/PrivacyChatBox/tests/conftest.py)
  Shared test fixtures and lightweight stubs for modules that may not be installed in the local test environment.

- [`tests/test_auth_and_session.py`](/C:/Users/mbelsis/Documents/GitHub/PrivacyChatBox/tests/test_auth_and_session.py)
  Auth rules, self-registration policy, and session expiration behavior.

- [`tests/test_utils_access_and_messages.py`](/C:/Users/mbelsis/Documents/GitHub/PrivacyChatBox/tests/test_utils_access_and_messages.py)
  Conversation ownership checks, deletion permissions, and message/title persistence.

- [`tests/test_privacy_scanner.py`](/C:/Users/mbelsis/Documents/GitHub/PrivacyChatBox/tests/test_privacy_scanner.py)
  Privacy scanner anonymization behavior.

- [`tests/test_detection_helpers.py`](/C:/Users/mbelsis/Documents/GitHub/PrivacyChatBox/tests/test_detection_helpers.py)
  Detection-event retrieval, filtering, formatting, and counts.

- [`tests/test_ai_providers.py`](/C:/Users/mbelsis/Documents/GitHub/PrivacyChatBox/tests/test_ai_providers.py)
  AI provider helper logic, including scan-bypass behavior and override isolation.

- [`tests/test_pdf_export.py`](/C:/Users/mbelsis/Documents/GitHub/PrivacyChatBox/tests/test_pdf_export.py)
  PDF export escaping and access control.

- [`tests/test_migration_add_dlp_columns.py`](/C:/Users/mbelsis/Documents/GitHub/PrivacyChatBox/tests/test_migration_add_dlp_columns.py)
  DLP migration commit behavior.

- [`tests/test_migration_add_local_llm_columns.py`](/C:/Users/mbelsis/Documents/GitHub/PrivacyChatBox/tests/test_migration_add_local_llm_columns.py)
  Local-LLM migration commit behavior.

- [`tests/test_page_logic_chat.py`](/C:/Users/mbelsis/Documents/GitHub/PrivacyChatBox/tests/test_page_logic_chat.py)
  Extracted chat helper logic.

- [`tests/test_page_logic_history_analytics.py`](/C:/Users/mbelsis/Documents/GitHub/PrivacyChatBox/tests/test_page_logic_history_analytics.py)
  Extracted history and analytics helper logic.

- [`tests/test_page_logic_settings_models.py`](/C:/Users/mbelsis/Documents/GitHub/PrivacyChatBox/tests/test_page_logic_settings_models.py)
  Extracted settings and model-manager helper logic.

- [`tests/test_page_logic_admin.py`](/C:/Users/mbelsis/Documents/GitHub/PrivacyChatBox/tests/test_page_logic_admin.py)
  Extracted admin helper logic.

## How The Tests Work

The suite is mostly unit-style and logic-focused.

Design choices:

- It uses an isolated SQLite test database for database-backed logic.
- It avoids requiring a full Streamlit app run.
- It stubs selected external packages in `conftest.py` so the tests can run in lightweight environments.
- It favors pure helper testing where possible, especially for logic extracted from page modules into [`page_logic.py`](/C:/Users/mbelsis/Documents/GitHub/PrivacyChatBox/page_logic.py).

This means:

- the suite is fast
- failures are usually specific and actionable
- coverage is strongest around application logic, not browser/UI rendering

This also means:

- it is not a substitute for full end-to-end Streamlit testing
- provider SDK integration is only partially covered
- visual/UI regressions are not covered here

## How To Run The Tests

From the repository root:

```bash
python -m pytest tests -q
```

If you want more detail:

```bash
python -m pytest tests -v
```

If you want to run a single file:

```bash
python -m pytest tests/test_page_logic_chat.py -q
```

If you want to run a single test:

```bash
python -m pytest tests/test_page_logic_chat.py -k provider_precheck -v
```

## Why These Tests Matter

These tests are not generic boilerplate. They target areas that were previously buggy or high-risk.

Examples:

- auth tests protect against broken registration/session logic
- access-control tests protect conversation privacy boundaries
- privacy-scanner tests protect anonymization correctness
- migration tests protect schema-update durability
- page-logic tests protect admin/history/analytics/chat/settings behavior after refactors

Without these tests, many of the earlier bugs fixed in this repository could quietly reappear.

## How To Interpret Results

### When everything passes

Example:

```text
36 passed in 1.96s
```

This means the currently covered logic still behaves as expected.

It does **not** mean:

- the entire application is bug-free
- every Streamlit page flow has been exercised interactively
- every external integration is fully verified

It means the covered logic contracts are holding.

### When a test fails

Read the failing test name first. Test names are written to describe the expected behavior.

Examples:

- `test_get_conversation_enforces_owner_scope`
- `test_export_conversation_to_pdf_escapes_markup`
- `test_get_chat_provider_precheck_error_covers_missing_keys_and_local_model`

Interpretation:

- if a single focused test fails, a specific behavior likely regressed
- if many tests fail together, a shared helper, fixture, or DB setup may have broken

Useful failure patterns:

- assertion mismatch:
  The code still runs, but behavior changed from the expected contract.

- import/setup failure:
  A module path, dependency assumption, or test harness/stub may need updating.

- database/ORM failure:
  A schema, session, or query change likely affected tested logic.

## Recommended Usage

Run the suite:

- before committing significant logic changes
- after refactoring page code into helpers
- after changing auth, privacy scanning, DB access, or migrations
- in CI on every push and pull request

The repository already includes a GitHub Actions workflow at [`.github/workflows/tests.yml`](/C:/Users/mbelsis/Documents/GitHub/PrivacyChatBox/.github/workflows/tests.yml) that runs the same command automatically.

## Current Scope Gap

The main remaining gaps are:

- full interactive Streamlit behavior
- external-service end-to-end integration
- browser/UI rendering verification

So the suite should be treated as a strong regression net for logic, not as complete system validation.
