"use client"

import { useState, useEffect } from "react"
import { TaskAPI } from "@/lib/api"
import type { Task } from "@/types/task"
import { TaskControls } from "@/components/task-controls"
import { TaskDetailsModal } from "@/components/task-details-modal"
import { LogViewer } from "@/components/log-viewer"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft, RefreshCw, Clock, CheckCircle, XCircle, AlertCircle, Pause } from "lucide-react"
import Link from "next/link"
import { formatTime } from "@/lib/time-utils"

interface TaskPageProps {
  params: {
    taskId: string
  }
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

export default function TaskPage({ params }: TaskPageProps) {
  const [task, setTask] = useState<Task | null>(null)
  const [loading, setLoading] = useState(true)
  const [showDetailsModal, setShowDetailsModal] = useState(false)

  const fetchTask = async () => {
    try {
      const fetchedTask = await TaskAPI.getTask(params.taskId)
      setTask(fetchedTask)
    } catch (error) {
      console.error("Failed to fetch task:", error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTask()
  }, [params.taskId])

  // Auto-refresh for running tasks
  useEffect(() => {
    if (!task || task.status !== "RUNNING") return

    const interval = setInterval(() => {
      fetchTask()
    }, 3000)

    return () => clearInterval(interval)
  }, [task]) // Updated to use the entire task object

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <RefreshCw className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!task) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center py-12">
          <AlertCircle className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
          <h1 className="text-2xl font-bold mb-2">任务未找到</h1>
          <p className="text-muted-foreground mb-4">无法找到ID为 {params.taskId} 的任务。</p>
          <Link href="/">
            <Button>
              <ArrowLeft className="h-4 w-4 mr-2" />
              返回面板
            </Button>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/">
          <Button variant="outline" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回面板
          </Button>
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            {statusIcons[task.status]}
            <h1 className="text-2xl font-bold">{task.name}</h1>
            <Badge className={statusColors[task.status]}>{statusLabels[task.status]}</Badge>
          </div>
          <p className="text-muted-foreground">任务ID: {task.id}</p>
        </div>
      </div>

      {/* Task Overview */}
      <Card>
        <CardHeader>
          <CardTitle>任务概览</CardTitle>
          <CardDescription>当前状态和进度信息</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <div className="text-sm text-muted-foreground">状态</div>
              <div className="text-lg font-semibold">{statusLabels[task.status]}</div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">进度</div>
              <div className="text-lg font-semibold">{task.progress.toFixed(1)}%</div>
              {task.status === "RUNNING" && (
                <div className="w-full bg-muted rounded-full h-2 mt-1">
                  <div
                    className="bg-primary h-2 rounded-full transition-all duration-300"
                    style={{ width: `${task.progress}%` }}
                  />
                </div>
              )}
            </div>
            <div>
              <div className="text-sm text-muted-foreground">创建时间</div>
              <div className="text-lg font-semibold">
                {/* Use centralized time formatting */}
                {formatTime(task.created_at)}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Task Controls */}
        <div className="lg:col-span-1">
          <TaskControls task={task} onTaskUpdated={fetchTask} onViewDetails={() => setShowDetailsModal(true)} />
        </div>

        {/* Log Viewer */}
        <div className="lg:col-span-2">
          <LogViewer taskId={task.id} />
        </div>
      </div>

      {/* Task Details Modal */}
      {showDetailsModal && (
        <TaskDetailsModal
          task={task}
          open={showDetailsModal}
          onOpenChange={setShowDetailsModal}
          onTaskUpdated={fetchTask}
        />
      )}
    </div>
  )
}
