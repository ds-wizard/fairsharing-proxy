import fastapi

from fairsharing_proxy.consts import BUILD_INFO, NICE_NAME, VERSION
from fairsharing_proxy.core import CORE

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


@app.on_event("startup")
async def app_init():
    await CORE.startup()


@app.on_event("shutdown")
async def shutdown_event():
    await CORE.shutdown()
