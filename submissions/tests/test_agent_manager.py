def test_list_images_imports():
    from submissions.agent_manager import list_agent_images
    assert callable(list_agent_images)