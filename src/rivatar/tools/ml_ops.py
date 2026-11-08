"""Deterministic ML operations used by Crew 2 (ML Team). Ported from the ML prototype.

`build_features` is the single source of truth for feature engineering:
training, evaluation and the Streamlit app all call it, so a prediction in
the app goes through exactly the same transformation as training data.
"""
from __future__ import annotations

import json
import platform
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from rivatar import config
from rivatar.tools.data_ops import SERVICES, file_sha256

CAT_FEATURES = ["event_type", "region", "venue_type", "catering_level", "design_package", "season"]
NUM_FEATURES = ["guest_count", "log_guests", "lead_days", "services_count", "month", "weekday",
                "is_thursday", "is_friday", "is_rush"]
BOOL_FEATURES = SERVICES
ALL_FEATURES = CAT_FEATURES + NUM_FEATURES + BOOL_FEATURES
EXCLUDED = [config.ID_COLUMN, "client_type", "lead_source", "inquiry_date", "event_date"]


def _season(month: int) -> str:
    return {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
            6: "summer", 7: "summer", 8: "summer"}.get(month, "autumn")


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Raw/clean event rows -> model feature table (no target)."""
    out = pd.DataFrame(index=df.index)
    inq = pd.to_datetime(df["inquiry_date"])
    evt = pd.to_datetime(df["event_date"])
    for c in ["event_type", "region", "venue_type", "catering_level", "design_package"]:
        out[c] = df[c].astype(str)
    out["guest_count"] = df["guest_count"].astype(float)
    out["log_guests"] = np.log1p(out["guest_count"])
    out["lead_days"] = (evt - inq).dt.days.astype(float)
    out["month"] = evt.dt.month
    out["weekday"] = evt.dt.day_of_week
    out["season"] = out["month"].map(_season)
    out["is_thursday"] = (out["weekday"] == 3).astype(int)
    out["is_friday"] = (out["weekday"] == 4).astype(int)
    out["is_rush"] = (out["lead_days"] < 45).astype(int)
    for s in SERVICES:
        out[s] = df[s].map(lambda v: str(v).strip().lower() in ("true", "1", "1.0", "yes")).astype(int)
    out["services_count"] = out[SERVICES].sum(axis=1)
    return out[ALL_FEATURES]


def prepare_features(clean_path=config.CLEAN_DATA, spec_path=config.FEATURES_SPEC) -> dict:
    df = pd.read_csv(clean_path)
    X = build_features(df)
    spec = {
        "categorical": CAT_FEATURES, "numeric": NUM_FEATURES, "boolean": BOOL_FEATURES,
        "excluded": EXCLUDED, "target": config.TARGET, "target_transform": "log1p",
        "n_rows": int(len(X)), "n_features": len(ALL_FEATURES),
        "derived": {
            "log_guests": "log1p(guest_count)", "lead_days": "event_date - inquiry_date",
            "month/weekday/season": "from event_date", "is_thursday/is_friday": "weekday flags",
            "is_rush": "lead_days < 45", "services_count": "sum of 5 service flags",
        },
        "null_check": {k: int(v) for k, v in X.isna().sum().items()},
    }
    if any(spec["null_check"].values()):
        raise ValueError(f"features contain nulls: {spec['null_check']}")
    spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return spec


def _model_versions(seed: int) -> dict[str, Pipeline]:
    onehot = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT_FEATURES),
        ("num", StandardScaler(), NUM_FEATURES + BOOL_FEATURES),
    ])
    ordinal = ColumnTransformer([
        ("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1), CAT_FEATURES),
        ("num", "passthrough", NUM_FEATURES + BOOL_FEATURES),
    ])

    def wrap(pre, model):
        return TransformedTargetRegressor(
            regressor=Pipeline([("pre", pre), ("model", model)]), func=np.log1p, inverse_func=np.expm1)

    n_cat = len(CAT_FEATURES)
    return {
        "v1_ridge_baseline": wrap(onehot, Ridge(alpha=1.0)),
        "v2_random_forest": wrap(ordinal, RandomForestRegressor(
            n_estimators=300, min_samples_leaf=2, random_state=seed, n_jobs=1)),
        "v3_hist_gradient_boosting": wrap(ordinal, HistGradientBoostingRegressor(
            max_iter=400, learning_rate=0.05, max_leaf_nodes=31, l2_regularization=0.1,
            categorical_features=list(range(n_cat)), random_state=seed)),
    }


def _metrics(y_true, y_pred) -> dict:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mape": float(mean_absolute_percentage_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def _split(seed: int, clean_path=config.CLEAN_DATA):
    df = pd.read_csv(clean_path)
    X, y = build_features(df), df[config.TARGET].astype(float)
    return train_test_split(X, y, test_size=config.TEST_SIZE, random_state=seed, stratify=df["event_type"])


# Simpler first: the order the selection policy prefers when models are close.
COMPLEXITY = {"v1_ridge_baseline": 1, "v2_random_forest": 2, "v3_hist_gradient_boosting": 3}
SELECTION_POLICY = (
    f"Only models with CV MAPE below {config.MAX_ALLOWED_MAPE:.0%} may be published. Among those, prefer the "
    f"simpler model unless a more complex one lowers CV MAE by more than {config.SIMPLER_MODEL_MARGIN:.0%}: "
    "a simpler model is easier to explain to a producer and less likely to overfit.")


class ModelDecisionError(ValueError):
    """A model choice that the policy does not allow (unknown version or failing MAPE)."""


def compare_models(seed: int = config.SEED, out_path=config.MODEL_COMPARISON) -> dict:
    """Cross-validate every model version on the training split. Does NOT pick or save a model:
    choosing the version to publish is a decision (see decide_model / publish_model)."""
    X_tr, X_te, y_tr, y_te = _split(seed)
    cv = KFold(n_splits=config.CV_FOLDS, shuffle=True, random_state=seed)
    results = {}
    for name, model in _model_versions(seed).items():
        cvr = cross_validate(model, X_tr, y_tr, cv=cv, scoring={
            "mae": "neg_mean_absolute_error", "mape": "neg_mean_absolute_percentage_error", "r2": "r2"})
        results[name] = {
            "complexity": COMPLEXITY[name],
            "cv_mae_mean": float(-cvr["test_mae"].mean()), "cv_mae_std": float(cvr["test_mae"].std()),
            "cv_mape_mean": float(-cvr["test_mape"].mean()), "cv_r2_mean": float(cvr["test_r2"].mean()),
        }
    lowest = min(results, key=lambda k: results[k]["cv_mae_mean"])
    comparison = {
        "seed": seed, "n_train": int(len(X_tr)), "n_test": int(len(X_te)), "cv_folds": config.CV_FOLDS,
        "results": results, "lowest_cv_mae": lowest, "selection_policy": SELECTION_POLICY,
    }
    out_path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    return comparison


def policy_choice(comparison: dict) -> tuple[str, str]:
    """The selection policy as a deterministic rule: used offline, and to check the agent's choice."""
    res = comparison["results"]
    allowed = sorted((n for n in res if res[n]["cv_mape_mean"] < config.MAX_ALLOWED_MAPE),
                     key=lambda n: res[n]["complexity"])
    if not allowed:
        raise ModelDecisionError("no model version has CV MAPE below the allowed maximum")
    chosen = allowed[0]
    for cand in allowed[1:]:
        gain = 1 - res[cand]["cv_mae_mean"] / res[chosen]["cv_mae_mean"]
        if gain > config.SIMPLER_MODEL_MARGIN:
            chosen = cand
    lowest = min(allowed, key=lambda n: res[n]["cv_mae_mean"])
    if chosen == lowest:
        reason = f"`{chosen}` has the lowest CV MAE (₪{res[chosen]['cv_mae_mean']:,.0f}) and passes the MAPE limit."
    else:
        gain = 1 - res[lowest]["cv_mae_mean"] / res[chosen]["cv_mae_mean"]
        reason = (f"`{lowest}` is only {gain:.1%} better on CV MAE than the simpler `{chosen}` "
                  f"(margin {config.SIMPLER_MODEL_MARGIN:.0%}), so the simpler model is kept.")
    return chosen, reason


