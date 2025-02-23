import fastapi
from http import HTTPStatus
from fastapi.responses import JSONResponse

router = fastapi.APIRouter()


@router.get('/live')
async def liveness():
    return JSONResponse(status_code=HTTPStatus.OK, content={"message": "OK"})
