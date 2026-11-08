# Model Card – RIVATAR Event Budget Estimator

_Generated 2026-11-08 16:08 UTC_

## Model details
- **Selected version:** `v1_ridge_baseline` – decided by **Model Trainer agent (gpt-4o-mini)**
- **Why:** I chose the Ridge Baseline model (v1) due to its CV MAPE of 7.94%, which is well below the 25% threshold. It also has the lowest CV MAE of 10711.50 and a complexity score of 1, making it the simplest and most interpretable model.
- **Selection policy:** Only models with CV MAPE below 25% may be published. Among those, prefer the simpler model unless a more complex one lowers CV MAE by more than 5%: a simpler model is easier to explain to a producer and less likely to overfit. Policy rule would choose `v1_ridge_baseline` (agrees).
- **Task:** regression – estimate total event budget in ILS (₪) from the lead's event details
- **Target transform:** trained on log1p(budget), predictions converted back with expm1
- **Random seed:** 42 · **CV:** 5-fold · **Train / test:** 1177 / 295
- **Libraries:** Python 3.12.10, scikit-learn 1.9.1, pandas 3.1.0

## Intended use
- Give RIVATAR's producers a **first budget range** when a lead fills the website contact form,
  before the first call: a starting point, not a quote. It supports – it does not replace – a producer's quote.
- **Out of scope:** binding price quotes, events larger than 1,500 guests, event types not in training data.

## Training data
- Dataset `rivatar_events_clean` v1.0.0, 1472 rows,
  sha256 `bd3a0fc838e48ccc…`
- **Synthetic data** (seed 42) generated to mimic a luxury event-production business (see `src/rivatar/data_generator.py`).
  Validated against the JSON data contract before training.

## Model comparison
| Version | CV MAE (₪) | CV MAPE | Hold-out MAE (₪) | Hold-out MAPE | Hold-out R² |
|---|---|---|---|---|---|
| `v1_ridge_baseline` | 10,711 ± 884 | 7.9% | 10,614 | 7.8% | 0.928 |
| `v2_random_forest` | 16,726 ± 984 | 12.6% | 17,865 | 12.9% | 0.806 |
| `v3_hist_gradient_boosting` | 13,006 ± 657 | 9.7% | 12,873 | 9.0% | 0.901 |

## Performance of the selected model (hold-out)
- MAE **₪10,614**, RMSE ₪17,735, MAPE **7.8%**, R² **0.928**
- 80% of hold-out predictions fall between **-12% and +12%** of the true budget –
  the app shows this as the estimate range.
- Quality gate (MAPE < 25%): **PASSED**

### Error by event type
| Event type | n | MAE (₪) | MAPE |
|---|---|---|---|
| bar_mitzvah | 39 | 9,436 | 7.1% |
| bat_mitzvah | 31 | 6,945 | 6.5% |
| business_dinner | 20 | 6,710 | 10.8% |
| conference | 31 | 13,332 | 8.7% |
| corporate_event | 35 | 11,608 | 8.3% |
| family_event | 26 | 6,054 | 9.4% |
| product_launch | 28 | 7,873 | 6.9% |
| wedding | 85 | 14,308 | 7.2% |

### Most important features (MAE increase when shuffled, ₪)
| Feature | Δ MAE |
|---|---|
| log_guests | 32,290 |
| catering_level | 9,583 |
| event_type | 8,944 |
| guest_count | 6,774 |
| design_package | 5,334 |
| region | 5,293 |
| venue_type | 4,572 |
| extra_music_talent | 1,639 |

## Reproducibility
- Retrained from scratch with the same seed: metrics identical = **True** (max diff 0.00e+00)
- Re-run: `python -m rivatar.main --offline` reproduces data, contract, model and this card.

## Limitations and risks
- Trained on **synthetic** data: absolute numbers illustrate the method, they are not real RIVATAR prices.
- Small segments (e.g. business dinners, events abroad) have fewer examples and wider errors.
- Prices drift with inflation and supplier costs; the model should be retrained on real, recent events.
- `lead_source` is deliberately excluded so the estimate does not depend on how the client found RIVATAR.
- Hold-out metrics for every version are reported, but the publishing decision uses CV results only, so the hold-out set stays unseen.

## Evaluator notes (LLM agent)

- The selected model (v1_ridge_baseline) demonstrates a strong performance with a CV MAPE of 7.94%, indicating reliable predictions within the acceptable threshold of 25%.
- Despite its overall effectiveness, the model shows higher MAE values for specific event types, particularly Weddings and Conferences, suggesting a need for further refinement in these areas.
- Producers should utilize the model's predictions with caution for event types with high MAE, as these may lead to less accurate estimates.
- Future iterations of the model could explore additional features or alternative modeling techniques to improve performance on weak segments.
- Continuous monitoring of model performance is recommended, especially as new data becomes available, to ensure its predictions remain valid and reliable.
