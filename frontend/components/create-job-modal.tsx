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
import { TaskAPI } from "@/lib/api"
import type { CreateJobRequest, Workflow } from "@/types/api"
import { Loader2, Clock, X } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { Textarea } from "@/components/ui/textarea"

interface CreateJobModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onJobCreated: () => void
}

const COMMON_CRON_EXPRESSIONS = [
  { label: "Every minute", value: "* * * * *" },
  { label: "Every 5 minutes", value: "*/5 * * * *" },
  { label: "Every 15 minutes", value: "*/15 * * * *" },
  { label: "Every 30 minutes", value: "*/30 * * * *" },
  { label: "Every hour", value: "0 * * * *" },
  { label: "Every 6 hours", value: "0 */6 * * *" },
  { label: "Every 12 hours", value: "0 */12 * * *" },
  { label: "Daily at midnight", value: "0 0 * * *" },
  { label: "Daily at 6 AM", value: "0 6 * * *" },
  { label: "Daily at 12 PM", value: "0 12 * * *" },
  { label: "Weekly on Sunday", value: "0 0 * * 0" },
  { label: "Monthly on 1st", value: "0 0 1 * *" },
]

const TIMEZONES = [
  "UTC",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Paris",
  "Europe/Berlin",
  "Asia/Tokyo",
  "Asia/Shanghai",
  "Asia/Kolkata",
  "Australia/Sydney",
]

export function CreateJobModal({ open, onOpenChange, onJobCreated }: CreateJobModalProps) {
  const [loading, setLoading] = useState(false)
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [selectedWorkflow, setSelectedWorkflow] = useState<string>("")
  const [customTaskName, setCustomTaskName] = useState("")
  const [useCustomName, setUseCustomName] = useState(false)
  const [cron, setCron] = useState("")
  const [customCron, setCustomCron] = useState("")
  const [useCustomCron, setUseCustomCron] = useState(false)
  const [timezone, setTimezone] = useState("UTC")
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

  // ✅ 这里预填充 schema 默认值
  useEffect(() => {
    if (selectedWorkflowData) {
      const { properties, required = [] } = selectedWorkflowData.params_schema
      const initialParams: Record<string, any> = {}

      Object.entries(properties).forEach(([key, schema]) => {
        if (schema.default !== undefined) {
          initialParams[key] = schema.default
        } else if (required.includes(key)) {
          initialParams[key] = "" // required 但无默认值，留空让用户填
        }
      })

      setParams(initialParams)
    }
  }, [selectedWorkflowData])

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
              value={params[key] ?? defaultValue}
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

  const handleArrayInput = (key: string, value: string) => {
    try {
      const parsed = JSON.parse(value)
      if (Array.isArray(parsed)) {
        setParams((prev) => ({ ...prev, [key]: parsed }))
        return
      }
    } catch {
      const items = value
        .split(",")
        .map((item) => item.trim())
        .filter((item) => item.length > 0)
      setParams((prev) => ({ ...prev, [key]: items }))
    }
  }

  const removeArrayItem = (key: string, index: number) => {
    const currentArray = params[key] || []
    const newArray = currentArray.filter((_: any, i: number) => i !== index)
    setParams((prev) => ({ ...prev, [key]: newArray }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    const finalTaskName = useCustomName ? customTaskName : selectedWorkflow
    const finalCron = useCustomCron ? customCron : cron

    if (!finalTaskName.trim()) {
      toast({
        title: "Error",
        description: "Please select a workflow or enter a custom task name",
        variant: "destructive",
      })
      return
    }

    if (!finalCron.trim()) {
      toast({
        title: "Error",
        description: "Please select or enter a cron expression",
        variant: "destructive",
      })
      return
    }

    setLoading(true)

    try {
      const request: CreateJobRequest = {
        task_name: finalTaskName.trim(),
        cron: finalCron.trim(),
        params: params,
        tz: timezone,
        enabled: true,
      }

      const result = await TaskAPI.createJob(request)
      console.log("[v0] Job creation result:", result)

      toast({
        title: "Success",
        description: "Scheduled job created successfully",
      })

      // Reset form
      setSelectedWorkflow("")
      setCustomTaskName("")
      setUseCustomName(false)
      setCron("")
      setCustomCron("")
      setUseCustomCron(false)
      setTimezone("UTC")
      setParams({})

      onJobCreated()
    } catch (error) {
      console.error("[v0] Failed to create job:", error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to create job",
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
      setCron("")
      setCustomCron("")
      setUseCustomCron(false)
      setTimezone("UTC")
      setParams({})
      onOpenChange(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create Scheduled Job</DialogTitle>
          <DialogDescription>Create a new scheduled job to run tasks automatically</DialogDescription>
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

          {/* Schedule Configuration */}
          <div className="space-y-4">
            <Label className="flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Schedule Configuration
            </Label>

            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <input
                  type="radio"
                  id="preset-cron"
                  name="cronType"
                  checked={!useCustomCron}
                  onChange={() => setUseCustomCron(false)}
                  className="h-4 w-4"
                />
                <Label htmlFor="preset-cron">Select common schedule</Label>
              </div>

              {!useCustomCron && (
                <Select value={cron} onValueChange={setCron}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a schedule" />
                  </SelectTrigger>
                  <SelectContent>
                    {COMMON_CRON_EXPRESSIONS.map((expr) => (
                      <SelectItem key={expr.value} value={expr.value}>
                        {expr.label} ({expr.value})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}

              <div className="flex items-center space-x-2">
                <input
                  type="radio"
                  id="custom-cron"
                  name="cronType"
                  checked={useCustomCron}
                  onChange={() => setUseCustomCron(true)}
                  className="h-4 w-4"
                />
                <Label htmlFor="custom-cron">Enter custom cron expression</Label>
              </div>

              {useCustomCron && (
                <Input
                  placeholder="Enter cron expression (e.g., 0 */6 * * *)"
                  value={customCron}
                  onChange={(e) => setCustomCron(e.target.value)}
                />
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="timezone">Timezone</Label>
              <Select value={timezone} onValueChange={setTimezone}>
                <SelectTrigger>
                  <SelectValue placeholder="Select timezone" />
                </SelectTrigger>
                <SelectContent>
                  {TIMEZONES.map((tz) => (
                    <SelectItem key={tz} value={tz}>
                      {tz}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
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
              Create Job
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
