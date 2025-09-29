# file: generic_crud_with_filters.py
# [最终、完整版] 支持插件化、参数化、动态UI Schema的通用查询框架

from typing import Optional, List, Any, Type, Dict, Union, get_type_hints, Callable
from typing_extensions import Annotated, get_origin, get_args
from dataclasses import dataclass
import pydantic
import inspect
from enum import Enum
from datetime import date

from fastapi import APIRouter, FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel, create_model
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import Document, init_beanie, PydanticObjectId


# ----------------------------------------------------
# 1. 核心数据结构和辅助函数
# ----------------------------------------------------

@dataclass
class Filter:
    ops: List[str] = None

    def __post_init__(self):
        if self.ops is None:
            self.ops = ["eq", "lt", "lte", "gt", "gte", "in", "contains", "ne", "exists"]


def convert_value_to_bson(field_type: Any, value: Any):
    if field_type in (PydanticObjectId, ObjectId) and value is not None:
        if isinstance(value, list): return [ObjectId(v) for v in value if not isinstance(v, ObjectId)]
        return ObjectId(value) if not isinstance(value, ObjectId) else value
    return value


# ----------------------------------------------------
# 2. 动态 UI Schema 生成器
# ----------------------------------------------------
# ----------------------------------------------------
# 2. 动态 UI Schema 生成器 (已修复)
# ----------------------------------------------------
def generate_filter_schema(
        doc_model: Type[Document],
        custom_query_builders: Optional[Dict[str, Callable]] = None
) -> List[Dict[str, Any]]:
    """
    [完整实现] 为前端动态生成一个描述性的、可用的筛选器 Schema。
    """
    schema = []

    def map_type(t: Any) -> str:
        origin = get_origin(t)
        if origin is Union:
            inner_type = next((arg for arg in get_args(t) if arg is not type(None)), None)
            if inner_type: t = inner_type
        if inspect.isclass(t) and issubclass(t, Enum): return "enum"
        if t is int or t is float: return "integer"
        if t is bool: return "boolean"
        if t is date: return "date"
        if t is str: return "string"
        if inspect.isclass(t) and issubclass(t, pydantic.BaseModel): return "object"
        return "string"

    op_labels = {"eq": "等于", "ne": "不等于", "gt": "大于", "gte": "大于等于", "lt": "小于", "lte": "小于等于",
                 "in": "在...之中", "contains": "包含", "exists": "是否存在"}

    # a. 递归扫描模型字段
    def _build_schema_recursive(model_cls: Type, prefix: str = "", label_prefix: str = ""):
        hints = get_type_hints(model_cls, include_extras=True)
        for field_name, hint in hints.items():
            origin, args = get_origin(hint), get_args(hint)
            base_type = next((arg for arg in args if arg is not type(None)), hint) if origin is Union else hint
            filter_spec, current_type = None, base_type
            if get_origin(base_type) is Annotated:
                annotated_args = get_args(base_type)
                current_type = annotated_args[0]
                if get_origin(current_type) is Union:
                    current_type = next((t for t in get_args(current_type) if t is not type(None)), None)
                for extra in annotated_args[1:]:
                    if isinstance(extra, Filter): filter_spec = extra; break
            if filter_spec:
                field_prefix = f"{prefix}{field_name}"
                human_label_base = f"{label_prefix}{field_name.replace('_', ' ').title()}"
                for op in filter_spec.ops:
                    item_type = "boolean" if op == "exists" else map_type(current_type)
                    item = {"name": f"{field_prefix}__{op}", "field": field_name,
                            "label": f"{human_label_base} {op_labels.get(op, op)}", "type": item_type, "operator": op,
                            "options": None}
                    if item_type == "enum" and inspect.isclass(current_type) and issubclass(current_type, Enum):
                        item["options"] = [e.value for e in current_type]
                    schema.append(item)
            actual_type = get_args(current_type)[0] if get_origin(current_type) is Union else current_type
            if actual_type and inspect.isclass(actual_type) and issubclass(actual_type, pydantic.BaseModel):
                _build_schema_recursive(actual_type, prefix=f"{prefix}{field_name}__",
                                        label_prefix=f"{label_prefix}{field_name.replace('_', ' ').title()} -> ")

    _build_schema_recursive(doc_model)

    # --- [修复] ---
    # b. 为所有已注册的自定义查询生成 Schema 条目
    if custom_query_builders:
        for query_name, builder_func in custom_query_builders.items():
            label = query_name.replace('_', ' ').title()
            try:
                sig = inspect.signature(builder_func)
                if len(sig.parameters) == 0:
                    # 标志查询 (e.g., today_episodes)
                    schema.append({"name": query_name, "field": query_name, "label": label, "type": "boolean",
                                   "operator": "custom_flag", "options": None})
                else:
                    # 参数化查询 (e.g., episodes_on_date)
                    first_param = next(iter(sig.parameters.values()))
                    param_type = first_param.annotation
                    schema.append(
                        {"name": query_name, "field": query_name, "label": label, "type": map_type(param_type),
                         "operator": "custom_param", "options": None})
            except (ValueError, TypeError):
                continue

    return sorted(schema, key=lambda x: x['label'])


