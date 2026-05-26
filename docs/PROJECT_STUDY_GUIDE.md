# Mediq Substitution Tool Study Guide

## 1. Project Overview

This project is a **Streamlit dashboard** for checking whether an external product has a mapped substitute in the Mediq MOB portfolio, and for analyzing substitution coverage, portfolio demand, and substitution gaps.

In simple terms, the tool answers three business questions:

1. Does an external product already have an internal portfolio substitute?
2. Which MOB products or product families appear most important based on requested quantity?
3. Which external products still have no substitute and may represent portfolio gaps or missed opportunities?

This makes the project a good study case for:

- business analytics
- data quality management
- master data integration
- descriptive dashboards
- information visualization
- operational decision support

---

## 2. Business Context

The project combines four CSV datasets:

1. A list of **external products**
2. A list of **MOB portfolio products**
3. A **substitute mapping table** linking external products to MOB products
4. A list of **products without substitute**

The dashboard helps a user:

- search for a single product
- upload a file of external products for bulk matching
- inspect overall substitution coverage
- review sales and demand patterns in the portfolio
- identify categories and product families where substitutes are missing

From a business point of view, this supports:

- product standardization
- purchasing and supply decisions
- portfolio rationalization
- gap analysis
- demand prioritization

---

## 3. Main Learning Value

If you are learning **business analytics** and **information visualization**, this project is useful because it shows how a small data app can connect:

- raw operational data
- data cleaning and normalization
- entity matching
- KPI design
- category-level aggregation
- family-level grouping
- interactive visual analytics

It is not a predictive system. It is mainly a **descriptive and diagnostic analytics** tool.

---

## 4. Project Structure

```text
Mediq Substi Tool/
|-- app.py
|-- requirements.txt
|-- README.md
|-- data/
|   |-- raw_external_products.csv
|   |-- mob_portfolio.csv
|   |-- substitute_database.csv
|   |-- products_without_substitute.csv
|-- src/
|   |-- config.py
|   |-- data_loader.py
|   |-- substitution.py
|   |-- visualization.py
|   |-- utils.py
```

### Why this structure matters

- `app.py` contains the dashboard interface and user interactions.
- `src/config.py` defines dataset schemas and file paths.
- `src/data_loader.py` loads and saves CSV data.
- `src/substitution.py` contains matching and substitution logic.
- `src/visualization.py` calculates KPIs and charts.
- `src/utils.py` contains text normalization helpers.

This is a clean modular design for a small analytics app.

---

## 5. Technology Stack

- **Python**: core programming language
- **Streamlit**: dashboard and interactive UI
- **Pandas**: table handling and analysis
- **Plotly Express**: charts
- **RapidFuzz**: fuzzy matching for product family detection
- **OpenPyXL**: reading Excel uploads

### Why these tools fit the project

- Streamlit is fast for internal analytics dashboards.
- Pandas is strong for CSV-based business data.
- Plotly provides interactive charts without much front-end code.
- RapidFuzz helps group similar product names into product families.

---

## 6. What the App Does

The dashboard has four major functional areas.

### A. Single Product Lookup

The user enters:

- `External ID`
- `External Product Name`

The app filters the merged lookup table and shows:

- matched external product
- category
- requested quantity
- mapped MOB substitute
- MOB category
- size or variant

### B. Bulk External Product Match

The user uploads a CSV or Excel file of external products.

The system then:

1. reads the file
2. standardizes the input columns
3. tries to match rows by external ID first
4. falls back to normalized external product name
5. outputs matched substitute information

### C. Overview Analytics

The app shows summary KPIs and charts for:

- substitution coverage
- portfolio quantity by category
- top MOB families or products
- products without substitute by category
- top missing product families

### D. Admin Panel

The admin panel allows direct editing and importing of the live CSV datasets.

This is important because the dashboard is not only a reporting tool. It also acts as a small **data maintenance interface**.

---

## 7. Data Model

This project uses a simple relational logic built from flat files.

### 7.1 `raw_external_products.csv`

Represents the source list of external products.

Important columns:

- `external_id`: product identifier
- `external_name`: product name
- `manufacturer`
- `category`
- `last_update`
- `qty_requested`: demand quantity
- `source_file`
- `import_date`

