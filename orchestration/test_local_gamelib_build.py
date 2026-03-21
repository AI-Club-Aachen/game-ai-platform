import io
import os
import sys
import zipfile

import docker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.agent_builder import build_from_zip

# Create a minimal valid agent zip
bio = io.BytesIO()
with zipfile.ZipFile(bio, 'w') as zf:
    zf.writestr('agent.py', "import gamelib; print('Success! Gamelib imported from', gamelib.__file__)")
zip_bytes = bio.getvalue()

os.environ["BUILD_LOCAL_BASE_IMAGE"] = "1"
# Ensure the fake test owner id is easily cleanable
print("Starting build...")
try:
    result = build_from_zip(zip_bytes, owner_id="test_local_gamelib")
    print("Build successful:", result)

    # Run a container from the image to see if it imports gamelib
    client = docker.from_env()
    container = client.containers.run(
        result["image_id"],
        command=["python", "agent.py"],
        remove=True
    )
    print("Container output:", container.decode('utf-8'))
except Exception as e:
    print("Build failed:", e)
    sys.exit(1)
