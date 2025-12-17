import fastapi

from typing import Annotated

from .consts import BUILD_INFO, NICE_NAME, VERSION
from .core import CORE
from .model import GraphQLFastSearchQuery

app = fastapi.FastAPI(
    title=NICE_NAME,
    version=VERSION,
)


@app.get(path='/')
async def get_info():
    return fastapi.responses.JSONResponse(
        content=BUILD_INFO,
    )


@app.get(path='/legacy/search/', include_in_schema=False)
@app.get(path='/legacy/search')
async def get_legacy_search(request: fastapi.Request):
    return await CORE.legacy_search(request=request)


@app.get(path='/search')
async def get_search(request: fastapi.Request):
    return await CORE.search(request=request, is_get=True)


@app.post(path='/search')
async def post_search(request: fastapi.Request):
    return await CORE.search(request=request, is_get=False)


@app.get(path='/v2/search')
async def get_v2_search(
        q: Annotated[str | None, fastapi.Query()] = None,
        registry: Annotated[str | None, fastapi.Query()] = None,
        record_type: Annotated[str | None, fastapi.Query()] = None,
        status: Annotated[str | None, fastapi.Query()] = None,
        min_q: Annotated[int, fastapi.Query()] = 1,
):
    if q is None or len(q) < min_q:
        return []
    query = GraphQLFastSearchQuery(
        q=q,
        registry=_process_query_param_list(registry),
        record_type=_process_query_param_list(record_type),
        status=_process_query_param_list(status),
    )
    return await CORE.v2_search(query)


@app.on_event("startup")
async def app_init():
    await CORE.startup()


@app.on_event("shutdown")
async def shutdown_event():
    await CORE.shutdown()


def _process_query_param_list(param: str | None) -> list[str] | None:
    if param is None:
        return None
    result = list(filter(lambda x: len(x) > 0, map(str.strip, param.split(','))))
    return result if len(result) > 0 else None
