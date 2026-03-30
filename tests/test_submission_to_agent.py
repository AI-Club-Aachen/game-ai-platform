import os
import time
import zipfile

import requests


def test_submission_to_agent(auth_headers, api_base_url):
    """
    Test submission to agent workflow.
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

        # send as submission to backend API
        with open(zip_path, 'rb') as f:
            files = {'file': ('agent.zip', f, 'application/zip')}
            sub_res = requests.post(f"{api_base_url}/submissions", headers=headers, files=files)
            
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
                submission = poll_sub
                final_job = build_job
                break
                
            time.sleep(2)

        assert final_status == "completed", f"Build failed or timed out. Final status: {final_status}"

        # check if image was created correctly
        assert final_job.get("image_id") is not None, "image_id was not set on successful build"
        assert final_job.get("image_tag") is not None, "image_tag was not set on successful build"
        print(f"Image created successfully with tag: {final_job['image_tag']}")

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
        agent = agent_res.json()
        assert agent["active_submission_id"] == sub_id
        assert agent["game_type"] == "tictactoe"

        print("Test passed successfully.")
    finally:
        # Cleanup
        if os.path.exists(zip_path):
            os.remove(zip_path)
