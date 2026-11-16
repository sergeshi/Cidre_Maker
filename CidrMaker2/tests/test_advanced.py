import unittest
from calculations import calculate_petnat, solera_recalculate

class AdvancedCalculationTests(unittest.TestCase):
    def test_petnat_estimates_target_sugar_from_pressure(self):
        result = calculate_petnat({
            "originalBrix": 12,
            "refractometerBrix": 4,
            "hydrometerSG": 0,
            "measurementAlcohol": 0,
            "estimatedResidualSugar": -1,
            "desiredPressure": 4.5,
            "pressureUnit": "bar",
            "maxBottlePressure": 4.5,
            "safetyMargin": 15,
        })
        self.assertAlmostEqual(result["targetSugar"], 18.0)
        self.assertGreaterEqual(result["residualSugar"], 0)
        self.assertTrue(result["warnings"])

    def test_petnat_manual_residual_sugar(self):
        result = calculate_petnat({
            "originalBrix": 12,
            "refractometerBrix": 3,
            "hydrometerSG": 0,
            "measurementAlcohol": 0,
            "estimatedResidualSugar": 20,
            "desiredPressure": 4,
            "pressureUnit": "bar",
            "maxBottlePressure": 4.5,
            "safetyMargin": 15,
        })
        self.assertEqual(result["residualSugar"], 20)
        self.assertAlmostEqual(result["pressureBar"], 5)

    def test_solera_volume_and_age_recalculation(self):
        stage3 = {
            "initialVolume": 100,
            "averageAgeYears": 1.7,
            "initialAverageAgeYears": 2,
            "operations": [
                {"date": "2026-01-01", "removed": 20, "added": 20, "sourceAgeYears": 0.5}
            ],
        }
        volume, age = solera_recalculate(stage3)
        self.assertAlmostEqual(volume, 100)
        self.assertAlmostEqual(age, 1.7)
        self.assertAlmostEqual(stage3["operations"][0]["volumeAfter"], 100)

    def test_solera_prevents_negative_volume(self):
        stage3 = {
            "initialVolume": 10,
            "averageAgeYears": 1,
            "operations": [{"date": "2026-01-01", "removed": 20, "added": 0}],
        }
        volume, _ = solera_recalculate(stage3)
        self.assertEqual(volume, 0)
        self.assertIn("warning", stage3["operations"][0])

if __name__ == "__main__":
    unittest.main()
