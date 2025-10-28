"use client"
import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { RefreshCw, Play, Pause, Clock, CheckCircle, XCircle, AlertCircle } from "lucide-react"
import { TaskAPI } from "@/lib/api"
import type { Task } from "@/types/api"
import { formatTime } from "@/lib/time-utils"
import { LoadingSpinner } from "./ui/loading-spinner"
import { ProgressBar } from "./ui/progress-bar"

interface TaskMonitorProps {
  taskId?: string
}

export function TaskMonitor({ taskId }: TaskMonitorProps) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [isAutoRefresh, setIsAutoRefresh] = useState(true)
  const [loading, setLoading] = useState(false)

  const fetchTasks = async () => {
    try {
      setLoading(true)
      const response = await TaskAPI.getTasks()
      setTasks(response.tasks || [])

      // If a specific task is selected, update its details
      if (selectedTask) {
        const updatedTask = response.tasks?.find((t) => t.id === selectedTask.id)
        if (updatedTask) {
          setSelectedTask(updatedTask)
        }
      }
    } catch (error) {
      console.error("获取任务失败:", error)
    } finally {
      setLoading(false)
    }
  }

  const fetchTaskDetails = async (id: string) => {
    try {
      const task = await TaskAPI.getTask(id)
      setSelectedTask(task)
    } catch (error) {
      console.error("获取任务详情失败:", error)
    }
  }

  useEffect(() => {
    fetchTasks()

    if (taskId) {
      fetchTaskDetails(taskId)
    }
  }, [taskId])

  useEffect(() => {
    let interval: NodeJS.Timeout

    if (isAutoRefresh) {
      interval = setInterval(fetchTasks, 3000) // 每3秒刷新一次
    }

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [isAutoRefresh])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "running":
        return <Play className="h-4 w-4 text-blue-500" />
      case "completed":
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case "failed":
        return <XCircle className="h-4 w-4 text-red-500" />
      case "pending":
        return <Clock className="h-4 w-4 text-yellow-500" />
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusBadge = (status: string) => {
    const variants = {
      running: "default",
      completed: "secondary",
      failed: "destructive",
      pending: "outline",
    } as const

    const labels = {
      running: "运行中",
      completed: "已完成",
      failed: "失败",
      pending: "等待中",
    }

    return (
      <Badge variant={variants[status as keyof typeof variants] || "outline"}>
        {labels[status as keyof typeof labels] || status}
      </Badge>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
      {/* 任务列表 */}
      <Card className="flex flex-col transition-all duration-300 hover:shadow-lg">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div>
            <CardTitle className="text-xl">实时任务监控</CardTitle>
            <CardDescription>监控所有任务的执行状态和进度</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsAutoRefresh(!isAutoRefresh)}
              className={`transition-all duration-200 hover:scale-105 active:scale-95 ${
                isAutoRefresh
                  ? "bg-green-50 border-green-200 text-green-700 hover:bg-green-100 dark:bg-green-900/20 dark:border-green-800 dark:text-green-300"
                  : ""
              }`}
            >
              {isAutoRefresh ? <Pause className="h-4 w-4 mr-1" /> : <Play className="h-4 w-4 mr-1" />}
              {isAutoRefresh ? "暂停刷新" : "开始刷新"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchTasks}
              disabled={loading}
              className="transition-all duration-200 hover:scale-105 active:scale-95 bg-transparent"
            >
              {loading ? <LoadingSpinner size="sm" className="mr-1" /> : <RefreshCw className="h-4 w-4 mr-1" />}
              刷新
            </Button>
          </div>
        </CardHeader>
        <CardContent className="flex-1 p-0">
          <ScrollArea className="h-[500px] px-6">
            <div className="space-y-3">
              {tasks.map((task) => (
                <div
                  key={task.id}
                  className={`group p-4 rounded-lg border cursor-pointer transition-all duration-300 hover:bg-accent hover:border-accent-foreground/20 hover:shadow-md hover:-translate-y-0.5 ${
                    selectedTask?.id === task.id
                      ? "bg-accent border-accent-foreground/20 shadow-md ring-2 ring-primary/20"
                      : "hover:shadow-sm"
                  }`}
                  onClick={() => setSelectedTask(task)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(task.status)}
                      <span className="font-medium group-hover:text-primary transition-colors duration-200">
                        {task.workflow_name}
                      </span>
                    </div>
                    {getStatusBadge(task.status)}
                  </div>
                  <div className="text-sm text-muted-foreground space-y-1">
                    <div>任务ID: {task.id}</div>
                    <div>创建时间: {formatTime(task.created_at)}</div>
                    {task.progress !== undefined && (
                      <div className="flex items-center gap-2 mt-2">
                        <span>进度:</span>
                        <ProgressBar
                          value={task.progress}
                          size="sm"
                          className="flex-1"
                          variant={
                            task.progress > 80
                              ? "success"
                              : task.progress > 50
                                ? "default"
                                : task.progress > 20
                                  ? "warning"
                                  : "error"
                          }
                        />
                        <span className="text-xs font-mono min-w-12 text-right">{task.progress.toFixed(1)}%</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {tasks.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  <AlertCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>暂无任务数据</p>
                </div>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* 任务详情 */}
      <Card className="flex flex-col transition-all duration-300 hover:shadow-lg">
        <CardHeader>
          <CardTitle className="text-xl">任务详情</CardTitle>
          <CardDescription>
            {selectedTask ? `查看任务 ${selectedTask.id} 的详细信息` : "选择一个任务查看详情"}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex-1">
          {selectedTask ? (
            <div className="space-y-6 animate-in fade-in-50 duration-300">
              {/* 基本信息 */}
              <div className="space-y-3">
                <h3 className="font-semibold text-lg">基本信息</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="p-3 rounded-lg bg-muted/50 transition-colors hover:bg-muted">
                    <span className="text-muted-foreground">工作流:</span>
                    <div className="font-medium">{selectedTask.workflow_name}</div>
                  </div>
                  <div className="p-3 rounded-lg bg-muted/50 transition-colors hover:bg-muted">
                    <span className="text-muted-foreground">状态:</span>
                    <div className="mt-1">{getStatusBadge(selectedTask.status)}</div>
                  </div>
                  <div className="p-3 rounded-lg bg-muted/50 transition-colors hover:bg-muted">
                    <span className="text-muted-foreground">创建时间:</span>
                    <div className="font-medium">{formatTime(selectedTask.created_at)}</div>
                  </div>
                  {selectedTask.completed_at && (
                    <div className="p-3 rounded-lg bg-muted/50 transition-colors hover:bg-muted">
                      <span className="text-muted-foreground">完成时间:</span>
                      <div className="font-medium">{formatTime(selectedTask.completed_at)}</div>
                    </div>
                  )}
                </div>
              </div>

              <Separator />

              {/* 执行结果 */}
              {selectedTask.result && (
                <div className="space-y-3">
                  <h3 className="font-semibold text-lg">执行结果</h3>
                  <ScrollArea className="h-32 w-full rounded-md border p-4 bg-muted/20">
                    <pre className="text-sm whitespace-pre-wrap">
                      {typeof selectedTask.result === "string"
                        ? selectedTask.result
                        : JSON.stringify(selectedTask.result, null, 2)}
                    </pre>
                  </ScrollArea>
                </div>
              )}

              {selectedTask.result && <Separator />}

              {/* 执行日志 */}
              <div className="space-y-3">
                <h3 className="font-semibold text-lg">执行日志</h3>
                <ScrollArea className="h-48 w-full rounded-md border p-4 bg-muted/20">
                  {selectedTask.logs && selectedTask.logs.length > 0 ? (
                    <div className="space-y-2">
                      {selectedTask.logs.map((log, index) => (
                        <div key={index} className="text-sm p-2 rounded bg-background/50 border-l-2 border-primary/20">
                          <span className="text-muted-foreground text-xs">[{formatTime(log.timestamp)}]</span>
                          <span
                            className={`ml-2 ${
                              log.level === "error"
                                ? "text-red-600"
                                : log.level === "warning"
                                  ? "text-yellow-600"
                                  : log.level === "info"
                                    ? "text-blue-600"
                                    : "text-foreground"
                            }`}
                          >
                            {log.message}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-muted-foreground text-sm text-center py-8">
                      <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      暂无日志信息
                    </div>
                  )}
                </ScrollArea>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <div className="text-center">
                <AlertCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>请从左侧选择一个任务查看详情</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
