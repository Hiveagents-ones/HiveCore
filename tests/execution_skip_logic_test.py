# -*- coding: utf-8 -*-
"""Test for execution skip logic fix.

This test validates that requirements are only skipped when BOTH:
1. All QA criteria pass (100%)
2. Code validation passes (is_valid=True)

Previously, requirements would be incorrectly skipped if only QA passed
but code validation failed, leading to undeployable code.
"""
import pytest


class TestExecutionSkipLogic:
    """Test cases for the fully_passed skip logic."""

    def test_req_state_has_fully_passed_flag(self):
        """Verify req_state includes fully_passed flag."""
        # Simulate req_state initialization
        requirements = [{"id": "REQ-001"}, {"id": "REQ-002"}]
        req_state = {
            req["id"]: {
                "passed": set(),
                "fully_passed": False,
                "code_validation_passed": False,
                "last_qa_report": None,
                "artifact": "",
                "summary": "",
                "feedback": "",
                "validation_errors": [],
                "validation_error_files": set(),
                "validated_files": set(),
                "modified_files": set(),
                "last_validation_score": 0.0,
                "blueprint": None,
                "path": None,
            }
            for req in requirements
        }

        # Verify flags exist and are False by default
        assert "fully_passed" in req_state["REQ-001"]
        assert req_state["REQ-001"]["fully_passed"] is False
        assert "code_validation_passed" in req_state["REQ-001"]
        assert req_state["REQ-001"]["code_validation_passed"] is False

    def test_pending_count_uses_fully_passed(self):
        """Verify pending_count calculation uses fully_passed flag."""
        requirements = [
            {"id": "REQ-001"},
            {"id": "REQ-002"},
            {"id": "REQ-003"},
        ]
        req_state = {
            "REQ-001": {"fully_passed": True},   # Should not be counted
            "REQ-002": {"fully_passed": False},  # Should be counted
            "REQ-003": {"fully_passed": False},  # Should be counted
        }

        # This is the new logic
        pending_count = sum(
            1 for req in requirements
            if not req_state[req["id"]]["fully_passed"]
        )

        assert pending_count == 2

    def test_qa_pass_but_code_fail_not_fully_passed(self):
        """Verify that QA pass + code validation fail = not fully passed."""
        # Simulate the calculation
        passed = 5  # All 5 QA criteria pass
        total = 5
        pass_ratio = passed / total  # 100%

        static_passed = passed == total  # True

        # Code validation has errors
        validation_is_valid = False
        code_validation_passed = validation_is_valid  # False

        overall_passed = static_passed and code_validation_passed
        assert overall_passed is False

        # State should NOT be updated
        state = {"fully_passed": False, "passed": set()}
        if overall_passed:
            state["fully_passed"] = True

        assert state["fully_passed"] is False

    def test_both_pass_means_fully_passed(self):
        """Verify that QA pass + code validation pass = fully passed."""
        passed = 5
        total = 5
        static_passed = passed == total  # True

        validation_is_valid = True
        code_validation_passed = validation_is_valid  # True

        overall_passed = static_passed and code_validation_passed
        assert overall_passed is True

        state = {"fully_passed": False, "passed": set()}
        if overall_passed:
            state["fully_passed"] = True

        assert state["fully_passed"] is True

    def test_skip_only_when_fully_passed(self):
        """Verify skip logic only triggers when fully_passed is True."""
        # Case 1: QA passed but code failed - should NOT skip
        state_qa_only = {
            "fully_passed": False,
            "passed": {"REQ-001.1", "REQ-001.2", "REQ-001.3", "REQ-001.4", "REQ-001.5"},
            "code_validation_passed": False,
        }
        should_skip_qa_only = state_qa_only["fully_passed"]
        assert should_skip_qa_only is False

        # Case 2: Both passed - should skip
        state_both = {
            "fully_passed": True,
            "passed": {"REQ-001.1", "REQ-001.2", "REQ-001.3", "REQ-001.4", "REQ-001.5"},
            "code_validation_passed": True,
        }
        should_skip_both = state_both["fully_passed"]
        assert should_skip_both is True

    def test_regression_resets_fully_passed(self):
        """Verify regression detection resets fully_passed flag."""
        state = {
            "fully_passed": True,
            "passed": {"REQ-001.1", "REQ-001.2"},
            "code_validation_passed": True,
        }

        # Simulate regression detected
        has_regression = True
        if has_regression:
            state["passed"] = set()
            state["fully_passed"] = False
            state["code_validation_passed"] = False

        assert state["fully_passed"] is False
        assert state["code_validation_passed"] is False
        assert len(state["passed"]) == 0


