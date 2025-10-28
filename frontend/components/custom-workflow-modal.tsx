"use client"

import type React from "react"
import { useState, useEffect } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { TaskAPI } from "@/lib/api"
import type { CreateTaskRequest, Workflow } from "@/types/api"
import { Loader2, Code2 } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

// 定制工作流配置接口
export interface CustomWorkflowConfig<T = any> {
  workflowName: string
  title: string
  description: string
  fixedParams: Record<string, any>
  fixedParamsBuilder: (selectedData: T[]) => Record<string, any>
  selectedDataValidator?: (selectedData: T[]) => { valid: boolean; message?: string }
}

interface CustomWorkflowModalProps<T = any> {
  open: boolean
  onOpenChange: (open: boolean) => void
  onTaskCreated: () => void
  config: CustomWorkflowConfig<T>
  selectedData: T[]
}

export function CustomWorkflowModal<T = any>({
  open,
  onOpenChange,
  onTaskCreated,
  config,
  selectedData,
}: CustomWorkflowModalProps<T>) {
  const [loading, setLoading] = useState(false)
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [targetWorkflow, setTargetWorkflow] = useState<Workflow | null>(null)
  const [dynamicParams, setDynamicParams] = useState<Record<string, any>>({})
  const [fixedParamsPreview, setFixedParamsPreview] = useState<Record<string, any>>({})
  const { toast } = useToast()

  useEffect(() => {
    if (open) {
      fetchWorkflows()
      // 构建固定参数预览
      try {
        const builtParams = config.fixedParamsBuilder(selectedData)
        setFixedParamsPreview(builtParams)
      } catch (error) {
        console.error("Failed to build fixed params:", error)
        setFixedParamsPreview({})
      }
    }
  }, [open, selectedData, config])

  const fetchWorkflows = async () => {
    try {
      const workflowList = await TaskAPI.listWorkflows()
      setWorkflows(workflowList)

      // 查找目标工作流
      const target = workflowList.find((w) => w.name === config.workflowName)
      if (target) {
        setTargetWorkflow(target)
        // 初始化动态参数默认值
        const defaultParams: Record<string, any> = {}
        Object.entries(target.params_schema.properties).forEach(([key, schema]) => {
          if (!config.fixedParams.hasOwnProperty(key)) {
            defaultParams[key] = schema.default !== undefined ? schema.default : ""
          }
        })
        setDynamicParams(defaultParams)
      }
    } catch (error) {
      console.error("Failed to fetch workflows:", error)
      toast({
        title: "错误",
        description: "无法加载工作流列表",
        variant: "destructive",
      })
    }
  }

  const handleArrayInput = (key: string, value: string) => {
    try {
      // 尝试解析为JSON数组
      const parsed = JSON.parse(value)
      if (Array.isArray(parsed)) {
        setDynamicParams((prev) => ({ ...prev, [key]: parsed }))
        return
      }
    } catch {
      // JSON解析失败，按逗号分隔处理
      const items = value
        .split(",")
        .map((item) => item.trim())
        .filter((item) => item.length > 0)
      setDynamicParams((prev) => ({ ...prev, [key]: items }))
    }
  }

  const generateDynamicFormFields = () => {
    if (!targetWorkflow) return null

    const { properties, required = [] } = targetWorkflow.params_schema

    // 过滤掉固定参数，只显示动态参数
    const dynamicProperties = Object.entries(properties).filter(([key]) => !config.fixedParams.hasOwnProperty(key))

    if (dynamicProperties.length === 0) {
      return <div className="text-center py-4 text-muted-foreground">该工作流只需要固定参数，无需额外配置</div>
    }

    return dynamicProperties.map(([key, schema]) => {
      const isRequired = required.includes(key)
      const defaultValue = schema.default !== undefined ? schema.default : ""

      return (
        <div key={key} className="space-y-2">
          <Label htmlFor={key}>
            {schema.title || key}
            {isRequired && <span className="text-destructive ml-1">*</span>}
          </Label>
          {schema.description && <p className="text-sm text-muted-foreground">{schema.description}</p>}

          {schema.type === "array" ? (
            <div className="space-y-2">
              <Textarea
                placeholder={`输入数组值，如: ["值1", "值2"] 或 值1, 值2`}
                className="min-h-[80px]"
                onChange={(e) => handleArrayInput(key, e.target.value)}
                defaultValue={Array.isArray(defaultValue) ? JSON.stringify(defaultValue) : ""}
              />
              <div className="text-xs text-muted-foreground">可以输入JSON数组格式或逗号分隔的值</div>
            </div>
          ) : schema.type === "boolean" ? (
            <Select
              value={dynamicParams[key]?.toString() || defaultValue.toString()}
              onValueChange={(value) => setDynamicParams((prev) => ({ ...prev, [key]: value === "true" }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="选择值" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="true">True</SelectItem>
                <SelectItem value="false">False</SelectItem>
              </SelectContent>
            </Select>
          ) : (
            <Input
              id={key}
              type={schema.type === "integer" || schema.type === "number" ? "number" : "text"}
              placeholder={`输入 ${schema.title || key}`}
              value={dynamicParams[key] || defaultValue}
              onChange={(e) => {
                const value =
                  schema.type === "integer" || schema.type === "number" ? Number(e.target.value) : e.target.value
                setDynamicParams((prev) => ({ ...prev, [key]: value }))
              }}
              required={isRequired}
            />
          )}
        </div>
      )
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // 验证选中的数据
    if (config.selectedDataValidator) {
      const validation = config.selectedDataValidator(selectedData)
      if (!validation.valid) {
        toast({
          title: "数据验证失败",
          description: validation.message || "选中的数据不符合要求",
          variant: "destructive",
        })
        return
      }
    }

    if (!targetWorkflow) {
      toast({
        title: "错误",
        description: "未找到目标工作流",
        variant: "destructive",
      })
      return
    }

    setLoading(true)

    try {
      // 合并固定参数和动态参数
      const allParams = {
        ...dynamicParams,
        ...fixedParamsPreview,
      }

      const request: CreateTaskRequest = {
        name: config.workflowName,
        params: allParams,
      }

      await TaskAPI.createTask(request)

      toast({
        title: "成功",
        description: `${config.title}任务创建成功`,
      })

      // 重置表单
      setDynamicParams({})
      setFixedParamsPreview({})
      onTaskCreated()
    } catch (error) {
      console.error("Failed to create custom workflow task:", error)
      toast({
        title: "错误",
        description: error instanceof Error ? error.message : "创建任务失败",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    if (!loading) {
      setDynamicParams({})
      setFixedParamsPreview({})
      onOpenChange(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Code2 className="h-5 w-5" />
            {config.title}
          </DialogTitle>
          <DialogDescription>{config.description}</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
       

          {/* 固定参数预览 */}
          <div className="space-y-3">
            <Label className="text-base font-medium">固定参数 (自动生成)</Label>
            <div className="p-3 bg-muted rounded-lg">
              <div className="text-xs font-mono bg-background p-3 rounded border max-h-32 overflow-auto">
                <pre>{JSON.stringify(fixedParamsPreview, null, 2)}</pre>
              </div>
            </div>
          </div>

          {/* 动态参数配置 */}
          {targetWorkflow && (
            <div className="space-y-4">
              <Label className="text-base font-medium">动态参数配置</Label>
              <div className="space-y-4">{generateDynamicFormFields()}</div>
            </div>
          )}

          {!targetWorkflow && (
            <div className="text-center py-8">
              <div className="text-muted-foreground">未找到工作流: {config.workflowName}</div>
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose} disabled={loading}>
              取消
            </Button>
            <Button type="submit" disabled={loading || !targetWorkflow}>
              {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              创建任务
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}