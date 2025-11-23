"""
Main entry point for the backend application.
Sets up and runs the FastAPI server.
"""

from fastapi import FastAPI


app = FastAPI()


@app.get("/")
async def hello_world() -> dict[str, str]:
    return {"Hello": "World"}