def publish_model(model_name: str, reason: str, decided_by: str, seed: int = config.SEED,
                  comparison_path=config.MODEL_COMPARISON, model_path=config.MODEL_FILE,
                  decision_path=config.MODEL_DECISION) -> dict:
    """Fit the chosen version on the training split and save it, with a record of who decided and why.
    Refuses a choice the policy forbids, so a decision can never publish a failing model."""
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    res = comparison["results"]
    model_name = model_name.strip().strip("`")
    if model_name not in res:
        raise ModelDecisionError(f"unknown model version {model_name!r}; choose one of {sorted(res)}")
    if res[model_name]["cv_mape_mean"] >= config.MAX_ALLOWED_MAPE:
        raise ModelDecisionError(f"{model_name} has CV MAPE {res[model_name]['cv_mape_mean']:.1%}, "
                                 f"not below {config.MAX_ALLOWED_MAPE:.0%}")
    rule_choice, rule_reason = policy_choice(comparison)
    X_tr, X_te, y_tr, y_te = _split(seed)
    model = _model_versions(seed)[model_name].fit(X_tr, y_tr)
    joblib.dump({"model": model, "name": model_name, "features": ALL_FEATURES, "seed": seed}, model_path)
    decision = {
        "decision": "which model version to publish",
        "chosen_model": model_name,
        "reason": reason.strip(),
        "decided_by": decided_by,
        "policy": SELECTION_POLICY,
        "policy_rule_choice": rule_choice,
        "policy_rule_reason": rule_reason,
        "agrees_with_policy_rule": model_name == rule_choice,
        "candidates": {n: {k: r[k] for k in ("complexity", "cv_mae_mean", "cv_mape_mean", "cv_r2_mean")}
                       for n, r in res.items()},
    }
    decision_path.write_text(json.dumps(decision, indent=2, ensure_ascii=False), encoding="utf-8")
    return decision


