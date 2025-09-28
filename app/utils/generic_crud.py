# file: generic_crud_with_filters.py
from typing import Optional, List, Any, Type, Dict, get_type_hints
from typing_extensions import Annotated, get_origin, get_args
from dataclasses import dataclass

from fastapi import APIRouter, FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel, create_model
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import Document, init_beanie, PydanticObjectId

import asyncio

# -------------------------
# Filter 注解定义（用于 Annotated）
# -------------------------
@dataclass
class Filter:
    """
    指定某字段允许的查询操作。
    usage:
      from typing_extensions import Annotated
      name: Annotated[str, Filter(ops=["eq","contains"])]
    可选操作（实现的）: eq, lt, lte, gt, gte, in, contains
    """
    ops: List[str] = None

    def __post_init__(self):
        if self.ops is None:
            self.ops = ["eq", "lt", "lte", "gt", "gte", "in", "contains"]


# -------------------------
# Helper: 根据 Document 构造 Filter Pydantic Model（用于依赖注入、从 query params 创建实例）
# -------------------------
def build_filter_model(doc_model: Type[Document]) -> Type[BaseModel]:
    """
    Inspect doc_model's type hints (include Annotated extras),
    create a dynamic Pydantic model with optional fields like:
      {field}__eq, {field}__lt, {field}__in, ...
    Return a BaseModel subclass suitable for Depends() in FastAPI endpoint.
    """
    hints = get_type_hints(doc_model, include_extras=True)
    model_fields: Dict[str, tuple] = {}

    for field_name, hint in hints.items():
        # detect Annotated[<type>, Filter(...)]
        origin = get_origin(hint)
        base_type = None
        filter_spec = None

        if origin is Annotated:
            args = get_args(hint)
            base_type = args[0]
            # search extras for Filter instance
            for extra in args[1:]:
                if isinstance(extra, Filter):
                    filter_spec = extra
                    break

        # 若未用 Annotated 指定 Filter，则跳过（默认不作为 filter）
        if filter_spec is None:
            continue

        # 为每个 op 创建一个可选的字段
        for op in filter_spec.ops:
            field_key = f"{field_name}__{op}"
            # 默认把 'in' 类型设为 List[base_type]
            if op == "in":
                # pydantic 需要 typing.List[...]（这里简单使用 List[base_type]）
                field_type = Optional[List[base_type]]  # e.g. Optional[List[int]]
                default = None
            else:
                field_type = Optional[base_type]
                default = None

            # create_model expects tuple (type, default)
            model_fields[field_key] = (field_type, default)

    # always add pagination/sort fields
    model_fields.setdefault("limit", (Optional[int], 50))
    model_fields.setdefault("skip", (Optional[int], 0))
    model_fields.setdefault("sort_by", (Optional[str], None))  # e.g. "age" or "-created_at"

    FilterModel = create_model(f"{doc_model.__name__}FilterModel", **model_fields)  # type: ignore
    return FilterModel


# -------------------------
# Helper: 将 FilterModel 实例转换为 Mongo filter dict
# -------------------------
def convert_value_to_bson(field_type: Any, value: Any):
    """如果需要把字符串 id 转为 ObjectId 等，做轻量转换。"""
    # 当 field_type 指向 PydanticObjectId / ObjectId 时，把字符串转为 ObjectId
    if field_type in (PydanticObjectId, ObjectId):
        if isinstance(value, list):
            return [ObjectId(v) if not isinstance(v, ObjectId) else v for v in value]
        return ObjectId(value) if not isinstance(value, ObjectId) else value
    # otherwise return as-is (could add more conversions)
    return value


