import fastapi
from http import HTTPStatus
from fastapi.responses import JSONResponse
from fastapi import Request
from pydantic import BaseModel
from typing import Any

router = fastapi.APIRouter()


class ModelInput(BaseModel):
    features: dict[str, Any]


class ModelOutput(BaseModel):
    predictions: Any


@router.post('/preprocess')
async def preprocess(request: Request, model_input: ModelInput):
    return JSONResponse(
        status_code=HTTPStatus.OK,
        content=request.state.model.preprocess(model_input.features)
    )


@router.post('/predict')
async def predict(request: Request, model_input: ModelInput):
    return JSONResponse(
        status_code=HTTPStatus.OK,
        content=request.state.model.predict(model_input.features)
    )


@router.post('/postprocess')
async def postprocess(request: Request, model_output: ModelOutput):
    return JSONResponse(
        status_code=HTTPStatus.OK,
        content=request.state.model.postprocess(model_output.predictions)
    )