def decide_and_publish_offline(seed: int = config.SEED) -> dict:
    """Offline mode: the same decision, taken by the deterministic policy rule instead of an agent."""
    chosen, reason = policy_choice(json.loads(config.MODEL_COMPARISON.read_text(encoding="utf-8")))
    return publish_model(chosen, reason, decided_by="offline policy rule (no LLM)", seed=seed)


def evaluate_model(seed: int = config.SEED, model_path=config.MODEL_FILE, out_path=config.EVALUATION,
                   comparison_path=config.MODEL_COMPARISON) -> dict:
    """Hold-out evaluation of every version + per-segment errors for the best one."""
    X_tr, X_te, y_tr, y_te = _split(seed)
    bundle = joblib.load(model_path)
    best = bundle["model"]
    holdout = {}
    for name, m in _model_versions(seed).items():
        pred = best.predict(X_te) if name == bundle["name"] else m.fit(X_tr, y_tr).predict(X_te)
        holdout[name] = _metrics(y_te, pred)

    pred = best.predict(X_te)
    seg = pd.DataFrame({"event_type": X_te["event_type"], "y": y_te, "p": pred})
    by_type = {k: {"n": int(len(g)), "mae": float(mean_absolute_error(g.y, g.p)),
                   "mape": float(mean_absolute_percentage_error(g.y, g.p))}
               for k, g in seg.groupby("event_type")}

    # permutation-free importance proxy: drop-in error when one feature is shuffled
    rng = np.random.default_rng(seed)
    base_mae = mean_absolute_error(y_te, pred)
    importance = {}
    for f in ALL_FEATURES:
        Xp = X_te.copy()
        Xp[f] = rng.permutation(Xp[f].values)
        importance[f] = float(mean_absolute_error(y_te, best.predict(Xp)) - base_mae)
    importance = dict(sorted(importance.items(), key=lambda kv: -kv[1]))

    residual_rel = (pred - y_te) / y_te
    evaluation = {
        "best_model": bundle["name"], "seed": seed,
        "holdout_metrics": holdout,
        "best_holdout": holdout[bundle["name"]],
        "by_event_type": by_type,
        "permutation_importance_mae_increase": importance,
        "prediction_interval_80pct_relative": [float(np.quantile(residual_rel, 0.1)),
                                                float(np.quantile(residual_rel, 0.9))],
        "quality_gate": {"max_mape": config.MAX_ALLOWED_MAPE,
                         "passed": holdout[bundle["name"]]["mape"] < config.MAX_ALLOWED_MAPE},
    }
    out_path.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    return evaluation