def build_mongo_filter_from_model(doc_model: Type[Document], filter_model: BaseModel) -> Dict:
    """
    规则：
      - 对于 field__eq -> {field: value}
      - field__lt -> {field: {"$lt": value}}, etc.
      - field__in -> {field: {"$in": value_list}}
      - field__contains -> {field: {"$regex": value, "$options": "i"}}
    """
    mongo_filter: Dict[str, Any] = {}
    hints = get_type_hints(doc_model, include_extras=True)

    # map operator to mongo op
    op_map = {
        "lt": "$lt",
        "lte": "$lte",
        "gt": "$gt",
        "gte": "$gte",
        "in": "$in",
    }

    for key, value in filter_model.__dict__.items():
        if value is None:
            continue
        if key in ("limit", "skip", "sort_by"):
            continue
        if "__" not in key:
            continue
        field, op = key.split("__", 1)
        # get field's base type for conversions if available
        hint = hints.get(field, None)
        base_type = None
        if hint is not None:
            origin = get_origin(hint)
            if origin is Annotated:
                base_type = get_args(hint)[0]
            else:
                base_type = hint

        converted = convert_value_to_bson(base_type, value)

        if op == "eq":
            # if there is already an operator dict for this field, merge carefully
            if isinstance(mongo_filter.get(field), dict):
                # set equality - override any previous eq
                mongo_filter[field]["$eq"] = converted
            else:
                mongo_filter[field] = converted
        elif op == "contains":
            # use case-insensitive regex
            mongo_filter.setdefault(field, {})
            # if user passed list (unlikely), join with '|'
            pattern = converted if not isinstance(converted, list) else "|".join(map(str, converted))
            mongo_filter[field].update({"$regex": pattern, "$options": "i"})
        elif op in op_map:
            mongo_filter.setdefault(field, {})
            mongo_filter[field].update({op_map[op]: converted})
        else:
            # unknown op -> ignore or raise
            raise ValueError(f"unknown filter op: {op}")

    return mongo_filter


# -------------------------
# Generic CRUD Router Factory
# -------------------------
class GenericCRUDRouter:
    def __init__(self, model: Type[Document], prefix: Optional[str] = None, tags: Optional[List[str]] = None):
        self.model = model
        self.router = APIRouter(prefix=prefix or f"/{model.__name__.lower()}s", tags=tags or [model.__name__])
        self.FilterModel = build_filter_model(model)

        # mount routes (create, get, update, delete)
        self.router.post("/", response_model=model)(self.create_one)
        self.router.get("/{item_id}", response_model=model)(self.get_one)
        self.router.patch("/{item_id}", response_model=model)(self.update_one)
        self.router.delete("/{item_id}")(self.delete_one)

        # register list route properly with concrete FilterModel via Depends()
        filter_cls = self.FilterModel

        def make_list_endpoint():
            async def list_endpoint(
                filters: filter_cls = Depends(),
                limit: int = Query(50, ge=1, le=1000),
                skip: int = Query(0, ge=0),
                sort_by: Optional[str] = Query(None)
            ):
                # call the instance method (use bound self)
                return await self.list_many(filters=filters, limit=limit, skip=skip, sort_by=sort_by)
            return list_endpoint

        self.router.get("/", response_model=List[model])(make_list_endpoint())


    # --- route handlers ---
    async def create_one(self, payload: dict):
        """
        payload 会由 FastAPI 自动校验为 dict（如果你想更严格可以使用 model as request body）
        这里采用底层 collection 来插入，然后返回 model.parse_obj(result)
        """
        print('cenima')
        coll = self.model.get_pymongo_collection()
        # convert PydanticObjectId / nested changes if needed
        res = await coll.insert_one(payload)
        doc = await coll.find_one({"_id": res.inserted_id})
        return self.model.parse_obj(doc)

    async def get_one(self, item_id: str):
        coll = self.model.get_pymongo_collection()
        try:
            _id = ObjectId(item_id)
        except Exception:
            raise HTTPException(status_code=400, detail="invalid id")
        doc = await coll.find_one({"_id": _id})
        if not doc:
            raise HTTPException(status_code=404, detail="not found")
        return self.model.parse_obj(doc)

    async def list_many(self, filters: BaseModel = Depends(), limit: int = Query(50, ge=1, le=1000), skip: int = Query(0, ge=0), sort_by: Optional[str] = Query(None)):
        # NOTE: FastAPI 依赖注入会把我们的 FilterModel 放到 `filters`（需要在路由定义里明确）
        # but due to how we register route above we must adapt signature in registration (see __init__).
        # For clarity, we will rebind proper signature later. For now assume filters is FilterModel instance.
        # Convert:
        if isinstance(filters, BaseModel):
            filter_model = filters
        else:
            # fallback
            filter_model = self.FilterModel()

        mongo_filter = build_mongo_filter_from_model(self.model, filter_model)
        coll = self.model.get_pymongo_collection()
        cursor = coll.find(mongo_filter).skip(skip).limit(limit)

        if sort_by:
            # simple support "-field" for desc
            if sort_by.startswith("-"):
                cursor = cursor.sort(sort_by[1:], -1)
            else:
                cursor = cursor.sort(sort_by, 1)

        docs = await cursor.to_list(length=limit)
        # parse to model instances
        return [self.model.parse_obj(d) for d in docs]

    async def update_one(self, item_id: str, payload: dict):
        coll = self.model.get_pymongo_collection()
        try:
            _id = ObjectId(item_id)
        except Exception:
            raise HTTPException(status_code=400, detail="invalid id")
        res = await coll.update_one({"_id": _id}, {"$set": payload})
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="not found")
        doc = await coll.find_one({"_id": _id})
        return self.model.parse_obj(doc)

    async def delete_one(self, item_id: str):
        coll = self.model.get_pymongo_collection()
        try:
            _id = ObjectId(item_id)
        except Exception:
            raise HTTPException(status_code=400, detail="invalid id")
        res = await coll.delete_one({"_id": _id})
        if res.deleted_count == 0:
            raise HTTPException(status_code=404, detail="not found")
        return {"deleted": True, "id": item_id}


