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
import type { UpdateJobRequest, ScheduledJob } from "@/types/api"
import { Loader2, Clock } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

interface EditJobModalProps {
  job: ScheduledJob
  open: boolean
  onOpenChange: (open: boolean) => void
  onJobUpdated: () => void
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

export function EditJobModal({ job, open, onOpenChange, onJobUpdated }: EditJobModalProps) {
  const [loading, setLoading] = useState(false)
  const [cron, setCron] = useState(job.cron)
  const [params, setParams] = useState<Record<string, any>>(job.params || {})
  const { toast } = useToast()

  useEffect(() => {
    setCron(job.cron)
    setParams(job.params || {})
  }, [job])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!cron.trim()) {
      toast({
        title: "Error",
        description: "Please enter a cron expression",
        variant: "destructive",
      })
      return
    }

    setLoading(true)

    try {
      const request: UpdateJobRequest = {
        cron: cron.trim(),
        params: params,
      }

      await TaskAPI.updateJob(job.job_id, request)

      toast({
        title: "Success",
        description: "Job updated successfully",
      })

      onJobUpdated()
    } catch (error) {
      console.error("Failed to update job:", error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to update job",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    if (!loading) {
      onOpenChange(false)
    }
  }

  const updateParam = (key: string, value: any) => {
    setParams((prev) => ({ ...prev, [key]: value }))
  }

  const removeParam = (key: string) => {
    setParams((prev) => {
      const newParams = { ...prev }
      delete newParams[key]
      return newParams
    })
  }

  const addParam = () => {
    const key = prompt("Enter parameter name:")
    if (key && key.trim()) {
      setParams((prev) => ({ ...prev, [key.trim()]: "" }))
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit Scheduled Job</DialogTitle>
          <DialogDescription>Update the schedule and parameters for "{job.task_name}"</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Job Info */}
          <div className="space-y-2">
            <Label>Task Name</Label>
            <Input value={job.task_name} disabled />
          </div>

          {/* Schedule Configuration */}
          <div className="space-y-4">
            <Label className="flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Schedule Configuration
            </Label>

            <div className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="cron-select">Common Schedules</Label>
                <Select value={cron} onValueChange={setCron}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a schedule or enter custom" />
                  </SelectTrigger>
                  <SelectContent>
                    {COMMON_CRON_EXPRESSIONS.map((expr) => (
                      <SelectItem key={expr.value} value={expr.value}>
                        {expr.label} ({expr.value})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="cron-input">Custom Cron Expression</Label>
                <Input
                  id="cron-input"
                  placeholder="Enter cron expression (e.g., 0 */6 * * *)"
                  value={cron}
                  onChange={(e) => setCron(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Parameters */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>Parameters</Label>
              <Button type="button" variant="outline" size="sm" onClick={addParam}>
                Add Parameter
              </Button>
            </div>

            {Object.keys(params).length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No parameters configured. Click "Add Parameter" to add some.
              </p>
            ) : (
              <div className="space-y-3">
                {Object.entries(params).map(([key, value]) => (
                  <div key={key} className="flex items-center gap-3 p-3 border rounded-lg">
                    <div className="flex-1">
                      <Label className="text-sm font-medium">{key}</Label>
                    </div>
                    <div className="flex-2">
                      <Input
                        value={typeof value === "object" ? JSON.stringify(value) : value}
                        onChange={(e) => {
                          try {
                            // Try to parse as JSON first
                            const parsed = JSON.parse(e.target.value)
                            updateParam(key, parsed)
                          } catch {
                            // If not valid JSON, treat as string
                            updateParam(key, e.target.value)
                          }
                        }}
                        placeholder="Parameter value"
                      />
                    </div>
                    <Button type="button" variant="outline" size="sm" onClick={() => removeParam(key)}>
                      Remove
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Update Job
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
