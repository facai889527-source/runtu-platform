import json

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from backend.auth.routes import require_permission
from backend.user_management import CreateUser, UpdateUser, UserPublic, UserPage, UserManagementService, UserDenied, UserConflict, UserMissing


def install_user_management(app, database):
    service = UserManagementService(database)
    app.state.user_management = service
    router = APIRouter(prefix='/api/admin/users', tags=['user management'])

    for error, status, detail in [(UserDenied,403,'User operation not permitted'),
        (UserConflict,409,'User already exists or changed; reload'),(UserMissing,404,'User not found')]:
        async def handler(_request, _error, status=status, detail=detail):
            return JSONResponse({'detail':detail},status_code=status,headers={'Cache-Control':'no-store'})
        app.add_exception_handler(error,handler)

    async def bounded_body(request, model):
        if request.headers.get('content-type','').split(';')[0].strip() != 'application/json':
            raise HTTPException(415,'JSON required',headers={'Cache-Control':'no-store'})
        raw = bytearray()
        async for chunk in request.stream():
            if len(raw)+len(chunk)>4096:
                raise HTTPException(413,'Request too large',headers={'Cache-Control':'no-store'})
            raw.extend(chunk)
        try:
            return model.model_validate(json.loads(raw))
        except (ValueError, TypeError, UnicodeError, RecursionError, ValidationError):
            # Never serialize validation errors or input: they may contain a password.
            raise HTTPException(422,'Invalid user request',headers={'Cache-Control':'no-store'}) from None
        finally:
            raw.clear()

    @router.get('',response_model=UserPage)
    def list_users(response: Response, limit:int=Query(20,ge=1,le=50),
                   after_username:str|None=Query(None,min_length=3,max_length=64,pattern=r'^[a-z0-9_.-]{3,64}$'),
                   identity=Depends(require_permission('users.manage'))):
        response.headers['Cache-Control']='no-store'
        return service.page(identity.id,limit,after_username)

    @router.post('',response_model=UserPublic,status_code=201)
    async def create_user(request: Request,identity=Depends(require_permission('users.manage'))):
        value=await bounded_body(request,CreateUser)
        result=await run_in_threadpool(service.create,identity.id,value)
        return JSONResponse(result.model_dump(mode='json'),status_code=201,headers={'Cache-Control':'no-store'})

    @router.patch('/{user_id}',response_model=UserPublic)
    async def update_user(request:Request,user_id:str=Path(min_length=1,max_length=36),identity=Depends(require_permission('users.manage'))):
        value=await bounded_body(request,UpdateUser)
        result=await run_in_threadpool(service.update,identity.id,user_id,value)
        return JSONResponse(result.model_dump(mode='json'),headers={'Cache-Control':'no-store'})

    app.include_router(router)