Business meaning:
This is the universe of products the organization wants to evaluate against the MOB portfolio.

### 7.2 `mob_portfolio.csv`

Represents internal portfolio products.

Important columns:

- `MOB_ID`
- `MOB_Name`
- `Kategorie`
- `Größe/Variante` in the source file, although parts of the code currently show a mojibake version of that name because of text encoding
- `Aktiv (Y/N)`
- `Last_Updated`
- `Req_Qty_Total`

Business meaning:
This is the portfolio from which substitutes can be chosen.

### 7.3 `substitute_database.csv`

This is the bridge table between external and internal products.

Important columns:

- `external_id`
- `mob_id`
- `source_file`
- `import_date`

Business meaning:
This table defines the substitution relationship.

### 7.4 `products_without_substitute.csv`

Represents external products still lacking a mapped MOB substitute.

Important columns:

- `external_id`
- `external_name`
- `category`
- `qty_requested`
- `created_date`

Business meaning:
This is the backlog or gap list for substitution work.

---

## 8. Data Flow

The data flow is straightforward and easy to study.

### Step 1. Define file schemas

`src/config.py` defines:

- dataset names
- CSV paths
- expected columns
- required columns
- uniqueness rules

This is similar to a lightweight metadata layer.

### Step 2. Load data

`src/data_loader.py`:

- ensures CSV files exist
- reads them with Pandas
- adds missing columns if necessary
- keeps a consistent column order

### Step 3. Merge substitution data

`src/substitution.py`:

1. loads external products
2. loads substitute mappings
3. loads MOB portfolio
4. renames MOB columns into a more dashboard-friendly form
5. merges tables together

Conceptually:

```text
raw_external_products
    LEFT JOIN substitute_database ON external_id
    LEFT JOIN mob_portfolio ON mob_id
```

### Step 4. Calculate analytics

`src/visualization.py`:

- computes metrics
- groups data by category
- groups similar products into families
- returns Plotly chart objects

### Step 5. Display in Streamlit

`app.py` builds the interface and renders:

- inputs
- tables
- KPIs
- charts
- editable admin tabs

---

## 9. Core Analytics Logic

### 9.1 Substitution Coverage

Coverage is calculated as:

```text
linked external products / total external products * 100
```

This is a strong operational KPI because it shows how much of the external product universe has already been mapped to substitutes.

Current data snapshot in this repository:

- External products: `1976`
- Linked substitutes: `1940`
- Coverage rate: `98.2%`

Interpretation:
Coverage is very high, which suggests the substitution database is already quite mature. However, the remaining unmatched products may still be strategically important.

### 9.2 MOB Portfolio Demand

The app uses `Req_Qty_Total` from the MOB portfolio to measure total requested quantity.

Current snapshot:

- Portfolio products: `1861`
- Products with sales quantity above zero: `272`
- Total sales quantity: `237,263,853`

Interpretation:
The portfolio may contain many listed products, but only part of them show measurable request volume. This is useful for Pareto-style analysis.

### 9.3 Gap Analysis

The app tracks external products without substitutes and aggregates their requested quantity.

Current snapshot:

- Products without substitute: `1830`
- Total gap requested quantity: `5,353,228`

Interpretation:
Even with high mapping coverage, the missing-substitute list still contains substantial demand volume. That means count-based coverage and volume-based impact can tell different stories.

This is a very important business analytics lesson.

---

## 10. Product Family Detection

One of the most interesting parts of the project is that it groups similar products into **families**.

This happens in `src/visualization.py` using:

- cleaned product names
- category boundaries
- fuzzy similarity scoring from RapidFuzz

### Why family detection is useful

Raw product names often differ slightly because of:

- spelling variation
- packaging descriptions
- size text
- naming conventions

If analysts only look at exact product names, demand may appear fragmented. Family detection reduces that problem and creates a more strategic view.

### Simplified logic

1. Normalize names
2. Compare names within the same category
3. Use fuzzy similarity scores
4. Assign very similar items to the same family
5. Aggregate quantity at the family level

### Analytics lesson

This is a basic example of **master data harmonization** and **entity grouping**, which are very common in business analytics projects.