def write_model_card(out_path=config.MODEL_CARD, narrative: str | None = None) -> str:
    comp = json.loads(config.MODEL_COMPARISON.read_text(encoding="utf-8"))
    decision = json.loads(config.MODEL_DECISION.read_text(encoding="utf-8"))
    ev = json.loads(config.EVALUATION.read_text(encoding="utf-8"))
    contract = json.loads(config.DATA_CONTRACT.read_text(encoding="utf-8"))
    repro = json.loads(config.RUN_STATUS.read_text(encoding="utf-8")).get("reproducibility") if config.RUN_STATUS.exists() else None
    notes = config.REPORTS_DIR / "model_card_notes.md"
    if narrative is None and notes.exists():
        narrative = notes.read_text(encoding="utf-8")
    b = ev["best_holdout"]
    lo, hi = ev["prediction_interval_80pct_relative"]

    rows = "\n".join(
        f"| `{n}` | {r['cv_mae_mean']:,.0f} ± {r['cv_mae_std']:,.0f} | {r['cv_mape_mean']:.1%} | "
        f"{ev['holdout_metrics'][n]['mae']:,.0f} | {ev['holdout_metrics'][n]['mape']:.1%} | "
        f"{ev['holdout_metrics'][n]['r2']:.3f} |" for n, r in comp["results"].items())
    seg = "\n".join(f"| {k} | {v['n']} | {v['mae']:,.0f} | {v['mape']:.1%} |" for k, v in ev["by_event_type"].items())
    imp = "\n".join(f"| {k} | {v:,.0f} |" for k, v in list(ev["permutation_importance_mae_increase"].items())[:8])

    text = f"""# Model Card – RIVATAR Event Budget Estimator

_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_

## Model details
- **Selected version:** `{decision['chosen_model']}` – decided by **{decision['decided_by']}**
- **Why:** {decision['reason']}
- **Selection policy:** {decision['policy']} Policy rule would choose `{decision['policy_rule_choice']}` ({'agrees' if decision['agrees_with_policy_rule'] else 'the decision differs; see reports/model_decision.json'}).
- **Task:** regression – estimate total event budget in ILS (₪) from the lead's event details
- **Target transform:** trained on log1p(budget), predictions converted back with expm1
- **Random seed:** {comp['seed']} · **CV:** {comp['cv_folds']}-fold · **Train / test:** {comp['n_train']} / {comp['n_test']}
- **Libraries:** Python {platform.python_version()}, scikit-learn {sklearn.__version__}, pandas {pd.__version__}

## Intended use
- Give RIVATAR's producers a **first budget range** when a lead fills the website contact form,
  before the first call: a starting point, not a quote. It supports – it does not replace – a producer's quote.
- **Out of scope:** binding price quotes, events larger than 1,500 guests, event types not in training data.

## Training data
- Dataset `{contract['contract_name']}` v{contract['version']}, {contract['row_count']} rows,
  sha256 `{contract['dataset_sha256'][:16]}…`
- **Synthetic data** (seed 42) generated to mimic a luxury event-production business (see `src/rivatar/data_generator.py`).
  Validated against the JSON data contract before training.

## Model comparison
| Version | CV MAE (₪) | CV MAPE | Hold-out MAE (₪) | Hold-out MAPE | Hold-out R² |
|---|---|---|---|---|---|
{rows}

## Performance of the selected model (hold-out)
- MAE **₪{b['mae']:,.0f}**, RMSE ₪{b['rmse']:,.0f}, MAPE **{b['mape']:.1%}**, R² **{b['r2']:.3f}**
- 80% of hold-out predictions fall between **{lo:+.0%} and {hi:+.0%}** of the true budget –
  the app shows this as the estimate range.
- Quality gate (MAPE < {config.MAX_ALLOWED_MAPE:.0%}): **{'PASSED' if ev['quality_gate']['passed'] else 'FAILED'}**

### Error by event type
| Event type | n | MAE (₪) | MAPE |
|---|---|---|---|
{seg}

### Most important features (MAE increase when shuffled, ₪)
| Feature | Δ MAE |
|---|---|
{imp}

## Reproducibility
{('- Retrained from scratch with the same seed: metrics identical = **' + str(repro['identical']) + '** (max diff ' + format(repro['max_abs_diff'], '.2e') + ')') if repro else '- Checked by the flow after training (see `reports/run_status.json`).'}
- Re-run: `python -m rivatar.main --offline` reproduces data, contract, model and this card.

## Limitations and risks
- Trained on **synthetic** data: absolute numbers illustrate the method, they are not real RIVATAR prices.
- Small segments (e.g. business dinners, events abroad) have fewer examples and wider errors.
- Prices drift with inflation and supplier costs; the model should be retrained on real, recent events.
- `lead_source` is deliberately excluded so the estimate does not depend on how the client found RIVATAR.
- Hold-out metrics for every version are reported, but the publishing decision uses CV results only, so the hold-out set stays unseen.
"""
    if narrative:
        text += "\n## Evaluator notes (LLM agent)\n\n" + narrative.strip() + "\n"
    out_path.write_text(text, encoding="utf-8")
    return text


def check_reproducibility(seed: int = config.SEED) -> dict:
    """Retrain the selected version from scratch and compare hold-out predictions."""
    bundle = joblib.load(config.MODEL_FILE)
    X_tr, X_te, y_tr, y_te = _split(seed)
    fresh = _model_versions(seed)[bundle["name"]].fit(X_tr, y_tr)
    diff = float(np.max(np.abs(fresh.predict(X_te) - bundle["model"].predict(X_te))))
    return {"model": bundle["name"], "seed": seed, "max_abs_diff": diff,
            "identical": diff <= config.REPRO_TOLERANCE, "data_sha256": file_sha256(config.CLEAN_DATA)}


def load_model():
    return joblib.load(config.MODEL_FILE)


def predict_budget(event: dict) -> dict:
    """Predict one event; returns point estimate and 80% range."""
    bundle = load_model()
    X = build_features(pd.DataFrame([event]))
    p = float(bundle["model"].predict(X)[0])
    ev = json.loads(config.EVALUATION.read_text(encoding="utf-8"))
    lo, hi = ev["prediction_interval_80pct_relative"]
    # residual = (pred - y)/y  =>  y = pred/(1+residual)
    return {"estimate": round(p, -2), "low": round(p / (1 + hi), -2), "high": round(p / (1 + lo), -2),
            "model": bundle["name"]}
