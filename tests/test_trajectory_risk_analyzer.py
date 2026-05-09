import math
import unittest

from src.trajectory_risk_analyzer import analyze_running_payload


def make_payload(points, status="normal"):
    return [
        {
            "tracks": [
                {
                    "status": status,
                    "tstate": "0",
                    "points": [
                        {
                            "latLng": {"latitude": lat, "longitude": lon},
                            "location": f"{lon:.7f},{lat:.7f}",
                            "step": 0,
                            "locatetime": timestamp,
                        }
                        for lat, lon, timestamp in points
                    ],
                }
            ]
        }
    ]


class TrajectoryRiskAnalyzerTests(unittest.TestCase):
    def test_flags_mechanical_constant_speed_payload_as_high_risk(self):
        base_time = 1_700_000_000_000
        points = [
            (31.0, 121.0 + index * 0.00004, base_time + index * 3000)
            for index in range(90)
        ]

        result = analyze_running_payload(make_payload(points))

        self.assertEqual(result["level"], "high")
        self.assertGreaterEqual(result["score"], 70)
        finding_names = {finding["name"] for finding in result["findings"]}
        self.assertIn("时间采样规律性", finding_names)
        self.assertIn("速度过度稳定", finding_names)
        self.assertIn("线性插值痕迹", finding_names)

    def test_marks_non_increasing_timestamps_as_high_risk(self):
        points = [
            (31.0, 121.0, 1_700_000_000_000),
            (31.00001, 121.00001, 1_699_999_999_000),
            (31.00002, 121.00002, 1_700_000_003_000),
        ]

        result = analyze_running_payload(make_payload(points))

        self.assertEqual(result["level"], "high")
        self.assertGreater(result["stats"]["non_increasing_timestamps"], 0)

    def test_marks_empty_payload_as_high_risk(self):
        result = analyze_running_payload([{"tracks": []}])

        self.assertEqual(result["level"], "high")
        self.assertEqual(result["stats"]["point_count"], 0)

    def test_curved_variable_sample_stays_below_high_risk(self):
        base_time = 1_700_000_000_000
        lat = 31.0
        lon = 121.0
        timestamp = base_time
        points = []

        for index in range(80):
            if index > 0:
                angle = index * 0.19 + math.sin(index / 5.0) * 0.7
                step_scale = 0.8 + 0.35 * math.sin(index / 4.0) + 0.12 * (index % 3)
                lat += math.sin(angle) * 0.000025 * step_scale
                lon += math.cos(angle) * 0.000035 * step_scale
                timestamp += int((2.1 + (index % 7) * 0.31 + 0.2 * math.sin(index)) * 1000)
            points.append((lat, lon, timestamp))

        result = analyze_running_payload(make_payload(points))

        self.assertNotEqual(result["level"], "high")
        self.assertLess(result["score"], 70)


if __name__ == "__main__":
    unittest.main()
