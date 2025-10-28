"use client"

import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { TaskAPI } from "@/lib/api"
import type { Task } from "@/types/task"
import {
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Pause,
  RefreshCw,
  Calendar,
  Settings,
  FileText,
  Trash2,
  Copy,
} from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { formatTime, formatDuration } from "@/lib/time-utils"

interface TaskDetailsModalProps {
  task: Task
  open: boolean
  onOpenChange: (open: boolean) => void
  onTaskUpdated: () => void
}

const statusIcons = {
  PENDING: <Clock className="h-5 w-5" />,
  RUNNING: <RefreshCw className="h-5 w-5 animate-spin" />,
  COMPLETED: <CheckCircle className="h-5 w-5" />,
  FAILED: <XCircle className="h-5 w-5" />,
  CANCELLED: <Pause className="h-5 w-5" />,
}

const statusColors = {
  PENDING:
    "bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/20 dark:text-yellow-300 dark:border-yellow-800",
  RUNNING: "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-800",
  COMPLETED:
    "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-800",
  FAILED: "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-800",
  CANCELLED: "bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-900/20 dark:text-gray-300 dark:border-gray-800",
}

const statusLabels = {
  PENDING: "等待中",
  RUNNING: "运行中",
  COMPLETED: "已完成",
  FAILED: "失败",
  CANCELLED: "已取消",
}