# ----------------------------------------------------
# 3. 动态 Pydantic Filter 模型构建器
# ----------------------------------------------------
def build_filter_model(doc_model: Type[Document], custom_query_builders: Optional[Dict[str, Callable]] = None) -> Type[
    BaseModel]:
    model_fields: Dict[str, tuple] = {}

    def _build_fields_recursive(model_cls: Type, prefix: str = ""):
        hints = get_type_hints(model_cls, include_extras=True)
        for field_name, hint in hints.items():
            origin = get_origin(hint)
            args = get_args(hint)
            base_type = next((arg for arg in args if arg is not type(None)), hint) if origin is Union else hint
            filter_spec = None
            current_type = base_type
            if get_origin(base_type) is Annotated:
                annotated_args = get_args(base_type)
                current_type = annotated_args[0]
                if get_origin(current_type) is Union and type(None) in get_args(current_type):
                    current_type = next((t for t in get_args(current_type) if t is not type(None)), None)
                for extra in annotated_args[1:]:
                    if isinstance(extra, Filter): filter_spec = extra; break
            if filter_spec:
                field_prefix = f"{prefix}{field_name}"
                for op in filter_spec.ops:
                    field_key = f"{field_prefix}__{op}"
                    if op == "in":
                        field_type = Optional[List[current_type]]
                    elif op == "exists":
                        field_type = Optional[bool]
                    elif op in ["eq", "ne"]:
                        field_type = Optional[Union[current_type, str]]
                    else:
                        field_type = Optional[current_type]
                    model_fields[field_key] = (field_type, None)
            actual_type = get_args(current_type)[0] if get_origin(current_type) is Union and type(None) in get_args(
                current_type) else current_type
            if actual_type and inspect.isclass(actual_type) and issubclass(actual_type, pydantic.BaseModel):
                _build_fields_recursive(actual_type, prefix=f"{prefix}{field_name}__")

    _build_fields_recursive(doc_model)
    if custom_query_builders:
        for query_name, builder_func in custom_query_builders.items():
            try:
                sig = inspect.signature(builder_func)
                if len(sig.parameters) == 0:
                    field_type = Optional[bool]
                else:
                    first_param = next(iter(sig.parameters.values()))
                    param_type = first_param.annotation
                    field_type = Optional[param_type if param_type != inspect.Parameter.empty else Any]
            except (ValueError, TypeError):
                field_type = Optional[Any]
            model_fields[query_name] = (field_type, None)
    model_fields.setdefault("limit", (Optional[int], 50))
    model_fields.setdefault("skip", (Optional[int], 0))
    model_fields.setdefault("sort_by", (Optional[str], None))
    return create_model(f"{doc_model.__name__}FilterModel", **model_fields)


# ----------------------------------------------------
# 4. MongoDB 查询构建器
# ----------------------------------------------------
def build_mongo_filter_from_model(doc_model: Type[Document], filter_model: BaseModel) -> Dict[str, Any]:
    mongo_filter: Dict[str, Any] = {}
    op_map = {"lt": "$lt", "lte": "$lte", "gt": "$gt", "gte": "$gte", "in": "$in", "ne": "$ne"}
    for key, value in filter_model.dict(exclude_none=True).items():
        if key in ("limit", "skip", "sort_by") or "__" not in key: continue
        field_path, op = key.rsplit("__", 1)
        mongo_field = field_path.replace("__", ".")
        processed_value = None if isinstance(value, str) and value.lower() == 'null' else value
        hints = get_type_hints(doc_model, include_extras=True)
        base_type = hints.get(field_path.split('__')[0], Any)
        converted = convert_value_to_bson(base_type, processed_value)
        if op == "exists":
            is_true = str(converted).lower() in ['true', '1', 'yes']
            mongo_filter[mongo_field] = {"$exists": True, "$ne": None} if is_true else {"$eq": None}
        elif op == "eq":
            mongo_filter[mongo_field] = converted
        elif op == "contains":
            mongo_filter[mongo_field] = {
                "$regex": processed_value if not isinstance(processed_value, list) else "|".join(
                    map(str, processed_value)), "$options": "i"}
        elif op in op_map:
            mongo_filter.setdefault(mongo_field, {})
            mongo_filter[mongo_field].update({op_map[op]: converted})
    return mongo_filter


