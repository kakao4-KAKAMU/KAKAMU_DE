from __future__ import annotations

from src.recommend.bandit import ThompsonBandit
from src.recommend.policy import RecommendPolicy
from src.recommend.reward_aggregator import reward_from_action


def test_reward_mapping() -> None:
    assert reward_from_action("like") == 3.0
    assert reward_from_action("skip") == -1.0


def test_bandit_updates() -> None:
    b = ThompsonBandit()
    b.update("baseline", "default", 1.0)
    st = b.get_state("baseline", "default")
    assert st.alpha > 1.0


def test_policy_baseline_share() -> None:
    from src.config.settings import BanditSettings

    policy = RecommendPolicy(settings=BanditSettings(baseline_min_share=1.0))
    w = policy.select_weights(user_id="u1")
    assert w["w_vec"] == 0.55
