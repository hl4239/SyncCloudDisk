# app/api/workflows.py
import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel as PydanticBaseModel

from app.core.task_registry import registry

router = APIRouter()
logger = logging.getLogger(__name__)

# ---------- Response models ----------
class WorkflowSummary(PydanticBaseModel):
    name: str
    has_params: bool


class WorkflowDetail(PydanticBaseModel):
    name: str
    # Pydantic 模型生成的 JSON Schema；若无 params_model 则为 None
    params_schema: Optional[Dict[str, Any]] = None
    # 从 schema 自动提取到的 example（只有包含 default 时才有对应项），可选
    params_example: Optional[Dict[str, Any]] = None
    # 可读型模型信息（module + class name）
    params_model_name: Optional[str] = None
    params_model_module: Optional[str] = None


# ---------- Helper utils ----------
_schema_cache: Dict[str, Dict[str, Any]] = {}
_example_cache: Dict[str, Dict[str, Any]] = {}


def _entry_to_summary(name: str) -> WorkflowSummary:
    try:
        entry = registry.get(name)
    except KeyError:
        return WorkflowSummary(name=name, has_params=False)

    has_params = bool(getattr(entry, "params_model", None))
    return WorkflowSummary(name=name, has_params=has_params)


def _model_to_schema_and_example(model_cls: type, include_examples: bool = True) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    将 Pydantic v2 model -> (json_schema_dict, example_dict)
    - 用缓存避免重复生成 schema（键使用模块+类名）
    - example_dict 从 JSON Schema 的 properties 中提取每个字段的 default（如果存在）
    - 如果生成 schema 失败，会返回一个简单的 error schema 而不是抛出，保证 API 的稳定性
    """
    key = f"{getattr(model_cls, '__module__', '<mod>')}.{getattr(model_cls, '__name__', str(model_cls))}"

    # schema 缓存
    cached_schema = _schema_cache.get(key)
    if cached_schema is None:
        try:
            # Pydantic v2: model_json_schema()
            schema = model_cls.model_json_schema()
            # 将 schema 存缓存（浅拷贝）
            _schema_cache[key] = schema
            cached_schema = schema
        except Exception as e:
            logger.exception("failed to build json schema for model %s: %s", key, e)
            # 返回错误信息作为 schema，避免抛 500（前端更友好）
            cached_schema = {"__schema_error__": str(e)}
            _schema_cache[key] = cached_schema

    example: Optional[Dict[str, Any]] = None
    if include_examples:
        cached_example = _example_cache.get(key)
        if cached_example is not None:
            example = cached_example
        else:
            example = {}
            try:
                props = cached_schema.get("properties", {}) if isinstance(cached_schema, dict) else {}
                # 如果 schema 包含 $ref 或 $defs，props 可能为空；在这种情况下 example 保持为空
                for field_name, field_schema in props.items():
                    if isinstance(field_schema, dict) and "default" in field_schema:
                        example[field_name] = field_schema["default"]
                if not example:
                    example = None
            except Exception:
                # 忽略示例提取错误，但记录日志
                logger.exception("failed to extract defaults for model %s", key)
                example = None

            # cache example (可能为 None)
            _example_cache[key] = example

    return cached_schema, example


# ---------- Endpoints ----------
@router.get("", response_model=List[WorkflowDetail])
async def list_workflows(detail: bool = Query(True, description="是否包含每个工作流的详细 params 信息（schema & example）。默认 true。"),
                         include_examples: bool = Query(True, description="是否从 schema 中提取默认值作为示例。默认 true。")):
    """
    列出所有已注册的工作流，并（可选）返回每个工作流的参数 JSON Schema 与示例值（如果存在）。
    - detail=True (默认): 返回每个工作流的详细信息（WorkflowDetail）
    - detail=False: 仅返回 name + has_params（等同于旧的 list 接口）
    """
    names = registry.list_names()
    results: List[WorkflowDetail] = []

    for name in names:
        try:
            entry = registry.get(name)
        except KeyError:
            # registry.list_names() 返回的名字理应有效，但若发生不一致，跳过并记录
            logger.warning("registry reported name %s but registry.get failed", name)
            results.append(WorkflowDetail(name=name, params_schema=None, params_example=None,
                                          params_model_name=None, params_model_module=None))
            continue

        model_cls = getattr(entry, "params_model", None)
        if not detail:
            results.append(WorkflowDetail(name=name,
                                          params_schema=None,
                                          params_example=None,
                                          params_model_name=(getattr(model_cls, "__name__", None) if model_cls else None),
                                          params_model_module=(getattr(model_cls, "__module__", None) if model_cls else None)))
            continue

        if not model_cls:
            # 无参数模型
            results.append(WorkflowDetail(name=name, params_schema=None, params_example=None,
                                          params_model_name=None, params_model_module=None))
            continue

        # 有 params_model：尽量安全地生成 schema 和示例
        try:
            schema, example = _model_to_schema_and_example(model_cls, include_examples=include_examples)
        except Exception as e:
            # 不应发生，但兜底
            logger.exception("unexpected error creating schema for %s: %s", name, e)
            schema, example = {"__schema_error__": str(e)}, None

        model_name = getattr(model_cls, "__name__", str(model_cls))
        model_module = getattr(model_cls, "__module__", "<unknown>")

        results.append(WorkflowDetail(name=name,
                                      params_schema=schema,
                                      params_example=example,
                                      params_model_name=model_name,
                                      params_model_module=model_module))

    return results


# 保留兼容的按名查询端点（如果未来仍需）
@router.get("/{workflow_name}", response_model=WorkflowDetail)
async def get_workflow_detail(workflow_name: str, include_examples: bool = Query(True, description="是否提取示例")):
    """
    向后兼容的单工作流详情查询（仍然可用），但 /workflows (list) 已包含所有详情。
    """
    try:
        entry = registry.get(workflow_name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"workflow '{workflow_name}' not found")

    model_cls = getattr(entry, "params_model", None)
    if not model_cls:
        return WorkflowDetail(name=workflow_name, params_schema=None, params_example=None,
                              params_model_name=None, params_model_module=None)

    schema, example = _model_to_schema_and_example(model_cls, include_examples=include_examples)
    model_name = getattr(model_cls, "__name__", str(model_cls))
    model_module = getattr(model_cls, "__module__", "<unknown>")

    return WorkflowDetail(name=workflow_name,
                          params_schema=schema,
                          params_example=example,
                          params_model_name=model_name,
                          params_model_module=model_module)
