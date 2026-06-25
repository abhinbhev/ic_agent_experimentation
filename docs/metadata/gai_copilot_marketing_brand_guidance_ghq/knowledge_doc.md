# Brand Guidance Knowledge Document
## Contents

- [About One Way Marketing](#about-one-way-marketing)
- [About the Domain and KPIs](#about-the-domain-and-kpis)
- [Available Granularities](#available-granularities)
  - [Brand Level](#brand-level)
  - [Brand Family Level](#brand-family-level)
  - [Country Level](#country-level)
  - [Global Level](#global-level)
- [Supported Analyses Today](#supported-analyses-today)
  - [Factual Data](#factual-data)
  - [DOP (Drivers of Power)](#dop-drivers-of-power)
  - [DOS (Drivers of Salience)](#dos-drivers-of-salience)
  - [DOM/DOD (Drivers of Meaningful/Drivers of Difference)](#domdod-drivers-of-meaningfuldrivers-of-difference)
  - [Country Highlights](#country-highlights)
  - [Global Highlights](#global-highlights)
- [Unsupported Analyses Today](#unsupported-analyses-today)
  - [Contributions of MDS](#contributions-of-mds)
  - [Contributions of DOS](#contributions-of-dos)
  - [Significance Testing](#significance-testing)
  - [Forecasting](#forecasting)
  - [External KPIs](#external-kpis)
  - [Superiority](#superiority)
- [Glossary](#glossary)

---

## About One Way Marketing

**One Way Marketing** is **Anheuser-Busch InBev’s unified marketing framework** designed to drive sustainable brand growth by aligning strategy, consumer understanding, brand building, innovation, execution, and value creation into one consistent approach.
---
## The 7 Pillars of One Way Marketing
1. **Category**
   Identify key category opportunities to lead and grow the market.
2. **Consumer**
   Deeply understand who our target consumers are and what drives them.
3. **Portfolio & Brand**
   Prioritize brands and platforms that can drive growth at scale.
4. **Innovation**
   Develop sustainable innovations that meet evolving consumer needs.
5. **Connections & Creativity**
   Build strong consumer connections through impactful creative and media.
6. **Trade Execution**
   Ensure strong in-market execution to drive growth at the point of purchase.
7. **Value Creation**
   Deliver sustainable business and brand value over the long term.

# Brand and Portfolio

## About the Domain and KPIs

- **Brand Guidance** (also called Brand and Portfolio) is a survey-based study designed by Kantar to quantify the mental share of brands in a market using a KPI called **Brand Power**. Brand Power is a 100-sum metric across all brands in a market. It is considered a proxy for predicted volume share in a market with respect to consumer mental perception.
- Brand Power is affected mainly by 3 KPIs — **Meaningful**, **Difference**, and **Salience** (MDS). These KPIs are further affected by other sub-KPIs like Affinity, Meet Needs, Unique, and Dynamic (AMUD), Consumption metrics/funnel (P4W, P3M, P7D), Awareness, Imageries, In-Market Facilitators/Barriers (IMFs), Consideration, Brand Clarity, etc.
  - **Affinity** and **Meet Needs** (AM) are sub-KPIs of **Meaningful**.
  - **Unique** and **Dynamic** (UD) are sub-KPIs of **Difference**.
- These KPIs are available at the brand level at various time periods and demographic cohorts.
- The calculations of these metrics — especially aggregations across time periods, countries, and zones — are extremely sensitive to decimal precision. Therefore, they are precalculated in the dataset.
- This study refreshes at a lag. Assumptions about data availability can be made at a lag of one quarter. For example, if we are in Q2, the latest data available would be Q1.
- Power is the only KPI available at aggregations beyond brand level, since it is summable at the same granularity.

---

## Available Granularities

- This section covers the precalculated granularities available in the dataset. These values are precalculated to avoid decimal errors.
- If a question requests anything within these granularities, avoid calculating anything and defer to the `analysis_tool`.
- Calculations outside these available granularities are not recommended. Basic calculations like delta will be provided by the `analysis_tool`.

### Brand Level

- **KPIs:** All KPIs are available — Power, Meaningful, Difference, Salience, Affinity, Meet Needs, Unique, Dynamic, Premium, Top of Mind, Awareness, Spontaneous Awareness, Trial, P4W, P3M, P7D, Consideration, Worth, Cost, Total Brand Communication Awareness, Brand Clarity, Imageries, and In-Market Facilitators (IMFs).
- **Time periods:** All time periods are available:
  - **MTH** — Monthly
  - **YTD** — Year to Date
  - **R3M** — Rolling 3 Months
  - **R6M** — Rolling 6 Months
  - **R12M** — Rolling 12 Months (also known as MAT — Moving Annual Total)
  - **FY** — Full Year
  - **H1** — First Half
  - **H2** — Second Half
  - **QTR** — Quarterly
- **Demographics:** All 4 demographic cohorts (age, gender, income, region) are available.
- **Markets:** Top 32 Markets/Countries.
- **Brands:** Over 600 brands with hierarchy.
- **Filters:** Brand attribute filters (such as ABI (AB InBev, this company)/competitor, price tier, portfolio classification, or life cycle).

### Brand Family Level

> **Note:** This level is only answerable when the user specifically asks for the family in the query.

- **KPIs:** Only Power KPI available.
- **Time periods:** All time periods are available (MTH, YTD, R3M, R6M, R12M, FY, H1, H2, QTR).
- **Demographics:** All 4 demographic cohorts (age, gender, income, region) are available.
- **Markets:** Top 32 Markets/Countries.

### Country Level

> **Note:** At times, the user simply assumes total ABI Power as the power of the country.

- **KPIs:** Only Power KPI available.
- **Time periods:** All time periods are available (MTH, YTD, R3M, R6M, R12M, FY, H1, H2, QTR).
- **Demographics:** All 4 demographic cohorts (age, gender, income, region) are available.
- **Markets:** Top 32 Markets/Countries.
- **Filters:** Aggregations at brand attribute filters (such as ABI/competitor, price tier, portfolio classification, or life cycle).

### Global Level

> **Note:** At times, the user simply assumes total ABI Power as global power.

- **KPIs:** Only Power KPI available.
- **Global brands:** 5 Global brands — Corona, Michelob Ultra, Budweiser, Stella Artois, Heineken (Competitor).
- **Home markets:** The 4 global brands of ABI each have their home market. This is the default calculation:

  | Brand          | Home Market |
  |----------------|-------------|
  | Budweiser      | US          |
  | Stella Artois  | Belgium     |
  | Corona         | Mexico      |
  | Michelob Ultra | US          |
  | Heineken       | Netherlands |

- A "without home market" calculation for the 4 ABI global brands is also readily available. Make sure to check the home market for the brand.
- **Time periods:** All time periods are available (MTH, YTD, R3M, R6M, R12M, FY, H1, H2, QTR).
- **Demographics:** Only 3 demographic cohorts (age, gender, income) are available.
- **Zone aggregations:** NAZ (North Americas), SAZ (South Americas), MAZ (Middle Americas), APAC (Asia Pacific), AFR (Africa), and EUR (Europe).
- **Market maturity levels:** M1, M2, M3 (in increasing order of maturity).
- **Filters:** Aggregations at attribute filters (such as ABI/competitor, price tier, portfolio classification, or life cycle).

---

## Supported Analyses Today

### Factual Data

- This function is primarily responsible for fetching any cut of the data based on the inputs.
- It should be called separately multiple times if the query involves multiple countries, KPIs, or time periods.
- It supports returning multiple brands or trends within a time period (like multiple quarters under QTR, etc.) at the same time, as long as the granularity and KPI are the same.

### DOP (Drivers of Power)

- This function provides a pre-curated analysis built to understand all the factors and KPIs that determine why Power is changing at a brand level.
- It accepts only 1 country, brand, and year/time period at a time. It automatically calculates delta with the previous year.
- Currently only available for FY, H1, H2, and Quarterly time periods.
- It only requires the Power KPI in the query.

### DOS (Drivers of Salience)

- This function provides a pre-curated analysis built to understand all the factors and KPIs that determine why Salience is changing at a brand level.
- Alternative ways of asking this question include: physical availability, mental availability, price perception, pack availability, trade visibility, brand clarity, spontaneous awareness, trade execution (P4W).
- It accepts only 1 country, brand, and year/time period at a time. It automatically calculates delta with the previous year.
- Currently only available for FY, H1, H2, and Quarterly time periods.
- It only requires the Salience KPI in the query.

### DOM/DOD (Drivers of Meaningful / Drivers of Difference)

- This function provides a pre-curated analysis built to understand all the factors and KPIs that determine why Meaningful or Difference is changing at a brand level.
- It accepts only 1 country, brand, and year/time period at a time. It automatically calculates delta with the previous year.
- **This analysis is still a work in progress and should be conveyed as such to the user.**
- Currently only available for FY, H1, H2, and Quarterly time periods.
- It only requires the Meaningful or Difference KPI in the query.

### Country Highlights

- This function covers all necessary granularities to explain the performance of a country.
- It accepts only 1 country and year/time period at a time. It automatically calculates delta with the previous year.
- Currently only available for FY, H1, H2, and Quarterly time periods.

### Global Highlights

- This function covers all necessary granularities to explain global ABI performance.
- This function cannot solve for global performance of individual brands or competitors, that should end up as a factual data question.
- It accepts only 1 year/time period at a time. It automatically calculates delta with the previous year.
- Currently only available for FY, H1, H2, and Quarterly time periods.

---

## Unsupported Analyses Today

The following analyses are **not currently supported** and should not be attempted:

### Contributions of MDS

- MDS (Meaningful, Difference, Salience) contributions to Power.
- Also referred to as BSA (Brand Structure Analysis).
- Imagery contributions.

### Contributions of DOS

- Mental and physical availability contributions.

### Significance Testing

- Statistical significance testing of KPI changes is not available.

### Forecasting

- Forward-looking projections or forecasts of KPIs are not supported.

### External KPIs

- SOV (Share of Voice)
- Media principles
- Market Share
- WD (Weighted Distribution)
- Creative scores / brand linkage

### Superiority

- Superiority analysis is not currently available.

---

## Glossary

| Term / Abbreviation | Definition |
|----------------------|------------|
| **Brand Power** | A 100-sum metric across all brands in a market; a proxy for predicted volume share based on consumer mental perception. |
| **MDS** | Meaningful, Difference, and Salience — the three primary KPIs that drive Brand Power. |
| **MDSP** | Meaningful, Difference, Salience, and Power — a shorthand for all four core Brand Guidance KPIs together. When a user asks for "MDSP", retrieve Power, Meaningful, Difference, and Salience. |
| **Meaningful** | A KPI measuring how well a brand meets consumer needs and builds affinity. |
| **Difference** | A KPI measuring how distinct or unique a brand is perceived to be. |
| **Salience** | How quickly and easily a brand comes to mind in buying situations. When Salience is above 120 (indexed), mental availability becomes a more significant driver than physical availability for further growth. |
| **AMUD** | Affinity, Meet Needs, Unique, and Dynamic — sub-KPIs that feed into MDS. |
| **IMFs** | In-Market Facilitators/Barriers — factors like trade visibility, price perception, and pack availability. |
| **P4W / P3M / P7D** | Consumption funnel time frames — Past 4 Weeks, Past 3 Months, Past 7 Days. |
| **ABI** | AB InBev (Anheuser-Busch InBev) — this company. |
| **DOP** | Drivers of Power — a pre-curated analysis explaining why Power is changing. |
| **DOS** | Drivers of Salience — a pre-curated analysis explaining why Salience is changing. |
| **DOM** | Drivers of Meaningful — a pre-curated analysis explaining why Meaningful is changing. |
| **DOD** | Drivers of Difference — a pre-curated analysis explaining why Difference is changing. |
| **BSA** | Brand Structure Analysis — another term for MDS contributions to Power. |
| **SOV** | Share of Voice. |
| **WD** | Weighted Distribution. |
| **MTH** | Monthly time period. |
| **YTD** | Year to Date. |
| **R3M / R6M / R12M** | Rolling 3 Months / Rolling 6 Months / Rolling 12 Months or Moving Annual Tool (MAT). |
| **FY** | Full Year. |
| **H1 / H2** | First Half / Second Half of the year. |
| **QTR** | Quarterly time period. |
| **NAZ** | North Americas zone. |
| **SAZ** | South Americas zone. |
| **MAZ** | Middle Americas zone. |
| **APAC** | Asia Pacific zone. |
| **AFR** | Africa zone. |
| **EUR** | Europe zone. |
| **M1 / M2 / M3** | Market maturity levels (M1 = lowest, M3 = highest maturity). |

## Usecase definitions

This section defines all KPIs and measures available in the dataset.
Each entry includes **definition**, **scale or calculation rule**, and a **sample query** at brand–country level.

---

### A) Equity Framework KPIs

#### **Power**
- **Definition:** Prediction of volume share a brand can command based on consumer predisposition to choose the brand over others.
- **Scale:** Within a market, Power sums to 100 across all brands (both ABI and competitor brands combined).
- **Example query:** *What is the Power of Budweiser in Brazil in FY 2024?*

#### **Meaning**
- **Definition:** Extent to which brands build an emotional connection and are seen to deliver against functional needs.
- **Scale:** Indexed at 100 within a market.
- **Example query:** *Show the Meaning trend of Corona in Mexico from 2020 to 2025.*

#### **Difference**
- **Definition:** Extent to which brands set themselves apart from the category by offering something others do not and by leading the way.
- **Scale:** Indexed at 100 within a market.
- **Example query:** *What is the Difference score of Skol in Brazil across age cohorts in 2024?*

#### **Salience**
- **Definition:** How quickly and easily the brand comes to mind.
- **Scale:** Indexed at 100 within a market.
- **Example query:** *Compare the Salience of Heineken in Netherlands across regions in FY 2023.*

#### **Premium**
- **Definition:** Prediction of price index a brand can support based on consumer predisposition to pay more for the brand than others.
- **Scale:** Indexed at 1 within a market.
- **Example query:** *What is the Premium score of Stella Artois in UK in Q2 2025?*

---

### B) Emotional and Functional Equity Sub-scores

#### **Affinity**
- **Definition:** Emotional connection with the consumer.
- **Scale:** Likert scale ranging from -3 to 3.
- **Example query:** *What is the Affinity score of Corona in Mexico across gender cohorts in FY 2024?*

#### **Meet Needs**
- **Definition:** Fulfillment of functional needs of the consumer.
- **Scale:** Likert scale ranging from 1 to 7.
- **Example query:** *Show the Meet Needs score of Budweiser in US by income cohorts in FY 2025.*

#### **Unique**
- **Definition:** Extent to which brands set themselves apart from others.
- **Scale:** Likert scale ranging from 1 to 7.
- **Example query:** *What is the Unique score of Heineken in Germany across regions in 2024?*

#### **Dynamic**
- **Definition:** Degree to which the brand is trend-setting.
- **Scale:** Likert scale ranging from 1 to 7.
- **Example query:** *Show the Dynamic score trend of Cass Fresh in South Korea from 2022 to 2025.*

---

### C) Funnel Metrics

#### **Top of Mind**
- **Definition:** First brand to come to mind.
- **Example query:** *What is the Top of Mind score of Quilmes in Argentina in Q1 2025?*

#### **Awareness**
- **Definition:** Familiarity with a brand.
- **Example query:** *What is the Awareness level of Skol in Brazil in FY 2024?*

#### **Spontaneous Awareness**
- **Definition:** Measure of how people recall a brand without any help. Also known as **unaided awareness**.
- **Example query:** *What is the Spontaneous Awareness of Stella Artois in Belgium in FY 2023?*

#### **Trial**
- **Definition:** Trial rate of the brand (ever tried).
- **Example query:** *What is the Trial score of Corona in Mexico in FY 2024?*

#### **P3M, P4W, P7D**
- **Definition:** Consumption incidence in the past 3 months (P3M), 4 weeks (P4W), or 7 days (P7D).
- **Example query:** *What is the P3M consumption of Budweiser in US in FY 2024?*

#### **Consideration**
- **Definition:** Likelihood to choose a brand next time.
- **Scale:** 5-point Likert scale.
- **Example query:** *What is the Consideration score of Heineken in Netherlands in Q2 2025?*

---

### D) Brand Associations and Drivers

#### **Imagery**
- **Definition:** Brand associations of a consumer, based on specific imagery statements. Examples of imagery statements include:
  - Is in vogue
  - Is preferred by younger people
  - It's a brand that makes me feel confident
  - Makes an occasion more special
  - It's a daring brand
  - Is brewed with care
  - It's a creative brand
  - Adds energy to your social occasion
  - Is good to drink when you want to relax
  - Is a high quality brand
  - It's a brand that highlights myself from the others
  - Perfectly balances lightness and flavor

  *Note: Imagery statements vary by market.*
- **Example query:** *What is the Imagery score for “ADDS ENERGY TO YOUR SOCIAL OCCASION” for Quilmes in Argentina in Q1 2025?*

#### **In Market Facilitators (IMF)**
- **Definition:** Attribute-level factors driving choice of a brand. Examples of IMF attributes include:
  - It was displayed prominently
  - It was easily available at the places I go to
  - It was easy to find
  - It was at a good price
  - It was a product I had not tried before
  - Other brand(s) I usually buy were not available
  - It was refrigerated
  - I liked the packaging
  - It had promotional material displayed

  *Note: IMF attributes may vary by market.*
- **Example query:** *What are the IMF scores of Budweiser in US in FY 2024?*

#### **Most Likely Occasion**
- **Definition:** Occasion most likely associated with beer consumption.
- **Example query:** *What is the Most Likely Occasion score of Corona in Mexico in FY 2025?*

#### **First Brand Occasion**
- **Definition:** First brand to come to mind for a given occasion.
- **Example query:** *What is the First Brand Occasion score of Skol in Brazil for party occasions in FY 2024?*

---

### E) Perceptions of Worth and Cost

#### **Worth**
- **Definition:** Worth perception of the brand.
- **Scale:** Likert scale ranging from 1 to 3.
- **Example query:** *What is the Worth score of Heineken in Netherlands in FY 2025?*

#### **Cost**
- **Definition:** Cost perception of the brand.
- **Scale:** Likert scale ranging from 1 to 7.
- **Example query:** *What is the Cost score of Cass Fresh in South Korea in Q3 2024?*

---

### F) Communication Awareness

#### **Total Brand Communication Awareness**
- **Definition:** Whether consumers have seen, heard, or read about the brand.
- **Example query:** *What is the Total Brand Communication Awareness of Budweiser in Canada in FY 2023?*