export function TaskDetailsModal({ task: initialTask, open, onOpenChange, onTaskUpdated }: TaskDetailsModalProps) {
  const [task, setTask] = useState<Task>(initialTask)
  const [logs, setLogs] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const { toast } = useToast()

  // Update task when prop changes
  useEffect(() => {
    setTask(initialTask)
  }, [initialTask])

  // Fetch detailed task info and logs when modal opens
  useEffect(() => {
    if (open && task.id) {
      fetchTaskDetails()
      fetchLogs()
    }
  }, [open, task.id])

  // Auto-refresh for running tasks
  useEffect(() => {
    if (!open || task.status !== "RUNNING") return

    const interval = setInterval(() => {
      fetchTaskDetails()
    }, 3000)

    return () => clearInterval(interval)
  }, [open, task.status])

  const fetchTaskDetails = async () => {
    try {
      const updatedTask = await TaskAPI.getTask(task.id)
      setTask(updatedTask)
    } catch (error) {
      console.error("Failed to fetch task details:", error)
    }
  }

  const fetchLogs = async () => {
    try {
      setLoading(true)
      const taskLogs = await TaskAPI.getTaskLogs(task.id)
      setLogs(taskLogs)
    } catch (error) {
      console.error("Failed to fetch logs:", error)
      toast({
        title: "错误",
        description: "获取任务日志失败",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = async () => {
    if (task.status !== "RUNNING" && task.status !== "PENDING") {
      toast({
        title: "无法取消",
        description: "只有运行中或等待中的任务可以取消",
        variant: "destructive",
      })
      return
    }

    setCancelling(true)
    try {
      const result = await TaskAPI.cancelTask(task.id)
      if (result.cancel_requested) {
        toast({
          title: "成功",
          description: "任务取消请求已发送",
        })
        await fetchTaskDetails()
        onTaskUpdated()
      } else {
        toast({
          title: "警告",
          description: "无法发送任务取消请求",
          variant: "destructive",
        })
      }
    } catch (error) {
      console.error("Failed to cancel task:", error)
      toast({
        title: "错误",
        description: "取消任务失败",
        variant: "destructive",
      })
    } finally {
      setCancelling(false)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast({
      title: "已复制",
      description: "已复制到剪贴板",
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {statusIcons[task.status]}
              <div>
                <DialogTitle className="text-xl">{task.name}</DialogTitle>
                <DialogDescription>任务ID: {task.id}</DialogDescription>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge className={statusColors[task.status]}>{statusLabels[task.status]}</Badge>
              {(task.status === "RUNNING" || task.status === "PENDING") && (
                <Button variant="destructive" size="sm" onClick={handleCancel} disabled={cancelling}>
                  {cancelling ? (
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Trash2 className="h-4 w-4 mr-2" />
                  )}
                  取消
                </Button>
              )}
            </div>
          </div>
        </DialogHeader>

        <Tabs defaultValue="overview" className="flex-1 overflow-hidden">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">概览</TabsTrigger>
            <TabsTrigger value="parameters">参数</TabsTrigger>
            <TabsTrigger value="result">结果</TabsTrigger>
            <TabsTrigger value="logs">日志</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4 overflow-y-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">状态</CardTitle>
                  {statusIcons[task.status]}
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{statusLabels[task.status]}</div>
                  {task.status === "RUNNING" && (
                    <div className="mt-2">
                      <div className="flex items-center justify-between text-sm">
                        <span>进度</span>
                        <span>{task.progress.toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-muted rounded-full h-2 mt-1">
                        <div
                          className="bg-primary h-2 rounded-full transition-all duration-300"
                          style={{ width: `${task.progress}%` }}
                        />
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">时间信息</CardTitle>
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="text-muted-foreground">创建时间:</span>
                      <br />
                      {formatTime(task.created_at)}
                    </div>
                    {task.started_at && (
                      <div>
                        <span className="text-muted-foreground">开始时间:</span>
                        <br />
                        {formatTime(task.started_at)}
                      </div>
                    )}
                    {task.finished_at && (
                      <div>
                        <span className="text-muted-foreground">完成时间:</span>
                        <br />
                        {formatTime(task.finished_at)}
                      </div>
                    )}
                    {task.started_at && (
                      <div>
                        <span className="text-muted-foreground">持续时间:</span>
                        <br />
                        {formatDuration(task.started_at, task.finished_at)}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            {task.error && (
              <Card className="border-destructive">
                <CardHeader>
                  <CardTitle className="text-destructive flex items-center gap-2">
                    <AlertCircle className="h-5 w-5" />
                    错误详情
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="bg-destructive/10 p-3 rounded-md">
                    <pre className="text-sm whitespace-pre-wrap text-destructive">{task.error}</pre>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="parameters" className="overflow-y-auto">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  任务参数
                </CardTitle>
                <CardDescription>创建任务时传递的参数</CardDescription>
              </CardHeader>
              <CardContent>
                {task.params && Object.keys(task.params).length > 0 ? (
                  <div className="space-y-3">
                    {Object.entries(task.params).map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between p-3 bg-muted rounded-lg">
                        <div>
                          <div className="font-medium">{key}</div>
                          <div className="text-sm text-muted-foreground">{typeof value} 类型</div>
                        </div>
                        <div className="flex items-center gap-2">
                          <code className="bg-background px-2 py-1 rounded text-sm">{JSON.stringify(value)}</code>
                          <Button variant="ghost" size="sm" onClick={() => copyToClipboard(JSON.stringify(value))}>
                            <Copy className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <Settings className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>未提供参数</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="result" className="overflow-y-auto">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5" />
                  任务结果
                </CardTitle>
                <CardDescription>任务完成后返回的输出</CardDescription>
              </CardHeader>
              <CardContent>
                {task.result ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">结果类型: {typeof task.result}</span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => copyToClipboard(JSON.stringify(task.result, null, 2))}
                      >
                        <Copy className="h-4 w-4 mr-2" />
                        复制
                      </Button>
                    </div>
                    <div className="bg-muted p-4 rounded-lg">
                      <pre className="text-sm whitespace-pre-wrap overflow-x-auto">
                        {JSON.stringify(task.result, null, 2)}
                      </pre>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>无结果可用</p>
                    <p className="text-sm">{task.status === "COMPLETED" ? "任务已完成但未返回结果" : "任务尚未完成"}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="logs" className="overflow-y-auto">
            <Card className="h-full">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="h-5 w-5" />
                    任务日志
                  </CardTitle>
                  <Button variant="outline" size="sm" onClick={fetchLogs} disabled={loading}>
                    {loading ? (
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <RefreshCw className="h-4 w-4 mr-2" />
                    )}
                    刷新
                  </Button>
                </div>
                <CardDescription>任务执行的实时日志</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <ScrollArea className="h-96 w-full">
                  {logs.length > 0 ? (
                    <div className="p-4 space-y-1">
                      {logs.map((log, index) => (
                        <div
                          key={index}
                          className="text-sm font-mono bg-muted/50 p-2 rounded border-l-2 border-primary/20"
                        >
                          {log}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-full text-muted-foreground">
                      <div className="text-center">
                        <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p>无日志可用</p>
                        <p className="text-sm">任务运行时日志将显示在这里</p>
                      </div>
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
