import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure backend directory is in path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import rules
from main import app

client = TestClient(app)


def test_healthz():
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"ok": True}


def test_budget_hard_cap_enforcement():
    # Executive candidate with budget of $200
    signals = {
        "career_stage": "executive",
        "target_roles": "Chief Technology Officer",
        "timeline": "urgent",
        "budget": 200,  # Below Executive ($699) and Professional ($349)
        "prior_resume_work": "diy",
        "self_promotion_comfort": "medium"
    }

    rec = rules.recommend(signals)
    # The deterministic rules MUST cap at Essentials ($149)
    assert rec["package"] == "essentials"
    assert rec["price"] <= 200
    assert rec["price"] == 149


def test_budget_hard_cap_mid_budget():
    # Executive candidate with budget of $500
    signals = {
        "career_stage": "executive",
        "target_roles": "VP of Engineering",
        "timeline": "weeks",
        "budget": 500,
        "prior_resume_work": "diy",
        "self_promotion_comfort": "high"
    }

    rec = rules.recommend(signals)
    # Executive ($699) exceeds $500, so it must return Professional ($349)
    assert rec["package"] == "professional"
    assert rec["price"] == 349
    assert rec["price"] <= 500


def test_upgrade_eligibility_multi_role():
    # Entry candidate targeting 2+ roles with sufficient budget ($400)
    signals = {
        "career_stage": "entry",
        "target_roles": "Frontend Developer, Backend Engineer",
        "timeline": "weeks",
        "budget": 400,
        "prior_resume_work": "diy",
        "self_promotion_comfort": "medium"
    }

    rec = rules.recommend(signals)
    # Base for entry is Essentials ($149), but multi-role + budget $400 triggers upgrade to Professional ($349)
    assert rec["package"] == "professional"
    assert rec["upgrade_offered"] is True
    assert rec["price"] == 349


def test_upgrade_eligibility_low_comfort():
    # Senior candidate with low comfort promoting themselves and $1000 budget
    signals = {
        "career_stage": "senior",
        "target_roles": "Staff Software Engineer",
        "timeline": "weeks",
        "budget": 1000,
        "prior_resume_work": "diy",
        "self_promotion_comfort": "low"
    }

    rec = rules.recommend(signals)
    # Base for senior is Professional ($349), but low comfort + high budget triggers upgrade to Executive ($699)
    assert rec["package"] == "executive"
    assert rec["upgrade_offered"] is True
    assert rec["price"] == 699


def test_chat_endpoint_turn():
    session_id = "test_session_123"
    res = client.post(
        "/chat",
        json={"session_id": session_id, "message": "I am an executive VP of Product targeting CTO roles with a $500 budget."}
    )
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert "done" in data