---

## 11. Text Normalization and Matching

The project uses text normalization in two places:

1. **Header normalization** for uploaded files
2. **Name normalization** for product matching and grouping

### Header normalization

The system removes accents, lowercases text, and replaces special characters with underscores.

Example:

```text
"Größe/Variante" -> normalized header form used for matching and import handling
```

This makes uploads more robust when source files use different spellings or formats.

It also highlights a real-world data issue in this project: some code references show mojibake such as `GrÃ¶ÃŸe/Variante`, which is a classic encoding problem when UTF-8 text is interpreted incorrectly. That is a valuable data-governance lesson on its own.

### Name normalization

`src/utils.py` converts text to:

- lowercase
- alphanumeric words only
- normalized spacing

This helps compare product names more consistently.

### Matching strategy for uploads

The bulk match feature uses a two-step approach:

1. Match by `external_id`
2. If not found, match by normalized product name

This is a strong design choice because ID matching is more precise, while name matching improves recall.

---

## 12. Information Visualization Design

This app uses simple but effective chart types.

### 12.1 Bar Chart: MOB Sales by Category

Purpose:
Compare total requested quantity across categories.

Why it works:
Bar charts are ideal for comparing magnitudes between discrete categories.

Business question:
Which categories dominate portfolio demand?

### 12.2 Horizontal Bar Chart: Top MOB Families or Products

Purpose:
Show the most important items ranked by total quantity.

Why it works:
Horizontal bars handle long product labels better than vertical bars.

Business question:
Which products or families should be prioritized in substitution strategy or portfolio planning?

### 12.3 Bar Chart: Products Without Substitute by Category

Purpose:
Show where substitution gaps are concentrated.

Why it works:
Category-level comparison highlights structural weaknesses in portfolio coverage.

Business question:
Which categories need new substitute mapping effort?

### 12.4 Horizontal Bar Chart: Top Missing Product Families

Purpose:
Rank the highest-demand families that still have no substitute.

Why it works:
This chart converts a long gap list into a prioritized action view.

Business question:
What should the business solve first?

---

## 13. KPI Interpretation Guide

When studying dashboards, it is important not only to know the formulas, but also how to interpret them.

### External Products

Meaning:
How many unique external products are being considered.

Use:
Shows the size of the substitution scope.

### Linked Substitutes

Meaning:
How many external products already have a mapped MOB substitute.

Use:
Measures mapping progress.

### Coverage Rate %

Meaning:
Share of external products covered by substitute mapping.

Use:
High-level maturity indicator.

Risk:
Can look strong even if high-volume gaps remain.

### Portfolio Products

Meaning:
How many distinct internal MOB products exist.

Use:
Shows portfolio breadth.

### Detected Families

Meaning:
How many grouped product families exist after fuzzy clustering.

Use:
Shows how fragmented or consolidated the portfolio appears at a family level.

### Total Sales Qty

Meaning:
Total requested quantity across MOB items.

Use:
Indicates operational scale.

### Gap Families

Meaning:
Grouped families among products without substitute.

Use:
Helps prioritize missing coverage by broader need, not only by exact SKU.

### Gap Qty Requested

Meaning:
Total demand associated with products that have no substitute.

Use:
Measures the business impact of the substitution gap.

---

## 14. Architecture and Design Assessment

From a software and analytics perspective, the project has several strengths.

### Strengths

- clear modular separation
- simple data pipeline
- low technical overhead
- practical analytics outputs
- editable operational data source
- upload support for CSV and Excel
- useful fallback matching logic

### Limitations

- data is stored only in CSV files, so concurrency and auditability are limited
- the dashboard mixes business logic and UI logic in `app.py`
- there are no automated tests
- there is no database or versioned data history
- fuzzy family detection is heuristic, not validated by a business taxonomy
- name-based matching can produce false positives or false negatives

### What this means analytically

This is a strong prototype or internal operations tool, but not yet a full enterprise-grade data product.

---

## 15. Good Business Analytics Concepts Demonstrated

This project demonstrates many concepts that are useful for your studies.

### Descriptive Analytics

The dashboard summarizes what is happening now:

- current coverage
- category totals
- top products
- current gap list