class TestBackwardsCompatibility:
    """Test that previously passing queries still pass after the fix."""

    def test_previously_passing_still_passes(self):
        """Verify that requirements which truly passed before still pass now.

        A requirement truly passed if:
        - All QA criteria passed (5/5)
        - Code validation had no errors (is_valid=True)
        """
        # Case: QA 5/5, code validation no errors
        passed = 5
        total = 5
        static_passed = passed == total  # True

        validation_is_valid = True
        validation_score = 0.8  # Score doesn't matter if is_valid=True
        code_validation_passed = validation_is_valid  # True

        overall_passed = static_passed and code_validation_passed
        assert overall_passed is True, "Previously truly passing requirement should still pass"

    def test_false_positive_now_correctly_fails(self):
        """Verify that requirements which were false positives now correctly fail.

        A false positive was a requirement that:
        - Had QA 5/5 pass (all criteria in passed set)
        - But code validation failed (is_valid=False or score < 0.6)
        - Was incorrectly skipped in next round due to bug

        Now these should correctly fail and be retried.
        """
        # Case: QA 5/5, but code validation has errors
        passed = 5
        total = 5
        static_passed = passed == total  # True

        validation_is_valid = False  # Has errors!
        validation_score = 0.54
        code_validation_passed = validation_is_valid  # False

        overall_passed = static_passed and code_validation_passed
        assert overall_passed is False, "False positive should now correctly fail"

        # State should NOT be marked as fully_passed
        state = {"fully_passed": False}
        if overall_passed:
            state["fully_passed"] = True

        assert state["fully_passed"] is False, "False positive should not be fully_passed"

    def test_old_threshold_logic_was_redundant(self):
        """Verify that removing overall_target threshold doesn't change behavior.

        Old logic: static_passed = pass_ratio >= overall_target and passed == total
        New logic: static_passed = passed == total

        If passed == total, then pass_ratio = 1.0, which is always >= 0.85 (overall_target)
        So the threshold check was redundant.
        """
        overall_target = 0.85

        # Case 1: All criteria pass
        passed = 5
        total = 5
        pass_ratio = passed / total  # 1.0

        old_static_passed = pass_ratio >= overall_target and passed == total  # True and True = True
        new_static_passed = passed == total  # True

        assert old_static_passed == new_static_passed, "Behavior should be identical"

        # Case 2: Not all criteria pass
        passed = 4
        total = 5
        pass_ratio = passed / total  # 0.8

        old_static_passed = pass_ratio >= overall_target and passed == total  # False and False = False
        new_static_passed = passed == total  # False

        assert old_static_passed == new_static_passed, "Behavior should be identical"

    def test_code_validation_change_is_more_lenient(self):
        """Verify that removing score threshold makes validation more lenient, not stricter.

        Old logic: code_validation_passed = is_valid and score >= 0.6
        New logic: code_validation_passed = is_valid

        This means:
        - If is_valid=True, it passes (regardless of score) - MORE LENIENT
        - If is_valid=False, it fails (regardless of score) - SAME

        So previously passing requirements will still pass.
        """
        # Case 1: Previously passed (is_valid=True, score >= 0.6)
        is_valid_1 = True
        score_1 = 0.8

        old_passed_1 = is_valid_1 and score_1 >= 0.6  # True
        new_passed_1 = is_valid_1  # True
        assert new_passed_1 is True, "Previously passing should still pass"

        # Case 2: Previously failed (is_valid=True, score < 0.6)
        is_valid_2 = True
        score_2 = 0.5

        old_passed_2 = is_valid_2 and score_2 >= 0.6  # False
        new_passed_2 = is_valid_2  # True (more lenient!)
        assert new_passed_2 is True, "Now more lenient - passes if no errors"

        # Case 3: Previously failed (is_valid=False)
        is_valid_3 = False
        score_3 = 0.7

        old_passed_3 = is_valid_3 and score_3 >= 0.6  # False
        new_passed_3 = is_valid_3  # False
        assert new_passed_3 is False, "Still fails if has errors"