# -------------------------
# Usage Example
# -------------------------
# Example Beanie Document model that uses Annotated + Filter
from typing import List
class User(Document):
    # name 支持 eq 和 contains
    name: Annotated[str, Filter(ops=["eq", "contains"])]
    # age 支持 eq, gt, lt
    age: Annotated[Optional[int], Filter(ops=["eq", "gt", "lt"])]
    tags: Annotated[Optional[List[str]], Filter(ops=["in"])]

    class Settings:
        name = "users"  # mongo collection name

# Build FastAPI app and include router
def create_app(mongo_uri: str = "mongodb://localhost:27017", db_name: str = "testdb"):
    app = FastAPI(title="Generic CRUD with Filter Annotations")

    @app.on_event("startup")
    async def startup():
        client = AsyncIOMotorClient(mongo_uri)
        # init_beanie requires a motor client or database
        await init_beanie(database=client[db_name], document_models=[User])

    # build router
    router = GenericCRUDRouter(User, prefix="/users").router

    # IMPORTANT: rebind list_many route signature so that FastAPI injects FilterModel via Depends()
    # Because we created the route earlier in __init__, we need to override the path operation
    # with a new function that has the right signature (filters: FilterModel = Depends()).
    filter_model = build_filter_model(User)

    async def user_list_endpoint(filters: filter_model = Depends(), limit: int = Query(50, ge=1, le=1000), skip: int = Query(0, ge=0), sort_by: Optional[str] = Query(None)):
        return await GenericCRUDRouter(User).list_many(filters=filters, limit=limit, skip=skip, sort_by=sort_by)

    # override GET /
    router.routes = [r for r in router.routes if not (r.path == "/users" and "get" in r.methods)]
    router.get("/", response_model=List[User])(user_list_endpoint)

    app.include_router(router)
    return app

# run example (uvicorn) would be external; for quick test:
# app = create_app()