### Diagnostic Analytics

The charts help explain where the problem is concentrated:

- which categories have missing substitutes
- which products drive the most demand
- how fragmented product naming may be

### Data Quality Management

The app includes:

- required column structure
- uniqueness validation
- missing-column recovery
- normalization of headers and names

### Master Data Mapping

The project links records across systems using identifiers and names.

This is very common in:

- procurement analytics
- ERP integration
- catalog harmonization
- portfolio management

### Prioritization by Volume

The project does not only count records. It also uses quantity to show impact.

That is a core analytics principle:
not every item matters equally.

---

## 16. Study the Code by File

If you want to learn this project step by step, use this reading order.

### 1. `app.py`

Study this first to understand the overall user experience and business workflow.

Focus on:

- input widgets
- metric display
- chart display
- admin panel logic

### 2. `src/config.py`

Study this next to understand the data contracts.

Focus on:

- dataset schema definitions
- expected columns
- uniqueness rules

### 3. `src/data_loader.py`

Study how the app loads and saves data consistently.

Focus on:

- schema preservation
- missing-file handling

### 4. `src/substitution.py`

This is the most important business-logic file.

Focus on:

- lookup creation
- table merging
- bulk upload standardization
- ID-first then name-based matching

### 5. `src/visualization.py`

This is the analytics layer.

Focus on:

- metric formulas
- groupby aggregations
- family detection logic
- chart generation

### 6. `src/utils.py`

Read this last. It is small, but important because normalization supports the matching logic.

---

## 17. Important Code Explanations

This section focuses on the most important implementation ideas in the project and why they are worth learning for future analytics work.

### 17.1 Configuration-Driven Design

One of the strongest design choices is the `DATASETS` dictionary in [src/config.py](../src/config.py).

Why it matters:

- file paths are centralized
- expected columns are centralized
- uniqueness rules are centralized
- other parts of the code can reuse one shared schema definition

What to learn:
Instead of hardcoding dataset details in many files, define a single configuration layer.

Reusable pattern:

```python
DATASETS = {
    "dataset_name": {
        "path": ...,
        "columns": [...],
        "unique_keys": [...],
    }
}
```

Why this helps in your next project:

- easier maintenance
- fewer schema mismatches
- faster onboarding when the project grows

### 17.2 Defensive Data Loading

[src/data_loader.py](../src/data_loader.py) is a good example of defensive programming.

Important idea:
The code does not assume that the CSV already exists or that every expected column is present.

What the loader does:

- creates missing data files
- reads the CSV
- adds any missing columns
- returns data in a fixed column order

Why this is important:
Business data systems are often messy, and dashboards should fail gracefully whenever possible.

Reusable lesson:
Build your ingestion layer to tolerate imperfect input.

### 17.3 Normalize Structure Before Processing

The upload workflow in [app.py](../app.py) and [src/substitution.py](../src/substitution.py) shows a very practical pattern: standardize structure before applying logic.

Important parts:

- `normalize_header()`
- `normalize_uploaded_dataset()`
- `_standardize_external_upload()`

What they do:

- clean column names
- map different header styles into a standard schema
- prepare uploaded files for matching

Why this matters:
Users rarely upload files with exactly the same column names.

What to reuse:

- define column aliases
- normalize headers first
- convert uploads into a controlled internal structure before analysis

### 17.4 Match with Confidence Levels

The bulk matching logic uses a hierarchy:

1. exact `external_id` match
2. normalized `external_name` match
3. `no_match` if both fail

Why this is a smart design:

- exact identifiers are highest confidence
- name matching acts as a useful fallback
- unmatched rows remain visible instead of being hidden

Very important detail:
The output includes `match_method`, which makes the result explainable.

What to learn:
When building matching logic, define a clear trust order and preserve how each match was found.

### 17.5 Normalize Text for Joining and Grouping

The `normalize_text()` function in [src/utils.py](../src/utils.py) is small but strategically important.

It:

- lowercases text
- removes non-alphanumeric characters
- normalizes whitespace

Why it matters:
Small differences in naming can break matching, grouping, and filtering.

Example:

```text
"MoliCare Form 6 Tropfen"
"molicare-form 6 tropfen"
"MOLICARE   FORM 6 Tropfen"
```

