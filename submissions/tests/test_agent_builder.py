from submissions.agent_builder import build_from_zip

def test_builder_creates_image(docker_client, load_zip):
    zip_bytes = load_zip("valid_agent.zip")
    result = build_from_zip(zip_bytes, owner_id="test")

    tag = result["tag"]
    image = docker_client.images.get(tag)

    assert image is not None
    assert tag in image.tags

def test_builder_with_generated_zip(docker_client, generated_simple_zip):
    from submissions.agent_builder import build_from_zip
    result = build_from_zip(generated_simple_zip, owner_id="x")