from typing import Optional

from sklearn.ensemble import BaggingRegressor, AdaBoostRegressor
from sklearn.tree import DecisionTreeRegressor
import numpy as np

from bvp.data.models.forecasting.model_spec_factory import create_initial_model_specs

"""
Ensemble models.
"""

# update this version if small things like parametrisation change
version: int = 1
# if a forecasting job using this model fails, fall back on this one
fallback_model_search_term: Optional[str] = "linear-OLS"


def adaboost_decision_tree_specs_configurator(**args):
    """Create and customize initial specs with OLS. See model__spec_factory for param docs."""
    model_specs = create_initial_model_specs(**args)
    model_specs.set_model(
        (
            AdaBoostRegressor,
            dict(
                base_estimator=DecisionTreeRegressor(max_depth=4),
                n_estimators=300,
                random_state=np.random.RandomState(1),
            ),
        )
    )
    model_identifier = "AdaBoost Decision Tree model (v%d)" % version
    return model_specs, model_identifier, fallback_model_search_term


def bagging_decision_tree_specs_configurator(**args):
    """Create and customize initial specs with OLS. See model__spec_factory for param docs."""
    model_specs = create_initial_model_specs(**args)
    model_specs.set_model(
        (
            BaggingRegressor,
            dict(
                base_estimator=DecisionTreeRegressor(max_depth=4),
                n_estimators=300,
                random_state=np.random.RandomState(1),
            ),
        )
    )
    model_identifier = "Bagging Decision Tree model (v%d)" % version
    return model_specs, model_identifier, fallback_model_search_term
