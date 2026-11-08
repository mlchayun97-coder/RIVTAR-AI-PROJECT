# RIVATAR – Data Insights

## Data quality
- Raw rows: **1530**, clean rows: **1472** (58 removed).
- `drop_duplicate_event_ids`: {'removed': 30}
- `normalize_category_spellings`: {'unknown_values': {}}
- `derive_client_type_from_event_type`: {'corrected': 6}
- `normalize_yes_no_flags`: {'columns': ['extra_lighting', 'extra_photography', 'extra_music_talent', 'extra_shuttles', 'extra_social_promo']}
- `parse_mixed_date_formats`: {'formats': ['%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d']}
- `drop_missing_or_non_positive_budget`: {'removed': 21}
- `drop_rows_without_event_type_or_dates`: {'removed': 0}
- `drop_event_before_inquiry`: {'removed': 7}
- `impute_guest_count_by_event_type_median`: {'impossible_values_nulled': 32, 'missing_imputed': 67}
- `impute_categoricals`: {'imputed': {'catering_level': 40, 'region': 33, 'venue_type': 0, 'design_package': 0, 'private_event_at_company_office(->hall)': 0, 'lead_source(->unknown)': 0}}

## Key findings
1. **Event type drives budget.** `wedding` has the highest median budget (₪167,600); `business_dinner` the lowest (₪62,800).
2. **Guest count is the strongest numeric driver** (correlation 0.778). Median spend per guest is ₪550.
3. **Design package matters:** luxury median ₪153,050 vs standard ₪103,400. Catering luxury ₪154,100 vs basic ₪101,300.
4. **Location:** events abroad have median ₪182,950; Jerusalem ₪123,900.
5. **Seasonality:** peak months (May, Jun, Sep, Oct) median ₪132,175 vs other months ₪121,200.
6. **Services with the largest lift:** `extra_music_talent` (+17.8%), `extra_photography` (+15.8%), `extra_lighting` (+1.4%).
7. **The target is right-skewed** (skew 1.234; after log -0.17), so the modelling team should train on log(budget).

## Recommendations for the modelling team
- Use guest_count, event_type, design_package, catering_level, region, venue_type and the extra-service flags.
- Derive season / weekday / lead time from the dates; do not feed raw dates.
- `client_type` is fully determined by `event_type` – keep one of them to avoid redundancy.
- `event_id` and `lead_source` should not influence price; exclude them from features.

## Analyst narrative (LLM agent)

- **Diverse Clientele**: The significant variation in event budgets, with a mean of **$134,121.3** and a range from **$23,700** to **$439,400**, indicates that RIVATAR caters to a diverse clientele. This diversity allows for tailored pricing strategies and package offerings to meet varying client needs.

- **Guest Count Correlation**: The strong positive correlation (0.778) between guest count and budget suggests that RIVATAR should consider upselling services based on guest count. As events grow in size, clients may be more inclined to invest in additional services, enhancing overall revenue.

- **Event Type Pricing Strategy**: The variability in median budgets by event type highlights the need for differentiated pricing strategies. For instance, weddings command higher budgets compared to business dinners, suggesting that RIVATAR could develop specialized packages for different event types to maximize profitability.

- **Value of Extra Services**: The notable budget increases associated with extra services (e.g., **15.8% lift** for photography and **17.8% lift** for music talent) indicate that RIVATAR should actively promote these upsell opportunities. Bundling these services into packages could enhance client satisfaction and increase overall event budgets.

- **Seasonal Trends**: The analysis of seasonal budget trends reveals October as a peak month for higher-budget events. RIVATAR could leverage this insight by launching targeted marketing campaigns or special packages during this period to capitalize on increased client spending.
