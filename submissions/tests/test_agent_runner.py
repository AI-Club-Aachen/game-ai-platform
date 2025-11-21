from submissions.agent_runner import run_agent


def test_run_agent_simple(docker_client, load_zip):
    from submissions.agent_builder import build_from_zip

    data = load_zip("valid_agent.zip")
    result = build_from_zip(data, owner_id="runner-test")

    out = run_agent(result["tag"])

    assert out["exit_code"] == 0
    assert "Agent" in out["logs"]