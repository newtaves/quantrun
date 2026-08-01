import os
import sys
import time
import subprocess
import httpx

def run_tests():
    # Detect the correct python executable
    python_cmd = "python"
    
    print("Starting FastAPI server on port 8001...")
    fastapi_proc = subprocess.Popen(
        ["uv", "run", python_cmd, "-m", "uvicorn", "paper.main:app", "--port", "8001"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    try:
        # Wait for servers to spin up
        print("Waiting 10 seconds for servers to start...")
        time.sleep(10)

        # check if servers started successfully (processes are still alive)
        if fastapi_proc.poll() is not None:
            stdout, stderr = fastapi_proc.communicate()
            print("FastAPI failed to start:")
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            sys.exit(1)

        headers = {"Content-Type": "application/json"}

        # 2. Create a Portfolio via FastAPI
        print("Creating a portfolio...")
        portfolio_payload = {
            "name": "E2E Test Portfolio",
            "description": "Integration testing portfolio",
            "available_cash": 50000.0,
            "invested_cash": 0.0,
            "total_pnl": 0.0
        }
        port_resp = httpx.post(
            "http://127.0.0.1:8001/portfolio",
            json=portfolio_payload,
            headers=headers,
            timeout=10.0
        )
        assert port_resp.status_code == 200, f"Portfolio creation failed: {port_resp.status_code} {port_resp.text}"
        portfolio_data = port_resp.json()
        portfolio_id = portfolio_data["portfolio"]["id"]
        print(f"Created portfolio with ID: {portfolio_id}")

        # 3. Place a market BUY order via FastAPI
        print("Placing market BUY order for SOLUSDT...")
        order_payload = {
            "portfolio_id": portfolio_id,
            "symbol": "SOLUSDT",
            "side": "BUY",
            "quantity": 2.0,
            "limit_price": None,
            "target": None,
            "stoploss": None,
            "status": "PENDING"
        }
        order_resp = httpx.post(
            "http://127.0.0.1:8001/order",
            json=order_payload,
            headers=headers,
            timeout=10.0
        )
        assert order_resp.status_code == 200, f"Order placement failed: {order_resp.status_code} {order_resp.text}"
        print("Order placed successfully.")

        # 4. Wait for execution (which happens on price tick)
        print("Waiting for order execution (approx 5 seconds)...")
        time.sleep(5)

        # 5. Get positions and verify position_id is used instead of id
        pos_resp = httpx.get(
            f"http://127.0.0.1:8001/portfolio/{portfolio_id}/positions",
            headers=headers,
            timeout=10.0
        )
        assert pos_resp.status_code == 200, f"Get positions failed: {pos_resp.status_code} {pos_resp.text}"
        positions = pos_resp.json().get("positions", [])
        
        # If the websocket price feed didn't tick yet, retry for another 5 seconds
        if not positions:
            print("Position not created yet, waiting another 5 seconds...")
            time.sleep(5)
            pos_resp = httpx.get(
                f"http://127.0.0.1:8001/portfolio/{portfolio_id}/positions",
                headers=headers,
                timeout=10.0
            )
            positions = pos_resp.json().get("positions", [])

        assert len(positions) > 0, "No active positions found. (Check internet/Binance websocket connectivity.)"
        
        position = positions[0]
        print(f"Active position found: {position}")
        assert "position_id" in position, f"Expected key 'position_id' in position dict, but found keys: {list(position.keys())}"
        position_id = position["position_id"]
        print(f"Found position_id: {position_id}")

        # 6. Call DELETE on positions/{position_id}
        print(f"Closing position #{position_id}...")
        del_resp = httpx.delete(
            f"http://127.0.0.1:8001/portfolio/{portfolio_id}/positions/{position_id}",
            headers=headers,
            timeout=10.0
        )
        assert del_resp.status_code == 200, f"Close position failed: {del_resp.status_code} {del_resp.text}"
        print("Close position API call succeeded.")

        # 7. Verify positions list is empty
        pos_resp_after = httpx.get(
            f"http://127.0.0.1:8001/portfolio/{portfolio_id}/positions",
            headers=headers,
            timeout=10.0
        )
        positions_after = pos_resp_after.json().get("positions", [])
        assert len(positions_after) == 0, f"Expected 0 positions, but got: {positions_after}"
        print("Position closed successfully. Verified via GET /positions.")
        print("\n=== ALL INTEGRATION TESTS PASSED! ===")

    finally:
        print("Shutting down FastAPI server...")
        fastapi_proc.terminate()
        try:
            fastapi_proc.wait(timeout=3)
        except Exception:
            fastapi_proc.kill()
        print("Servers shut down.")

if __name__ == "__main__":
    run_tests()
