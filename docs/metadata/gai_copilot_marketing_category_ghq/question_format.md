Extract arguments from the user question for the function `get_factual_analysis`.

Arguments:
[year, period, period_type, brand, sub_brand, country, zone, market_maturity, macrocategory, manufacturer, category, sub_category, price_tier, price_tier_aggregated, product_marketing_strategy, style, kpi, analysis_level, age, gender, income, region]

General Rules
- Normalize extracted values to the allowed values for the arguments where the exhaustive list is provided below.
- For dimensions like category, sub_category, brand, manufacturer, etc., where the list of possible values is not exhaustive, always prioritize `ner_heads` over predefined examples. For these dimensions, when an entity exists in `ner_heads`, ALWAYS use the exact `entity_value` from `ner_heads`.
- If the user question implies inclusion of all values for a dimension, set it to "across".

year
- Accept any 4-digit year (e.g., 2022–2026).
- For ranges/comparisons include all years (For example, for 2024 vs 2023 extract [2023, 2024]).
- Extract year only if it is explicitly mentioned in the user question.
- If the user question implies trend or across years, normalize to "across".

period
- Allowed: months (Jan–Dec), quarters (Q1, Q2, Q3, Q4), halves (H1, H2), FY.
- If the user question mentions "quarterly" or "by quarter", extract all quarters - Q1, Q2, Q3, Q4.

period_type
- Allowed: QTR, YTD, half_year, full_year, R3M, R6M, R9M, R12M.
- Use R12M for “rolling 12 months” or “last 12 months”.

brand
- Map using `ner_heads`.
- If the question asks for top 5 / top 10 / best-performing brands/by brands, return across
- Prioritize brand over sub_brand unless the sub_brand is explicitly mentioned.
- For factual global brand queries, use brand with analysis_level: [global_level]. If the user asks for global brands or participation of global brands without naming a specific brand, set brand to "across". Do not map the phrase "global brands" to Product Marketing Strategy.

sub_brand
- Map using `ner_heads`.

country
- Allowed: argentina, belgium, bolivia, brazil, canada, chile, china, colombia, germany, dominican republic, ecuador, france, united kingdom, guatemala, honduras, italy, south korea, mexico, mozambique, nigeria, netherlands, panama, peru, paraguay, el salvador, tanzania, uganda, us, vietnam, south africa, zambia
- Keep lowercase and standardized.

zone
- Allowed: SAZ, APAC, AFR, MAZ, EU, NAZ.
- The zone value must be one of SAZ, APAC, AFR, MAZ, EU, or NAZ. If the user says EUR, Europe, European zone, or Europe zone, set zone to [EU]. Do not output EUR as a zone value.
- Do not extract ABI as zone

market_maturity
- Allowed: M1, M2, M3.

Macrocategory
-Map using `ner_heads`. (For example, alc bevs, alc bevs formal, formal + informal alc bevs.)


manufacturer
- Map using `ner_heads` when present.
- Normalize ABI, AB InBev, AB-INBEV, Anheuser-Busch InBev, and similar aliases to abinbev.
- Normalize Heineken aliases to heineken.
- If the user asks by manufacturer, across manufacturers, manufacturer split, or manufacturer breakdown without naming a specific manufacturer, set manufacturer to "across".
- In category positioning or category comparison questions that contain both "ABI" and a valid zone, treat the zone as the filter and do not extract manufacturer = abinbev.

category
- Map using `ner_heads` (For example, beer, beer + bb, bottled water, carbonated softdrinks, energy drinks, wine, spirits, rtd/cider).
- For factual global category queries, use category with analysis_level: [global_level]. If the user asks by/across global categories or global participation by categories, set category to "across". If the user names a category, such as global beer participation, set category to that named category.

sub_category
- valid options : [specialty beer, alcohoolic beer, conventional beer, non-alcoholic beer, flavoured beer]
select specified sub category mentioned in the question ,if not set as null.

price_tier
- Allowed: super premium, premium, core+, core, value.

price_tier_aggregated
- Use only if the user question explicitly mentions “core co” or “premium co”.


