from http import HTTPStatus
from typing import Any

import fastapi
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from sameli.utils import make_serializable

router = fastapi.APIRouter()


class PredictInput(BaseModel):
    task_id: str
    features: dict[str, Any]


class PreprocessInput(BaseModel):
    task_id: str
    raw_features: dict[str, Any]


class PostprocessInput(BaseModel):
    task_id: str
    predictions: Any


@router.post('/preprocess')
async def preprocess(request: Request, data: PreprocessInput):
    result = request.state.model.preprocess(data.raw_features)
    result = make_serializable(result)

    await request.state.redis.store_result(task_id=data.task_id, result=result)

    return JSONResponse(
        status_code=HTTPStatus.OK,
        content=result
    )


@router.post('/predict')
async def predict(request: Request, data: PredictInput):
    result = request.state.model.predict(data.features)
    result = make_serializable(result)

    await request.state.redis.store_result(task_id=data.task_id, result=result)

    return JSONResponse(
        status_code=HTTPStatus.OK,
        content=result
    )


@router.post('/pipeline')
async def pipeline(request: Request, data: PreprocessInput):
    result = request.state.model.pipeline(data.raw_features)
    result = make_serializable(result)

    await request.state.redis.store_result(task_id=data.task_id, result=result)

    return JSONResponse(
        status_code=HTTPStatus.OK,
        content=result
    )


@router.post('/postprocess')
async def postprocess(request: Request, data: PostprocessInput):
    result = request.state.model.postprocess(data.predictions)
    result = make_serializable(result)

    await request.state.redis.store_result(task_id=data.task_id, result=result)

    return JSONResponse(
        status_code=HTTPStatus.OK,
        content=result
    )
