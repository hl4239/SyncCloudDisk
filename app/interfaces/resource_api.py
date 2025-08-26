import json

from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse
from sqlmodel import Session, select

from app.domain.dtos.comm import ApiResponse
from app.domain.dtos.resource_dto import resource_to_dto
from app.domain.models.resource import Resource, TvCategory
from app.infrastructure.containers import container

router = APIRouter(prefix="/resources", tags=["资源"])

@router.get("/", response_model=ApiResponse)
def get_resources(tv_cate:TvCategory,count:int=10):
    resources=container.resource_repo().get_by_category(tv_cate,count=count)

    response=ApiResponse(success=True,message='',data=[resource_to_dto(r) for r in resources])
    return response

