"""
Deterministic recommendation layer.

This is the part of the system that makes the actual decision. The language
model never picks a package -- it only supplies the structured signals (see
extraction.py). The rules below turn those signals into a recommendation, and
the customer's stated budget is enforced here as a hard cap.

Why this lives in code and not in the prompt:
A model that occasionally recommends a package above someone's stated budget
isn't a tuning problem you fix with better prompt wording -- it's a
refund-and-trust problem. So the guardrail goes somewhere it cannot drift.
The model proposes; these rules dispose.

NOTE: the tiers, prices, and thresholds below are illustrative placeholders for
this public reference version. The production decision tree was designed with
the client and is not reproduced here.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Package:
    key: str
    name: str
    price: int  # USD
    summary: str


# Three service tiers, cheapest to most expensive (illustrative).
PACKAGES = [
    Package("essentials", "Essentials", 149, "A polished single-version resume."),
    Package("professional", "Professional", 349, "Resume, cover letter, and LinkedIn refresh."),
    Package("executive", "Executive", 699, "Full rewrite, multi-role targeting, and a strategy call."),
]
BY_KEY = {p.key: p for p in PACKAGES}

# The six signals the conversation collects. Kept here so extraction.py and
# the rules stay in sync.
REQUIRED_SIGNALS = (
    "career_stage",            # "entry" | "mid" | "senior" | "executive"
    "target_roles",            # roles/titles the visitor is targeting
    "timeline",                # "urgent" | "weeks" | "exploring"
    "budget",                  # integer USD the visitor is comfortable spending
    "prior_resume_work",       # "none" | "diy" | "professional"
    "self_promotion_comfort",  # "low" | "medium" | "high"
)


def recommend(signals: dict) -> dict:
    """
    Turn collected signals into a recommendation.

    The budget cap is applied LAST so that it overrides everything above it --
    no path through this function can ever return a package above budget.
    """
    base = _base_recommendation(signals)
    chosen = base
    upgrade_offered = False

    # Consider a genuine upgrade (honest fit, not an upsell)...
    if _is_upgrade_eligible(signals, base):
        higher = _next_tier(base)
        if higher and _affordable(higher, signals.get("budget")):
            chosen = higher
            upgrade_offered = True

    # ...then enforce the budget cap no matter what was chosen above.
    if not _affordable(chosen, signals.get("budget")):
        chosen = _best_affordable(signals.get("budget"))
        upgrade_offered = False

    return {
        "package": chosen.key,
        "name": chosen.name,
        "price": chosen.price,
        "summary": chosen.summary,
        "upgrade_offered": upgrade_offered,
        "reason": _explain(chosen, base, upgrade_offered),
    }


def _base_recommendation(signals: dict) -> Package:
    """Pick a starting tier from career stage. Illustrative mapping."""
    stage = signals.get("career_stage")
    if stage == "executive":
        return BY_KEY["executive"]
    if stage == "senior":
        return BY_KEY["professional"]
    return BY_KEY["essentials"]


def _is_upgrade_eligible(signals: dict, base: Package) -> bool:
    """
    A genuine upgrade candidate is someone the higher tier would actually serve
    better -- targeting several different roles, or low comfort writing about
    themselves (where the strategy call earns its place). About fit, not upsell.
    """
    if base.key == "executive":
        return False
    multi_role = _role_count(signals.get("target_roles")) >= 2
    low_comfort = signals.get("self_promotion_comfort") == "low"
    return multi_role or low_comfort


def _role_count(target_roles) -> int:
    if not target_roles:
        return 0
    if isinstance(target_roles, int):
        return target_roles
    parts = str(target_roles).replace(" and ", ",").split(",")
    return len([p for p in parts if p.strip()])


def _affordable(package: Package, budget) -> bool:
    """Budget is a hard cap. No package over the stated budget, ever."""
    try:
        return package.price <= int(budget)
    except (TypeError, ValueError):
        return True  # budget not known yet -> don't filter on it


def _next_tier(package: Package):
    idx = PACKAGES.index(package)
    return PACKAGES[idx + 1] if idx + 1 < len(PACKAGES) else None


def _best_affordable(budget):
    """Most capable package at or under budget; falls back to the cheapest."""
    affordable = [p for p in PACKAGES if _affordable(p, budget)]
    return affordable[-1] if affordable else PACKAGES[0]


def _explain(chosen, base, upgrade_offered) -> str:
    if upgrade_offered:
        return (f"{chosen.name} fits because you're targeting more than one kind of "
                f"role or want help framing your experience -- and it's within budget.")
    if chosen != base:
        return f"{chosen.name} is the best fit that stays within your stated budget."
    return f"{chosen.name} matches where you are in your search."
