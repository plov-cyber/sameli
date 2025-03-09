from http import HTTPStatus
from typing import Any

import fastapi
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = fastapi.APIRouter()


class PredictInput(BaseModel):
    features: dict[str, Any]


class PreprocessInput(BaseModel):
    raw_features: dict[str, Any]


class PostprocessInput(BaseModel):
    predictions: Any


@router.post('/preprocess')
async def preprocess(request: Request, data: PreprocessInput):
    return JSONResponse(
        status_code=HTTPStatus.OK,
        content=request.state.model.preprocess(data.raw_features)
    )


@router.post('/predict')
async def predict(request: Request, data: PredictInput):
    return JSONResponse(
        status_code=HTTPStatus.OK,
        content=request.state.model.predict(data.features)
    )


@router.post('/pipeline')
async def pipeline(request: Request, data: PreprocessInput):
    return JSONResponse(
        status_code=HTTPStatus.OK,
        content=request.state.model.pipeline(data.raw_features)
    )


@router.post('/postprocess')
async def postprocess(request: Request, data: PostprocessInput):
    return JSONResponse(
        status_code=HTTPStatus.OK,
        content=request.state.model.postprocess(data.predictions)
    )