product_marketing_strategy
- Map using `ner_heads` when present.
- Do not interpret "global brands" as Product Marketing Strategy in factual global queries; use brand with analysis_level: [global_level] instead.
- Canonical Product Marketing Strategy values are: mega brand, expansion brand, sustain brand, tail brand.
- Map megabrand, megabrands, mega brands, and mega brand to product_marketing_strategy: [mega brand].
- Map expansion, expansion brands, and expansion brand to product_marketing_strategy: [expansion brand].
- Map sustain, sustain brands, and sustain brand to product_marketing_strategy: [sustain brand].
- Map tail, tail brands, and tail brand to product_marketing_strategy: [tail brand].
- When one of these aliases appears, set product_marketing_strategy to the canonical value and do not set brand to "across" just because the phrase contains brand or brands.
- If no matching `ner_heads` value or explicit alias exists, extract the literal Product Marketing Strategy value exactly from the user question.
- Do not normalize Product Marketing Strategy beyond the explicit alias mappings above.
- Do not classify Product Marketing Strategy values as brand or sub_brand unless `ner_heads` explicitly says so.
- If the user asks for a breakdown by/across Product Marketing Strategy, set product_marketing_strategy to "across".

style
- Map using `ner_heads`.

kpi
- Allowed: participation_p4w, participation_p7d, occasions_p4w, occasions_p7d, servings.
- If the user explicitly mentions P7D with participation, such as P7D participation or participation P7D, use participation_p7d.
- If the user explicitly mentions P7D with occasions, such as P7D occasions or occasions P7D, use occasions_p7d.
- If the user explicitly mentions P4W with participation, or asks for participation without saying P7D, use participation_p4w.
- If the user explicitly mentions P4W with occasions, or asks for occasions without saying P7D, use occasions_p4w.
- If the user does not mention any KPI, do not output the `kpi` argument. Leaving `kpi` absent lets the code return all KPI columns supported by the selected table: participation_p4w, participation_p7d, occasions_p4w, occasions_p7d, and servings. For global brand queries, the supported default set is participation_p4w, occasions_p4w, and servings because P7D is not available there.
- If the user asks for POS, use participation_p4w, occasions_p4w, and servings.
- If the user explicitly asks for servings, use servings.
- If multiple KPI families are requested, return all requested KPI values in a list, using P4W unless P7D is explicitly mentioned for that KPI family.
- Global brand queries (analysis_level: [global_level] with brand and no category, zone, or market_maturity) do not support participation_p7d or occasions_p7d. If the user explicitly asks for P7D on a global brand, preserve the P7D KPI and analysis_level so the function can return the unsupported-KPI message; do not silently convert P7D to P4W. P7D remains allowed for direct, zone, market maturity, and global category queries where the code supports it.

analysis_level
- Allowed: global_level, market_maturity_aggregate, zone_aggregate, cohort_level, direct.
- global_level for global brand or global category aggregation.
- Use analysis_level: [global_level] for factual global brand/category KPI requests such as global participation, global POS, global beer participation, global category/categories, and global brands.
- For global category/category-across questions, set category to the named category or "across". For global brand/global brands questions, set brand to the named brand(s) or "across". Leave country absent unless the user explicitly asks for a country-level query.
- market_maturity_aggregate for aggregation by M1/M2/M3.
- If market_maturity is present (M1, M2, M3), use analysis_level: [market_maturity_aggregate] even when the query asks by age, gender, income, region, or cohorts.
- zone_aggregate for aggregation by zone.
- If a valid zone is present (SAZ, APAC, AFR, MAZ, EU, NAZ), use analysis_level: [zone_aggregate] even when the query asks by age, gender, income, region, or cohorts.
- These scope precedence rules apply for all KPI variants: participation_p4w, participation_p7d, occasions_p4w, occasions_p7d, and servings.
- cohort_level when the user asks for all cohorts or a combined cohort package; this includes age, gender, income, and region cohort cuts.
- direct for brand, manufacturer, country, category, Product Marketing Strategy, or any granular user question including a single cohort dimension such as age, gender, income, or region.

age, gender, income, region
- Extract the literal phrasing used in the user question.
- Age examples: LDA-24, 18?24.
- Extract LDA entities only when they follow the format LDA-<number> (e.g., LDA-24), as these represent age bands. Do not extract LDA+ or LDA, because it represents the full Legal Drinking Age population (entire dataset) and is not an age band entity.
- Gender: male, female, non-binary, gender fluid, prefer not to say.
- Income: low income, medium income, high income.
- Region is a cohort dimension. Use only unique_values-backed region values. Examples provided so far are USA: Great Lakes, Midwest, Northeast, South Central; Brazil: GEO NORTH, GEO RJ (Rio de Janeiro), GEO SOUTH, GEO SP (S?o Paulo); South Korea: Gangwon, Seoul, Gwangju / Jeolla / Jeju, Incheon / Gyeonggi, Daejeon / Sejong/ Chungcheong. These examples are not exhaustive. Do not invent region values beyond NER or provided unique_values-backed values.
- If the user mentions Incheon as a South Korea region, set region to [Incheon / Gyeonggi].
- If the user asks by region, across regions, regional split, or region breakdown without naming a specific region, set region to "across".
- For zone or market maturity questions, phrases like by age, by gender, by income, and by region should set that cohort argument to [across] while preserving the explicit zone or market_maturity filter.
- Do not extract the generic word "region" or "regions" as a region value.

