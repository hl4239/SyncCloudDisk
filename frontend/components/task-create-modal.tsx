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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { TaskAPI } from "@/lib/api"
import type { CreateTaskRequest, Workflow } from "@/types/api"
import { Loader2, X } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

interface TaskCreateModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onTaskCreated: () => void
}

export function TaskCreateModal({ open, onOpenChange, onTaskCreated }: TaskCreateModalProps) {
  const [loading, setLoading] = useState(false)
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [selectedWorkflow, setSelectedWorkflow] = useState<string>("")
  const [customTaskName, setCustomTaskName] = useState("")
  const [useCustomName, setUseCustomName] = useState(false)
  const [params, setParams] = useState<Record<string, any>>({})
  const { toast } = useToast()

  useEffect(() => {
    if (open) {
      fetchWorkflows()
    }
  }, [open])

  const fetchWorkflows = async () => {
    try {
      const workflowList = await TaskAPI.listWorkflows()
      setWorkflows(workflowList)
    } catch (error) {
      console.error("Failed to fetch workflows:", error)
      toast({
        title: "Error",
        description: "Failed to load available workflows",
        variant: "destructive",
      })
    }
  }

  const selectedWorkflowData = workflows.find((w) => w.name === selectedWorkflow)

  const handleArrayInput = (key: string, value: string) => {
    try {
      // Try to parse as JSON array first
      const parsed = JSON.parse(value)
      if (Array.isArray(parsed)) {
        setParams((prev) => ({ ...prev, [key]: parsed }))
        return
      }
    } catch {
      // If JSON parsing fails, treat as comma-separated values
      const items = value
        .split(",")
        .map((item) => item.trim())
        .filter((item) => item.length > 0)
      setParams((prev) => ({ ...prev, [key]: items }))
    }
  }

  const addArrayItem = (key: string, item: string) => {
    if (!item.trim()) return
    const currentArray = params[key] || []
    setParams((prev) => ({ ...prev, [key]: [...currentArray, item.trim()] }))
  }

  const removeArrayItem = (key: string, index: number) => {
    const currentArray = params[key] || []
    const newArray = currentArray.filter((_: any, i: number) => i !== index)
    setParams((prev) => ({ ...prev, [key]: newArray }))
  }

  const generateFormFields = () => {
    if (!selectedWorkflowData) return null

    const { properties, required = [] } = selectedWorkflowData.params_schema

    return Object.entries(properties).map(([key, schema]) => {
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
            <div className="space-y-3">
              {params[key] && params[key].length > 0 && (
                <div className="space-y-2">
                  <div className="text-sm font-medium">Current items:</div>
                  <div className="space-y-1">
                    {params[key].map((item: string, index: number) => (
                      <div key={index} className="flex items-center gap-2 p-2 bg-muted rounded">
                        <span className="flex-1 text-sm">{item}</span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeArrayItem(key, index)}
                          className="h-6 w-6 p-0"
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div className="space-y-2">
                <div className="text-sm font-medium">Add items:</div>
                <Textarea
                  placeholder={`Enter items as JSON array: ["China", "USA"] or comma-separated: China, USA`}
                  className="min-h-[80px]"
                  onChange={(e) => handleArrayInput(key, e.target.value)}
                />
                <div className="text-xs text-muted-foreground">
                  You can enter items as a JSON array or comma-separated values
                </div>
              </div>
            </div>
          ) : schema.type === "boolean" ? (
            <Select
              value={params[key]?.toString() || defaultValue.toString()}
              onValueChange={(value) => setParams((prev) => ({ ...prev, [key]: value === "true" }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select value" />
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
              placeholder={`Enter ${schema.title || key}`}
              value={params[key] || defaultValue}
              onChange={(e) => {
                const value =
                  schema.type === "integer" || schema.type === "number" ? Number(e.target.value) : e.target.value
                setParams((prev) => ({ ...prev, [key]: value }))
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

    const finalTaskName = useCustomName ? customTaskName : selectedWorkflow

    if (!finalTaskName.trim()) {
      toast({
        title: "Error",
        description: "Please select a workflow or enter a custom task name",
        variant: "destructive",
      })
      return
    }

    setLoading(true)

    try {
      const request: CreateTaskRequest = {
        name: finalTaskName.trim(),
        params: params,
      }

      await TaskAPI.createTask(request)

      toast({
        title: "Success",
        description: "Task created successfully",
      })

      // Reset form
      setSelectedWorkflow("")
      setCustomTaskName("")
      setUseCustomName(false)
      setParams({})

      onTaskCreated()
    } catch (error) {
      console.error("Failed to create task:", error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to create task",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    if (!loading) {
      setSelectedWorkflow("")
      setCustomTaskName("")
      setUseCustomName(false)
      setParams({})
      onOpenChange(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create New Task</DialogTitle>
          <DialogDescription>Create a new background task from available workflows</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Task Selection */}
          <div className="space-y-4">
            <Label>Task Type</Label>
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <input
                  type="radio"
                  id="workflow"
                  name="taskType"
                  checked={!useCustomName}
                  onChange={() => setUseCustomName(false)}
                  className="h-4 w-4"
                />
                <Label htmlFor="workflow">Select from available workflows</Label>
              </div>

              {!useCustomName && (
                <Select value={selectedWorkflow} onValueChange={setSelectedWorkflow}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a workflow" />
                  </SelectTrigger>
                  <SelectContent>
                    {workflows.map((workflow) => (
                      <SelectItem key={workflow.name} value={workflow.name}>
                        {workflow.name.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}

              <div className="flex items-center space-x-2">
                <input
                  type="radio"
                  id="custom"
                  name="taskType"
                  checked={useCustomName}
                  onChange={() => setUseCustomName(true)}
                  className="h-4 w-4"
                />
                <Label htmlFor="custom">Enter custom task name</Label>
              </div>

              {useCustomName && (
                <Input
                  placeholder="Enter custom task name"
                  value={customTaskName}
                  onChange={(e) => setCustomTaskName(e.target.value)}
                />
              )}
            </div>
          </div>

          {/* Parameters */}
          {selectedWorkflowData && !useCustomName && (
            <div className="space-y-4">
              <Label>Parameters</Label>
              <div className="space-y-4">{generateFormFields()}</div>
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Create Task
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
