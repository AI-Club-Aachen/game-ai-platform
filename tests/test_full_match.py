import os
import time
import zipfile

import requests


def upload_agent_and_wait_for_build(api_base_url, headers, zip_path):
    # send as submission to backend API
    with open(zip_path, 'rb') as f:
        files = {'file': ('agent.zip', f, 'application/zip')}
        sub_res = requests.post(f"{api_base_url}/submissions/", headers=headers, files=files, data={"game_type": "tictactoe"})
        
    assert sub_res.status_code == 201, f"Failed to create submission: {sub_res.text}"
    submission = sub_res.json()
    sub_id = submission["id"]
    print(f"Created submission: {sub_id}")

    # check if build job is created
    assert "build_jobs" in submission and len(submission["build_jobs"]) > 0, "No build jobs returned"
    build_job = submission["build_jobs"][0]
    assert build_job["status"] == "queued", f"Expected initially 'queued', got {build_job['status']}"

    # monitor build worker & wait for build to complete
    max_retries = 60
    final_status = None
    for i in range(max_retries):
        poll_res = requests.get(f"{api_base_url}/submissions/{sub_id}", headers=headers)
        assert poll_res.status_code == 200
        poll_sub = poll_res.json()
        assert "build_jobs" in poll_sub and len(poll_sub["build_jobs"]) > 0
        build_job = poll_sub["build_jobs"][0]
        status = build_job["status"]
        print(f"Poll {i+1}: Build status is '{status}'")
        
        if status in ["completed", "failed"]:
            final_status = status
            final_job = build_job
            break
            
        time.sleep(2)

    assert final_status == "completed", f"Build failed or timed out. Final status: {final_status}"
    assert final_job.get("image_id") is not None, "image_id was not set on successful build"
    assert final_job.get("image_tag") is not None, "image_tag was not set on successful build"
    
    agent_res = requests.post(
        f"{api_base_url}/agents",
        headers=headers,
        json={
            "user_id": submission["user_id"],
            "game_type": "tictactoe",
            "active_submission_id": sub_id,
        },
    )
    assert agent_res.status_code == 201, f"Failed to create agent: {agent_res.text}"
    return agent_res.json()["id"]

def test_full_match(auth_headers, api_base_url):
    """
    Test full match workflow.
    Uses auth_headers and api_base_url fixtures from conftest.py.
    """
    headers = auth_headers

    # pack example agent into zip
    current_dir = os.path.dirname(__file__)
    example_agent_path = os.path.normpath(os.path.join(current_dir, "../gamelib/gamelib/tictactoe/examples/simple_agent.py"))
    zip_path = os.path.join(current_dir, "agent.zip")
    
    try:
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.write(example_agent_path, arcname="agent.py")

        print("Building agent 1...")
        agent1_id = upload_agent_and_wait_for_build(api_base_url, headers, zip_path)
        
        print("Building agent 2...")
        agent2_id = upload_agent_and_wait_for_build(api_base_url, headers, zip_path)

        match_payload = {
            "game_type": "tictactoe",
            "agent_ids": [agent1_id, agent2_id],
            "config": {}
        }
        print("Starting match...")
        match_res = requests.post(f"{api_base_url}/matches/", headers=headers, json=match_payload)
        assert match_res.status_code == 201, f"Failed to create match: {match_res.text}"
        match = match_res.json()
        match_id = match["id"]
        print(f"Created match: {match_id}")

        max_retries = 60
        final_status = None
        final_match = None
        for i in range(max_retries):
            poll_res = requests.get(f"{api_base_url}/matches/{match_id}", headers=headers)
            assert poll_res.status_code == 200
            poll_match = poll_res.json()
            status = poll_match["status"]
            print(f"Poll {i+1}: Match status is '{status}'")
            
            if status in ["completed", "failed", "client_error"]:
                final_status = status
                final_match = poll_match
                break
                
            time.sleep(5)

        result = final_match.get("result", {})
        error_msg = f"Match failed or timed out. Final status: {final_status}"
        if final_status == "client_error":
            error_msg = f"Match failed with client error. Reason: {result.get('reason')}"
            
        assert final_status == "completed", error_msg
        assert final_match.get("result") is not None, "Match result was not set"
        
        result = final_match["result"]
        print(f"Match completed successfully with result: {result}")
        assert result.get("winner") is not None
        assert result.get("reason") is not None
        assert result.get("scores") is not None
        assert len(result["scores"]) == 2

        print("Test passed successfully.")
    finally:
        # Cleanup
        if os.path.exists(zip_path):
            os.remove(zip_path)
