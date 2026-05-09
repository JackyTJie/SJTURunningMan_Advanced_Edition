import unittest

from src.route_preview import (
    UPLOAD_LATITUDE_OFFSET,
    UPLOAD_LONGITUDE_OFFSET,
    build_route_preview,
    extract_payload_points,
    generate_route_preview_html,
    update_preview_status,
)


def make_payload(tracks):
    return [
        {
            "tracks": [
                {
                    "status": "normal",
                    "points": [
                        {
                            "latLng": {"latitude": lat, "longitude": lng},
                            "location": f"{lng:.7f},{lat:.7f}",
                            "locatetime": timestamp,
                            "step": 0,
                        }
                        for lat, lng, timestamp in track_points
                    ],
                }
                for track_points in tracks
            ]
        }
    ]


class RoutePreviewTests(unittest.TestCase):
    def test_extracts_points_from_multiple_tracks(self):
        payload = make_payload([
            [
                (31.0, 121.0, 1_700_000_000_000),
                (31.0, 121.0001, 1_700_000_003_000),
            ],
            [
                (31.0001, 121.0002, 1_700_000_006_000),
            ],
        ])

        points = extract_payload_points(payload)

        self.assertEqual(len(points), 3)
        self.assertEqual(points[0]["track_index"], 0)
        self.assertEqual(points[2]["track_index"], 1)

    def test_extracts_baidu_display_coordinates_for_map_rendering(self):
        payload = make_payload([
            [
                (31.0, 121.0, 1_700_000_000_000),
                (31.0, 121.0001, 1_700_000_003_000),
            ]
        ])

        points = extract_payload_points(payload)

        self.assertAlmostEqual(points[0]["display_lng"], 121.0 - UPLOAD_LONGITUDE_OFFSET)
        self.assertAlmostEqual(points[0]["display_lat"], 31.0 - UPLOAD_LATITUDE_OFFSET)

    def test_build_preview_computes_stats_and_jump_segments(self):
        payload = make_payload([
            [
                (31.0, 121.0, 1_700_000_000_000),
                (31.0, 121.0001, 1_700_000_003_000),
                (31.0, 121.0040, 1_700_000_006_000),
            ]
        ])

        preview = build_route_preview(
            payload,
            run_index=1,
            total_runs=2,
            risk_analysis={"score": 76, "level": "high", "level_label": "高风险"},
        )

        self.assertTrue(preview["available"])
        self.assertEqual(preview["stats"]["point_count"], 3)
        self.assertEqual(preview["stats"]["jump_count"], 1)
        self.assertGreater(preview["stats"]["max_segment_m"], 150)
        self.assertIn("第1/2条", preview["summary"])
        self.assertIn("高风险 76", preview["summary"])

    def test_empty_payload_is_not_available(self):
        preview = build_route_preview([{"tracks": []}])

        self.assertFalse(preview["available"])
        self.assertEqual(preview["summary"], "暂无可预览路线")

    def test_update_preview_status_refreshes_summary(self):
        preview = build_route_preview(make_payload([
            [
                (31.0, 121.0, 1_700_000_000_000),
                (31.0, 121.0001, 1_700_000_003_000),
            ]
        ]), run_index=1, total_runs=1)

        updated = update_preview_status(preview, "上传成功")

        self.assertEqual(updated["status"], "上传成功")
        self.assertIn("上传成功", updated["summary"])

    def test_preview_html_contains_baidu_map_and_route_data(self):
        preview = build_route_preview(make_payload([
            [
                (31.0, 121.0, 1_700_000_000_000),
                (31.0, 121.0001, 1_700_000_003_000),
                (31.0, 121.0040, 1_700_000_006_000),
            ]
        ]))

        html = generate_route_preview_html(preview)

        self.assertIn("api.map.baidu.com", html)
        self.assertIn("routePoints", html)
        self.assertIn("jumpSegments", html)
        self.assertIn("display_lng", html)
        self.assertIn("反向应用 GPS 校正", html)
        self.assertIn("实际上传路线", html)


if __name__ == "__main__":
    unittest.main()