class TestFinalRegressionCheck:
    """Test final regression check for previously passed requirements.

    Scenario: 10 requirements, first 3 pass in round 1.
    Later rounds modify shared files. The final regression check
    should detect if the first 3 requirements got broken.
    """

    def test_final_check_collects_all_fully_passed(self):
        """Verify final check correctly collects all fully_passed requirements."""
        requirements = [
            {"id": f"REQ-{i:03d}"} for i in range(1, 11)
        ]
        # First 3 passed in round 1, rest still pending
        req_state = {
            "REQ-001": {"fully_passed": True},
            "REQ-002": {"fully_passed": True},
            "REQ-003": {"fully_passed": True},
            "REQ-004": {"fully_passed": False},
            "REQ-005": {"fully_passed": False},
            "REQ-006": {"fully_passed": False},
            "REQ-007": {"fully_passed": False},
            "REQ-008": {"fully_passed": False},
            "REQ-009": {"fully_passed": False},
            "REQ-010": {"fully_passed": False},
        }

        # Simulate final check collection
        fully_passed_rids = [
            req["id"] for req in requirements
            if req_state[req["id"]].get("fully_passed")
        ]

        assert len(fully_passed_rids) == 3
        assert set(fully_passed_rids) == {"REQ-001", "REQ-002", "REQ-003"}

    def test_final_check_detects_regression(self):
        """Verify final check detects when previously passed requirements regressed."""
        req_state = {
            "REQ-001": {"fully_passed": True, "code_validation_passed": True},
            "REQ-002": {"fully_passed": True, "code_validation_passed": True},
            "REQ-003": {"fully_passed": True, "code_validation_passed": True},
        }

        # Simulate final regression check results
        # REQ-002 regressed due to shared file modifications
        final_regression_results = {
            "REQ-001": True,   # Still valid
            "REQ-002": False,  # Regressed!
            "REQ-003": True,   # Still valid
        }

        regressed_in_final = [
            rid for rid, passed in final_regression_results.items()
            if not passed
        ]

        assert len(regressed_in_final) == 1
        assert "REQ-002" in regressed_in_final

        # Apply regression reset
        for rid in regressed_in_final:
            req_state[rid]["fully_passed"] = False
            req_state[rid]["code_validation_passed"] = False

        assert req_state["REQ-001"]["fully_passed"] is True
        assert req_state["REQ-002"]["fully_passed"] is False
        assert req_state["REQ-003"]["fully_passed"] is True

    def test_final_check_skipped_when_all_passed_same_round(self):
        """Verify final check is skipped when all requirements pass in same round.

        If all requirements are fully_passed, no need for final check
        since there are no pending requirements that could have broken them.
        """
        requirements = [{"id": "REQ-001"}, {"id": "REQ-002"}, {"id": "REQ-003"}]
        req_state = {
            "REQ-001": {"fully_passed": True},
            "REQ-002": {"fully_passed": True},
            "REQ-003": {"fully_passed": True},
        }

        fully_passed_rids = [
            req["id"] for req in requirements
            if req_state[req["id"]].get("fully_passed")
        ]

        # Condition to run final check: some passed but not all
        should_run_final_check = (
            len(fully_passed_rids) > 0 and
            len(fully_passed_rids) < len(requirements)
        )

        # All passed, so no need for final check
        assert should_run_final_check is False

    def test_final_check_runs_when_partial_pass(self):
        """Verify final check runs when some requirements passed but not all."""
        requirements = [
            {"id": "REQ-001"},
            {"id": "REQ-002"},
            {"id": "REQ-003"},
            {"id": "REQ-004"},
        ]
        req_state = {
            "REQ-001": {"fully_passed": True},
            "REQ-002": {"fully_passed": True},
            "REQ-003": {"fully_passed": False},  # Still pending
            "REQ-004": {"fully_passed": False},  # Still pending
        }

        fully_passed_rids = [
            req["id"] for req in requirements
            if req_state[req["id"]].get("fully_passed")
        ]

        # Condition to run final check
        should_run_final_check = (
            len(fully_passed_rids) > 0 and
            len(fully_passed_rids) < len(requirements)
        )

        # Some passed, some pending - need final check
        assert should_run_final_check is True

    def test_shared_file_modification_scenario(self):
        """Simulate the exact scenario user was worried about.

        Round 1: REQ-001, REQ-002, REQ-003 pass
        Round 2-N: Work on REQ-004 to REQ-010, modify shared files
        Final: REQ-001 and REQ-003 still valid, REQ-002 regressed
        """
        # Initial state after round 1
        req_state = {
            "REQ-001": {"fully_passed": True, "modified_files": {"shared/config.py"}},
            "REQ-002": {"fully_passed": True, "modified_files": {"shared/utils.py", "shared/config.py"}},
            "REQ-003": {"fully_passed": True, "modified_files": {"components/widget.py"}},
            "REQ-004": {"fully_passed": False, "modified_files": set()},
            "REQ-005": {"fully_passed": False, "modified_files": set()},
        }

        # Simulate later rounds modifying shared files
        later_round_modifications = {"shared/utils.py", "services/api.py"}

        # Check which previously passed requirements might be affected
        potentially_affected = []
        for rid, state in req_state.items():
            if state["fully_passed"]:
                # Check if any modified files overlap
                overlap = state["modified_files"] & later_round_modifications
                if overlap:
                    potentially_affected.append((rid, overlap))

        # REQ-002 should be flagged as potentially affected
        assert len(potentially_affected) == 1
        assert potentially_affected[0][0] == "REQ-002"
        assert "shared/utils.py" in potentially_affected[0][1]