## Examples
| User Query | Extracted Parameters |
|---|---|
| P7D Participation for Budweiser in Brazil 2024 | country: [brazil], year: [2024], brand: [Budweiser], kpi: [participation_p7d], analysis_level: [direct] |
| Show me occasions in the past 7 days for beer in Mexico | country: [mexico], category: [beer], kpi: [occasions_p7d], analysis_level: [direct] |
| Show me beer participation for males aged 25-34 in Brazil 2024 | country: [brazil], year: [2024], category: [beer], gender: [male], age: [25-34], kpi: [participation_p4w], analysis_level: [direct] |
| Total alc bevs occasions across all cohorts in Mexico 2023 | country: [mexico], year: [2023], macrocategory: [alc bevs], age: [across], gender: [across], income: [across], kpi: [occasions_p4w], analysis_level: [cohort_level] |
| What are the servings for Budweiser in the US for FY 2024? | country: [us], year: [2024], period: [FY], brand: [Budweiser], kpi: [servings], analysis_level: [direct] |
| Trend of participation across years for low income consumers in Argentina | country: [argentina], year: [across], income: [low income], kpi: [participation_p4w], analysis_level: [direct] |
| Participation highlights for Mexico beer + bb Q1 2025 | country: [mexico], year: [2025], period: [Q1], kpi: [participation_p4w], category: [beer + bb], analysis_level: [direct] |
| Key highlights of Argentina beer + bb for FY 2023 | country: [argentina], year: [2023], period: [FY], category: [beer + bb], analysis_level: [direct] |
| What are the beer occasions highlights of Peru 2024? | country: [peru], year: [2024], kpi: [occasions_p4w], category: [beer], analysis_level: [direct] |
| Servings highlights for UK beer + bb Q1 2024 | country: [united kingdom], year: [2024], period: [Q1], kpi: [servings], category: [beer + bb], analysis_level: [direct] |
| Show me beer participation in Mexico 2023 | country: [mexico], year: [2023], category: [beer], kpi: [participation_p4w], analysis_level: [direct] |
| Trend of cider occasions in Argentina across years | country: [argentina], year: [across], category: [cider], kpi: [occasions_p4w], analysis_level: [direct] |
| Breakdown of alc bevs in Brazil 2024 | country: [brazil], year: [2024], macrocategory: [alc bevs], analysis_level: [direct] |
| Compare Budweiser and Corona in us FY 2023 | country: [us], year: [2023], period: [FY], brand: [Budweiser, Corona], kpi: [participation_p4w], analysis_level: [direct] |
| Performance of premium tier beer + bb in Italy Q2 2024 | country: [italy], year: [2024], period: [Q2], category: [beer + bb], price_tier: [premium], analysis_level: [direct] |
| Quarterly performance of premium tier beer in Ecuador | country: [ecuador], period: [Q1, Q2, Q3, Q4], category: [beer], price_tier: [premium], analysis_level: [direct] |
| All brands trend for spirits in Canada | country: [canada], brand: [across], category: [spirits], analysis_level: [direct] |
| Participation by manufacturer in Brazil beer 2024 | country: [brazil], year: [2024], category: [beer], manufacturer: [across], kpi: [participation_p4w], analysis_level: [direct] |
| ABI vs Heineken participation in Mexico beer | country: [mexico], category: [beer], manufacturer: [abinbev, heineken], kpi: [participation_p4w], analysis_level: [direct] |
| Zone comparison for Q1 2024 | period: [Q1], year: [2024], zone: [across], analysis_level: [zone_aggregate] |
| How do M1 markets perform in 2023? | year: [2023], market_maturity: [M1], analysis_level: [market_maturity_aggregate] |
| Participation trend across zones for beer + bb | category: [beer + bb], kpi: [participation_p4w], zone: [across], analysis_level: [zone_aggregate] |
| Show spirits participation among 25–34 in France 2024 | country: [france], year: [2024], category: [spirits], age: [25-34], kpi: [participation_p4w], analysis_level: [direct] |
| Show spirits participation among LDA+ females in France 2024 | country: [france], year: [2024], category: [spirits], kpi: [participation_p4w], analysis_level: [direct] |
| beer + bb occasions for young adults in Germany | country: [germany], category: [beer + bb], age: [lda-24], kpi: [occasions_p4w], analysis_level: [direct] |
| Breakdown by gender for Mexico beer + bb 2023 | country: [mexico], year: [2023], category: [beer + bb], gender: [across], kpi: [participation_p4w], analysis_level: [direct] |
| Mexico beer 2023 by age | country: [mexico], year: [2023], category: [beer], age: [across], kpi: [participation_p4w], analysis_level: [direct] |
| High-income consumers for premium beer in South Africa | country: [south africa], category: [beer], price_tier: [premium], income: [high income], analysis_level: [direct] |
| Rolling 12 months servings for Italy | country: [italy], period_type: [R12M], kpi: [servings], analysis_level: [direct] |
| R3M participation for Nigeria beer + bb | country: [nigeria], period_type: [R3M], category: [beer + bb], kpi: [participation_p4w] , analysis_level: [direct] |
| YTD 2024 highlights for Belgium | country: [belgium], year: [2024], period_type: [YTD], analysis_level: [direct] |
| Compare premium vs value beer occasions across APAC markets in 2023 | zone: [APAC], year: [2023], category: [beer], price_tier: [premium, value], kpi: [occasions_p4w], analysis_level: [zone_aggregate] |
| Top brands by servings across years in Mexico beer | country: [mexico], category: [beer], year: [across], brand: [across], kpi: [servings], analysis_level: [direct] |
| Show participation for alc bevs among 25–34 males in Brazil FY 2024 | country: [brazil], year: [2024], period: [FY], macrocategory: [alc bevs], age: [25-34], gender: [male], kpi: [participation_p4w], analysis_level: [direct] |
| What is the global participation of Corona? | brand: [Corona], kpi: [participation_p4w], analysis_level: [global_level] |
| Show me global servings for Heineken | brand: [Heineken], kpi: [servings], analysis_level: [global_level] |
| Global participation of Heineken and Corona | brand: [Heineken, Corona], kpi: [participation_p4w], analysis_level: [global_level] |
| What is the global P7D participation of Corona? | brand: [Corona], kpi: [participation_p7d], analysis_level: [global_level] |
| Global participation by categories | category: [across], kpi: [participation_p4w], analysis_level: [global_level] |
| Global beer participation | category: [beer], kpi: [participation_p4w], analysis_level: [global_level] |
| Participation of global brands | brand: [across], kpi: [participation_p4w], analysis_level: [global_level] |
| POS of global brands | brand: [across], kpi: [participation_p4w, occasions_p4w, servings], analysis_level: [global_level] |
| POS of global categories | category: [across], kpi: [participation_p4w, occasions_p4w, servings], analysis_level: [global_level] |
| POS of global brand Budweiser | brand: [Budweiser], kpi: [participation_p4w, occasions_p4w, servings], analysis_level: [global_level] |