# ----------------------------------------------------
# 5. 可扩展的通用仓储层 (Repository)
# ----------------------------------------------------
class GenericRepository:
    def __init__(self, model: Type[Document], id_field: str = "_id",
                 custom_query_builders: Optional[Dict[str, Callable]] = None):
        self.model = model
        self.id_field = id_field
        self.custom_query_builders = custom_query_builders or {}
        self.FilterModel = build_filter_model(self.model, self.custom_query_builders)

    async def find(self, filters: Dict[str, Any], limit: int = 50, skip: int = 0, sort_by: Optional[str] = None) -> \
    List[Document]:
        and_clauses = []
        custom_params = {}
        generic_params = {}
        for key, value in filters.items():
            if key in self.custom_query_builders:
                custom_params[key] = value
            else:
                generic_params[key] = value
        if generic_params:
            generic_filter_model = self.FilterModel(**generic_params)
            generic_mongo_filter = build_mongo_filter_from_model(self.model, generic_filter_model)
            if generic_mongo_filter: and_clauses.append(generic_mongo_filter)
        for key, value in custom_params.items():
            builder_func = self.custom_query_builders[key]
            sig = inspect.signature(builder_func)
            custom_mongo_filter = None
            if len(sig.parameters) == 0:
                if value is True: custom_mongo_filter = builder_func()
            else:
                if value is not None: custom_mongo_filter = builder_func(value)
            if custom_mongo_filter: and_clauses.append(custom_mongo_filter)
        final_mongo_filter = {"$and": and_clauses} if len(and_clauses) > 1 else (and_clauses[0] if and_clauses else {})
        coll = self.model.get_pymongo_collection()
        cursor = coll.find(final_mongo_filter).skip(skip).limit(limit)
        if sort_by:
            direction = -1 if sort_by.startswith("-") else 1
            field = sort_by.lstrip('-')
            cursor = cursor.sort(field, direction)
        docs = await cursor.to_list(length=limit)
        return [self.model.parse_obj(d) for d in docs]

    def _parse_id_value(self, raw_value: Any):
        hints = get_type_hints(self.model, include_extras=True)
        hint = hints.get(self.id_field, None)
        base_type = get_args(hint)[0] if get_origin(hint) is Annotated else hint if hint else Any
        return convert_value_to_bson(base_type, raw_value)

    async def create(self, payload: dict) -> Document:
        coll = self.model.get_pymongo_collection()
        if self.id_field in payload:
            try:
                payload[self.id_field] = self._parse_id_value(payload[self.id_field])
            except Exception:
                pass
        res = await coll.insert_one(payload)
        doc = await coll.find_one({"_id": res.inserted_id})
        return self.model.parse_obj(doc)

    async def get_by_id(self, item_id: Any) -> Optional[Document]:
        coll = self.model.get_pymongo_collection()
        parsed_id = self._parse_id_value(item_id)
        doc = await coll.find_one({self.id_field: parsed_id})
        return self.model.parse_obj(doc) if doc else None

    async def update(self, item_id: Any, payload: dict) -> Optional[Document]:
        coll = self.model.get_pymongo_collection()
        parsed_id = self._parse_id_value(item_id)
        res = await coll.update_one({self.id_field: parsed_id}, {"$set": payload})
        if res.matched_count == 0: return None
        return await self.get_by_id(item_id)

    async def delete(self, item_id: Any) -> bool:
        coll = self.model.get_pymongo_collection()
        parsed_id = self._parse_id_value(item_id)
        res = await coll.delete_one({self.id_field: parsed_id})
        return res.deleted_count > 0


# ----------------------------------------------------
# 6. 可扩展的通用 API 路由层 (Router)
# ----------------------------------------------------
class GenericCRUDRouter:
    def __init__(self, model: Type[Document], prefix: Optional[str] = None, tags: Optional[List[str]] = None,
                 id_field: str = "_id", custom_query_builders: Optional[Dict[str, Callable]] = None):
        self.model = model
        self.router = APIRouter(prefix=prefix or f"/{model.__name__.lower()}s", tags=tags or [model.__name__])
        self.repository = GenericRepository(model, id_field=id_field, custom_query_builders=custom_query_builders)
        self.FilterModel = self.repository.FilterModel
        self.router.get("/", response_model=List[model])(self.list_many())
        self.router.get("/filters", response_model=List[Dict[str, Any]], summary="获取可用的筛选器 Schema")(
            self.get_filter_schema)
        self.router.post("/", response_model=model)(self.create_one)
        self.router.get("/{item_id}", response_model=model)(self.get_one)
        self.router.patch("/{item_id}", response_model=model)(self.update_one)
        self.router.delete("/{item_id}")(self.delete_one)

    def list_many(self):
        repo = self.repository

        async def endpoint(filters: repo.FilterModel = Depends()):
            filter_dict = filters.dict(exclude_none=True)
            return await repo.find(filters=filter_dict, limit=filter_dict.get('limit', 50),
                                   skip=filter_dict.get('skip', 0), sort_by=filter_dict.get('sort_by'))

        return endpoint

    async def get_filter_schema(self):
        return generate_filter_schema(self.model, self.repository.custom_query_builders)

    async def create_one(self, payload: dict):
        return await self.repository.create(payload)

    async def get_one(self, item_id: str):
        doc = await self.repository.get_by_id(item_id)
        if not doc: raise HTTPException(status_code=404, detail="Not found")
        return doc

    async def update_one(self, item_id: str, payload: dict):
        updated_doc = await self.repository.update(item_id, payload)
        if not updated_doc: raise HTTPException(status_code=404, detail="Not found")
        return updated_doc

    async def delete_one(self, item_id: str):
        success = await self.repository.delete(item_id)
        if not success: raise HTTPException(status_code=404, detail="Not found")
        return {"deleted": True, "id": item_id}