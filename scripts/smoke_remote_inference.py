#!/usr/bin/env python3
"""Paid, opt-in smoke test for the configured Hugging Face model family."""
import asyncio, os, sys
from pathlib import Path
from pydantic import BaseModel
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"backend")); os.environ.setdefault("DATABASE_URL","sqlite://")
from app.providers.llm import HuggingFaceProvider, ModelRole
class Answer(BaseModel): answer: str
async def main():
    provider=HuggingFaceProvider()
    for role,prompt in ((ModelRole.FAST,"Pose une question courte aidant à résoudre 3x-7=11."),(ModelRole.DEEP,"Donne la valeur de x pour 3x-7=11.")):
        result=await provider.structured_response(instructions="Réponds en JSON.",input_text=prompt,response_model=Answer,role=role)
        assert result.answer and provider.last_request
        print(role.value, result.answer, provider.last_request)
if __name__=="__main__": asyncio.run(main())
