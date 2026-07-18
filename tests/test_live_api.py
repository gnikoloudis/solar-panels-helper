"""End-to-end test: start uvicorn, make a real estimate request."""

import multiprocessing
import time
import uvicorn
import httpx
from solarpanels.main import app


def _run_server():
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="error")


class TestLiveApi:
    def test_real_estimate_paris_july(self):
        proc = multiprocessing.Process(target=_run_server, daemon=True)
        proc.start()
        time.sleep(2)

        try:
            r = httpx.post(
                "http://127.0.0.1:8765/api/estimate",
                json={
                    "latitude": 48.85,
                    "longitude": 2.35,
                    "start_date": "2026-07-10",
                    "end_date": "2026-07-16",
                    "panel_area_m2": 1.6,
                    "efficiency": 0.20,
                    "system_losses": 0.14,
                    "tracking": "fixed",
                    "tilt": 35,
                    "azimuth": 180,
                },
                timeout=30,
            )
            assert r.status_code == 200, f"Status {r.status_code}: {r.text}"
            data = r.json()

            assert "total_energy_kwh" in data
            assert data["total_energy_kwh"] > 0
            assert len(data["daily_estimates"]) == 7

            for d in data["daily_estimates"]:
                assert d["energy_kwh"] >= 0
                assert d["radiation_mj_m2"] >= 0

            assert data["panel_parameters"]["tracking"] == "fixed"
            assert data["location"]["latitude"] == 48.85
        finally:
            proc.kill()
