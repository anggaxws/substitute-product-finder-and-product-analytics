# Substitution Tool

Streamlit dashboard for searching external products, reviewing MOB substitutes, and exploring substitution coverage and portfolio insights.

## What It Does

- Search external products by ID or name.
- Show one or many matching MOB substitute results.
- Review connected substitutions in a table view.
- Analyze MOB portfolio demand by category, family, and product.
- Analyze products without substitute as a derived gap view.
- Edit the live datasets from the admin panel.

## Storage Model

The app now runs on SQLite, not runtime CSV files.

- Main database: `data/substitution_tool.db`
- Active tables:
  1. `external_products`
  2. `mob_portfolio`
  3. `substitute_database`

`products without substitute` is no longer stored as a separate dataset. It is calculated from external products that do not have a substitute mapping.

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Data Management

- The app reads and writes through SQLite.
- CSV and Excel uploads are still supported in the UI for bulk import.
- The admin panel edits the database-backed datasets directly.
- The repository is expected to include `data/substitution_tool.db` as a seed database for deployment.

## Notes

- The database file must exist in `data/` for the app to show existing data in local runs and deployments.
- If you want to ship updated insights to deployment, commit the latest `data/substitution_tool.db`.
- Category-based gap analytics and coverage metrics are derived from the unified external-products table plus substitute mappings.