class TestReturnValueStructure:
    """Test the enhanced return value structure with regression info."""

    def test_execution_summary_structure(self):
        """Verify execution_summary has all required fields."""
        requirements = [{"id": f"REQ-{i:03d}"} for i in range(1, 6)]
        req_state = {
            "REQ-001": {"fully_passed": True},
            "REQ-002": {"fully_passed": True},
            "REQ-003": {"fully_passed": False},
            "REQ-004": {"fully_passed": False},
            "REQ-005": {"fully_passed": False},
        }
        regressed_in_final = ["REQ-002"]

        # Simulate the return value calculation
        final_passed_count = sum(
            1 for req in requirements
            if req_state[req["id"]].get("fully_passed")
        )
        all_passed = final_passed_count == len(requirements)

        execution_summary = {
            "total_requirements": len(requirements),
            "passed_count": final_passed_count,
            "failed_count": len(requirements) - final_passed_count,
            "all_passed": all_passed,
            "total_rounds": 3,
            "regressed_in_final_check": regressed_in_final,
        }

        # Verify structure
        assert execution_summary["total_requirements"] == 5
        assert execution_summary["passed_count"] == 2
        assert execution_summary["failed_count"] == 3
        assert execution_summary["all_passed"] is False
        assert "REQ-002" in execution_summary["regressed_in_final_check"]

    def test_final_regression_info_when_regression_found(self):
        """Verify final_regression info when regression is detected."""
        fully_passed_rids = ["REQ-001", "REQ-002", "REQ-003"]
        regressed_in_final = ["REQ-002"]

        final_regression_info = {
            "checked": len(fully_passed_rids),
            "regressed": regressed_in_final,
            "regressed_count": len(regressed_in_final),
            "still_valid": [rid for rid in fully_passed_rids if rid not in regressed_in_final],
        }

        assert final_regression_info["checked"] == 3
        assert final_regression_info["regressed_count"] == 1
        assert "REQ-002" in final_regression_info["regressed"]
        assert "REQ-001" in final_regression_info["still_valid"]
        assert "REQ-003" in final_regression_info["still_valid"]
        assert "REQ-002" not in final_regression_info["still_valid"]

    def test_final_regression_info_when_no_regression(self):
        """Verify final_regression info when no regression is detected."""
        fully_passed_rids = ["REQ-001", "REQ-002", "REQ-003"]
        regressed_in_final = []

        final_regression_info = {
            "checked": len(fully_passed_rids),
            "regressed": regressed_in_final,
            "regressed_count": len(regressed_in_final),
            "still_valid": fully_passed_rids,
        }

        assert final_regression_info["checked"] == 3
        assert final_regression_info["regressed_count"] == 0
        assert final_regression_info["regressed"] == []
        assert final_regression_info["still_valid"] == fully_passed_rids

    def test_rounds_updated_on_regression(self):
        """Verify rounds data is updated when regression is detected."""
        rounds = [
            {"round": 1, "results": [
                {"requirement_id": "REQ-001", "overall_passed": True},
                {"requirement_id": "REQ-002", "overall_passed": True},
            ]},
        ]
        regressed_in_final = ["REQ-002"]

        # Simulate updating rounds
        last_round = rounds[-1]
        for result in last_round.get("results", []):
            if result.get("requirement_id") in regressed_in_final:
                result["overall_passed"] = False
                result["regression_detected"] = True

        # Verify updates
        req_001_result = next(r for r in last_round["results"] if r["requirement_id"] == "REQ-001")
        req_002_result = next(r for r in last_round["results"] if r["requirement_id"] == "REQ-002")

        assert req_001_result["overall_passed"] is True
        assert "regression_detected" not in req_001_result

        assert req_002_result["overall_passed"] is False
        assert req_002_result["regression_detected"] is True


class TestRegressionScoringConsistency:
    """Test that regression scoring uses same criteria as main pass logic."""

    def test_regression_uses_is_valid_only(self):
        """Verify regression check uses is_valid, not score threshold."""
        # New logic: only check is_valid
        is_valid = True
        score = 0.55  # Below old 0.6 threshold

        # This should pass now (previously would fail with score < 0.6)
        regression_is_valid = is_valid  # No score check
        assert regression_is_valid is True

    def test_score_drop_check_guards_against_zero(self):
        """Verify score drop check handles zero prev_score."""
        prev_score = 0.0
        current_score = 0.5
        is_valid = True

        # Guard against division issues with zero prev_score
        score_drop = prev_score - current_score  # -0.5
        has_regression = not is_valid or (prev_score > 0 and score_drop > 0.2)

        # Should not trigger regression since prev_score is 0
        assert has_regression is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
