from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src import config, database
from src.data_loader import save_dataset
from src.database import fetch_audit_log, increment_requested_amounts
from src.substitution import connected_substitutions_view
from src.visualization import gap_metrics, substitution_metrics


class CoreFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        config.DATA_DIR = temp_path
        config.DB_PATH = temp_path / "test_substitution_tool.db"
        database.DATA_DIR = config.DATA_DIR
        database.DB_PATH = config.DB_PATH
        database.ensure_database()

        save_dataset(
            "raw_external_products",
            pd.DataFrame(
                [
                    {
                        "external_id": "E1",
                        "duplicate_detection": "? Unique",
                        "external_name": "External One",
                        "manufacturer": "",
                        "category": "Cat A",
                        "last_update": "",
                        "qty_requested": "10",
                        "created_date": "",
                        "source_file": "",
                        "import_date": "",
                    },
                    {
                        "external_id": "E2",
                        "duplicate_detection": "? Unique",
                        "external_name": "External Two",
                        "manufacturer": "",
                        "category": "Cat B",
                        "last_update": "",
                        "qty_requested": "5",
                        "created_date": "",
                        "source_file": "",
                        "import_date": "",
                    },
                ]
            ),
        )
        save_dataset(
            "mob_portfolio",
            pd.DataFrame(
                [
                    {
                        "MOB_ID": "M1",
                        "MOB_Name": "Mob One",
                        "Kategorie": "Cat A",
                        "GrÃ¶ÃŸe/Variante": "",
                        "Aktiv (Y/N)": "Y",
                        "Last_Updated": "",
                        "Req_Qty_Total": "100",
                    },
                    {
                        "MOB_ID": "M2",
                        "MOB_Name": "Mob Two",
                        "Kategorie": "Cat B",
                        "GrÃ¶ÃŸe/Variante": "",
                        "Aktiv (Y/N)": "Y",
                        "Last_Updated": "",
                        "Req_Qty_Total": "50",
                    },
                ]
            ),
        )
        save_dataset(
            "substitute_database",
            pd.DataFrame(
                [
                    {"external_id": "E1", "mob_id": "M1", "source_file": "", "import_date": ""},
                ]
            ),
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_requested_amount_update_updates_external_and_mob_and_audit_log(self) -> None:
        result = increment_requested_amounts([{"external_id": "E1", "amount": 7}])

        self.assertEqual(result["missing_external_ids"], [])
        self.assertEqual(result["applied_updates"][0]["new_external_qty"], "17")
        self.assertEqual(result["applied_updates"][0]["linked_mob_ids"], ["M1"])

        external_df = database.load_dataset_from_db("raw_external_products")
        mob_df = database.load_dataset_from_db("mob_portfolio")
        audit_df = fetch_audit_log(limit=5)

        self.assertEqual(external_df.loc[external_df["external_id"] == "E1", "qty_requested"].iloc[0], "17")
        self.assertEqual(mob_df.loc[mob_df["MOB_ID"] == "M1", "Req_Qty_Total"].iloc[0], "107")
        self.assertIn("requested_amount_update", audit_df["action"].tolist())

    def test_substitution_and_gap_metrics_use_live_database(self) -> None:
        sub_metrics = substitution_metrics()
        gap_summary = gap_metrics()

        self.assertEqual(sub_metrics["External products"], 2.0)
        self.assertEqual(sub_metrics["Linked substitutes"], 1.0)
        self.assertEqual(sub_metrics["Coverage rate %"], 50.0)
        self.assertEqual(gap_summary["Products without substitute"], 1.0)

    def test_connected_substitutions_reflect_saved_mapping(self) -> None:
        connected_df = connected_substitutions_view()

        self.assertEqual(len(connected_df), 1)
        self.assertEqual(connected_df.iloc[0]["external_id"], "E1")
        self.assertEqual(connected_df.iloc[0]["mob_id"], "M1")


if __name__ == "__main__":
    unittest.main()