These become more consistent after normalization.

Lesson:
Text normalization is one of the highest-value low-complexity steps in many analytics projects.

### 17.6 Separate UI from Analysis Logic

The project uses a useful modular split:

- [app.py](../app.py) for UI
- [src/substitution.py](../src/substitution.py) for matching logic
- [src/visualization.py](../src/visualization.py) for KPIs and charts

Why this matters:
It becomes easier to understand, debug, and reuse logic when the app interface is not doing everything itself.

Practical takeaway:
In your next project, try to keep these layers separate:

- data access
- transformation and business rules
- visualization
- user interface

### 17.7 Treat KPIs as Named Business Rules

Functions such as:

- `substitution_metrics()`
- `mob_sales_metrics()`
- `gap_metrics()`

are good examples of making KPI logic explicit.

Why this matters:

- formulas are easy to inspect
- logic is reusable
- dashboard metrics stay consistent

What to learn:
Do not scatter KPI calculations across many charts. Give them clear function names and one source of truth.

### 17.8 Aggregate Before Visualizing

The charts in [src/visualization.py](../src/visualization.py) are built from summarized data, not directly from raw rows.

Common patterns used:

- `groupby`
- `sum`
- sorting
- top-N filtering

Why this is important:
Most business charts should communicate decision-level summaries rather than raw operational detail.

Key lesson:
The analytical value often comes from the transformation before the chart, not from the chart library alone.

### 17.9 Product Family Detection is a Valuable Pattern

The `_detect_product_families()` function is one of the most reusable ideas in the whole project.

Conceptually it:

1. normalizes product names
2. compares names within the same category
3. uses fuzzy similarity
4. assigns a family label
5. aggregates by family

Why this matters:
Real data often has many name variations for essentially similar items.

What this teaches:
Sometimes the right analytical unit is not the exact record. It is a grouped business concept such as a family, cluster, or category.

### 17.10 Validate Before Saving

The admin panel uses `validate_unique_keys()` before saving edited or imported data.

Why this matters:
Bad data can enter a system through manual editing just as easily as through upstream imports.

What the validation protects against:

- duplicate external product IDs
- duplicate MOB IDs
- duplicate substitute mappings

Reusable lesson:
Any write-back workflow should validate data quality before saving.

### 17.11 Make Outputs Explainable

This project does not only show KPIs. It also shows:

- matching rows
- substitute details
- connected substitutions
- match methods in bulk outputs

Why this matters:
Business users trust analytics tools more when they can trace the result.

What to learn:
Always balance summary metrics with enough detail for verification.

### 17.12 Design for Practical Use

This project uses CSV files, Streamlit, and compact Python modules. It is not an enterprise-scale architecture, but it still delivers clear business value.

Why this is an important lesson:
The best learning projects are often the ones that solve a real workflow with understandable logic.

What to carry forward:
Do not wait for a perfect architecture before building a useful analytics product.

---

## 18. Key Reusable Patterns for Your Next Project

These are the most transferable lessons from this codebase.

### Pattern 1. Central schema configuration

Keep dataset definitions in one place.

### Pattern 2. Robust ingestion

Expect missing files, missing columns, and inconsistent headers.

### Pattern 3. Normalize before matching

Prepare headers, identifiers, and names before joins or comparisons.

### Pattern 4. Layered matching

Use exact rules first, then lower-confidence fallback logic.

### Pattern 5. Validation before write-back

Protect data quality before saving edits or imports.

### Pattern 6. Function-based KPIs

Treat important metrics as named reusable business rules.

### Pattern 7. Aggregate to business level

Turn raw rows into category, family, and top-item summaries.

### Pattern 8. Explainable outputs

Show enough detail that users can understand how results were produced.

### Pattern 9. Data quality is part of analytics design

Encoding issues, inconsistent names, and duplicates are core project concerns, not side issues.

### Pattern 10. Build for decisions

Good dashboards help users decide what action to take next.

---

## 19. Suggested Learning Path for You

Since you are learning **business analytics** and **information visualization**, here is a practical path.

### Phase 1. Understand the business process

Ask:

- What is an external product?
- What is a substitute?
- Why is substitution coverage valuable?
- Why do missing substitutes matter operationally?

### Phase 2. Understand the data model

Ask:

- Which file is the source list?
- Which file is the mapping table?
- Which file is the portfolio reference?
- Which file shows the gap list?

### Phase 3. Understand the KPIs

Ask:

- How is coverage calculated?
- Why can coverage be high while gap demand is still important?
- Which KPI is count-based and which is volume-based?

### Phase 4. Understand the visualizations

Ask:

- Why are bar charts used here?
- Why is ranking helpful?
- Why is family aggregation more strategic than raw SKU counts?

### Phase 5. Understand the data preparation

Ask:

- Why normalize text?
- Why validate unique keys?
- Why standardize uploaded headers?

### Phase 6. Think critically

Ask:

- Where could matching errors happen?
- Which fields are missing for stronger analytics?
- How would you validate family groupings with business users?

---

## 20. Possible Improvements

If you want to extend this project as a learning exercise, these are good next steps.

### Analytics Improvements

- add trend analysis over time
- separate demand by customer or source
- add Pareto charts
- add category contribution percentages
- compare covered demand vs uncovered demand
- add a priority score combining quantity and strategic category

### Visualization Improvements

- add filters for category, manufacturer, and active status
- add drill-down from category to product family
- add KPI tooltips with definitions
- add traffic-light indicators for high-risk gap categories

### Data Engineering Improvements

- move from CSV to a relational database
- keep import history and change logs
- create validation reports for bad IDs and missing names
- add deduplication rules beyond exact unique keys

### Modeling Improvements

- improve fuzzy matching with domain-specific rules
- distinguish exact substitute from approximate substitute
- score match confidence
- create approved product family taxonomy instead of heuristic clustering

---

## 21. Risks and Caveats

Every analytics project has interpretation risks.

### Risk 1. High coverage may be misleading

If many low-volume products are mapped but a few high-volume products are missing, the percentage can still look excellent.

### Risk 2. Quantity fields may not equal revenue or profit

`qty_requested` and `Req_Qty_Total` represent volume, but not necessarily financial value.

### Risk 3. Fuzzy grouping can over-group or under-group

Two product names may look similar but be different products. The opposite can also happen.

### Risk 4. CSV-based operations can create governance issues

Without database controls, multiple edits may be hard to audit.

### Risk 5. Missing context fields limit analysis

For example, price, margin, customer segment, and date granularity are not visible in the current dashboard.

---

## 22. Key Takeaways

This project is a strong example of a small operational analytics application.

What it does well:

- integrates multiple product datasets
- links external products to internal substitutes
- highlights substitution gaps
- uses business-friendly KPIs
- transforms raw product lists into actionable visual summaries

What you should learn from it:

- how data models support business questions
- how dashboard KPIs are constructed
- why aggregation and normalization matter
- how visualization can prioritize action
- why record counts alone are not enough without impact measures

---

## 23. Short Summary You Can Reuse

The Mediq Substitution Tool is a Streamlit-based analytics dashboard that matches external products to internal MOB portfolio substitutes using CSV datasets. It supports single-product lookup, bulk matching, substitution coverage analysis, portfolio demand analysis, and gap analysis for products without substitutes. From a business analytics perspective, it demonstrates descriptive reporting, data integration, fuzzy product-family grouping, and action-oriented visualization for operational decision support.

---

## 24. How to Run the Project

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 25. Recommended Study Exercises

1. Draw the entity relationship between the four CSV files.
2. Recalculate the coverage KPI manually in Excel or Pandas.
3. Identify one chart and explain why its chart type is appropriate.
4. Compare count-based coverage with quantity-based business impact.
5. Propose one additional KPI for substitution prioritization.
6. Design a mock dashboard improvement for executives versus operational users.

---

## 26. File Reference Map

- Main app: [app.py](../app.py)
- Dataset config: [src/config.py](../src/config.py)
- Data loading: [src/data_loader.py](../src/data_loader.py)
- Matching logic: [src/substitution.py](../src/substitution.py)
- Metrics and charts: [src/visualization.py](../src/visualization.py)
- Text normalization: [src/utils.py](../src/utils.py)
