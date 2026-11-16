import json
import tempfile
import unittest
from pathlib import Path
from model import load_data, save_data, new_batch, predicted_abv, classic_tirage, batch_search_text

class ModelTests(unittest.TestCase):
    def test_round_trip_preserves_unknown_fields(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"cider_data.json"
            original={"appVersion":"2.3.0","dataSchemaVersion":"2.3","custom":"keep me","batches":[new_batch()]}
            original["batches"][0]["stage3"]["customNested"]={"x":1}
            save_data(p,original); restored=load_data(p)
            self.assertEqual(restored["custom"],"keep me")
            self.assertEqual(restored["batches"][0]["stage3"]["customNested"],{"x":1})

    def test_predicted_abv(self):
        self.assertAlmostEqual(predicted_abv(10),5.5)
        self.assertAlmostEqual(predicted_abv(13,3),5.5)
        self.assertEqual(predicted_abv("bad"),0)

    def test_classic_tirage(self):
        result=classic_tirage(20,4,0.75,600)
        self.assertEqual(result["sugar_g"],320)
        self.assertAlmostEqual(result["bottles"],20/0.75)
        self.assertGreater(result["required_liqueur_ml_per_bottle"],0)

    def test_search(self):
        b=new_batch(); b["name"]="Антоновка"; b["stage1"]["varieties"]="Antonovka"
        self.assertIn("антоновка",batch_search_text(b))
        self.assertIn("antonovka",batch_search_text(b))

if __name__ == "__main__": unittest.main()