| Which country has the highest servings for beer + bb | country: [across], kpi: [servings], category: [beer + bb], analysis_level: [direct] |
| Global zone participation for beer + bb 2024 | zone: [across], category: [beer + bb], year: [2024], kpi: [participation_p4w], analysis_level: [zone_aggregate] |
| Global market maturity occasions for M1 markets | market_maturity: [M1], kpi: [occasions_p4w], analysis_level: [market_maturity_aggregate] |

| Beer participation by region in Brazil 2024 | country: [brazil], year: [2024], category: [beer], region: [across], kpi: [participation_p4w], analysis_level: [direct] |
| Beer participation in GEO NORTH region in Brazil | country: [brazil], category: [beer], region: [GEO NORTH], kpi: [participation_p4w], analysis_level: [direct] |
| Participation by region for beer in NAZ | zone: [NAZ], category: [beer], region: [across], kpi: [participation_p4w], analysis_level: [zone_aggregate] |
| Beer participation by age in NAZ | zone: [NAZ], category: [beer], age: [across], kpi: [participation_p4w], analysis_level: [zone_aggregate] |
| Beer participation by gender in NAZ | zone: [NAZ], category: [beer], gender: [across], kpi: [participation_p4w], analysis_level: [zone_aggregate] |
| Beer participation by income in NAZ | zone: [NAZ], category: [beer], income: [across], kpi: [participation_p4w], analysis_level: [zone_aggregate] |
| Beer participation among LDA-24 in NAZ | zone: [NAZ], category: [beer], age: [lda-24], kpi: [participation_p4w], analysis_level: [zone_aggregate] |
| Beer participation by age in M1 markets | market_maturity: [M1], category: [beer], age: [across], kpi: [participation_p4w], analysis_level: [market_maturity_aggregate] |
| Servings by region for beer in M1 markets | market_maturity: [M1], category: [beer], region: [across], kpi: [servings], analysis_level: [market_maturity_aggregate] |
| Beer participation by age in EU | zone: [EU], category: [beer], age: [across], kpi: [participation_p4w], analysis_level: [zone_aggregate] |
| Beer participation by age in Europe zone | zone: [EU], category: [beer], age: [across], kpi: [participation_p4w], analysis_level: [zone_aggregate] |
| Beer participation by age in EUR | zone: [EU], category: [beer], age: [across], kpi: [participation_p4w], analysis_level: [zone_aggregate] |
| Beer participation in Incheon region in South Korea | country: [south korea], category: [beer], region: [Incheon / Gyeonggi], kpi: [participation_p4w], analysis_level: [direct] |
| Beer POS by age in M1 markets | market_maturity: [M1], category: [beer], age: [across], kpi: [participation_p4w, occasions_p4w, servings], analysis_level: [market_maturity_aggregate] |
| Occasions by age in NAZ | zone: [NAZ], age: [across], kpi: [occasions_p4w], analysis_level: [zone_aggregate] |
| P7D participation by gender in NAZ | zone: [NAZ], gender: [across], kpi: [participation_p7d], analysis_level: [zone_aggregate] |
| beer and abi positioned against other alcohol categories in APAC| zone: [APAC], category: [across], analysis_level: [zone_aggregate], kpi: [participation_p4w, occasions_p4w, servings] |
| P7D occasions by age in M1 markets | market_maturity: [M1], age: [across], kpi: [occasions_p7d], analysis_level: [market_maturity_aggregate] |
| Occasions by region in M2 markets | market_maturity: [M2], region: [across], kpi: [occasions_p4w], analysis_level: [market_maturity_aggregate] |
| P7D participation by income in M3 markets | market_maturity: [M3], income: [across], kpi: [participation_p7d], analysis_level: [market_maturity_aggregate] |
| Participation by product marketing strategy in Mexico | country: [mexico], product_marketing_strategy: [across], kpi: [participation_p4w], analysis_level: [direct] |
| POS of megabrands in Brazil | country: [brazil], product_marketing_strategy: [mega brand], kpi: [participation_p4w, occasions_p4w, servings], analysis_level: [direct] |
| Participation of expansion brands in Mexico | country: [mexico], product_marketing_strategy: [expansion brand], kpi: [participation_p4w], analysis_level: [direct] |
| Occasions of sustain brands in Peru | country: [peru], product_marketing_strategy: [sustain brand], kpi: [occasions_p4w], analysis_level: [direct] |
| POS of tail brands in Colombia | country: [colombia], product_marketing_strategy: [tail brand], kpi: [participation_p4w, occasions_p4w, servings], analysis_level: [direct] |
| POS by product marketing strategy in Brazil | country: [brazil], product_marketing_strategy: [across], kpi: [participation_p4w, occasions_p4w, servings], analysis_level: [direct] |

| Participation by product marketing strategy x region in Mexico | country: [mexico], product_marketing_strategy: [across], region: [across], kpi: [participation_p4w], analysis_level: [direct] |
| Participation for expansion brand beer in Mexico 2024 | country: [mexico], year: [2024], category: [beer], product_marketing_strategy: [expansion brand], kpi: [participation_p4w], analysis_level: [direct] |
| Participation for sustain brand beer in GEO RJ (Rio de Janeiro) region in Brazil | country: [brazil], category: [beer], product_marketing_strategy: [sustain brand], region: [GEO RJ (Rio de Janeiro)], kpi: [participation_p4w], analysis_level: [direct] |
| Participation by brands in Brazil | country: [brazil], category: [beer], brands: [across], kpi: [participation_p4w], analysis_level: [direct] |
