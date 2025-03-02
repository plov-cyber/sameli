from http import HTTPStatus
from typing import Any

import fastapi
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

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


@router.post('/predict_only')
async def predict_only(request: Request, model_input: ModelInput):
    return JSONResponse(
        status_code=HTTPStatus.OK,
        content=request.state.model.predict(model_input.features)
    )


@router.post('/predict')
async def predict(request: Request, model_input: ModelInput):
    try:
        preprocessed_input = request.state.model.preprocess(model_input.features)
        predictions = request.state.model.predict(preprocessed_input)
        output = request.state.model.postprocess(predictions)

        return JSONResponse(status_code=HTTPStatus.OK, content=output)

    except Exception as e:
        return JSONResponse(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            content=str(e)
        )


@router.post('/postprocess')
async def postprocess(request: Request, model_output: ModelOutput):
    return JSONResponse(
        status_code=HTTPStatus.OK,
        content=request.state.model.postprocess(model_output.predictions)
    )
