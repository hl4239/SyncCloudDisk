"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { TaskAPI } from "@/lib/api"
import type { Task } from "@/types/api"
import { Plus, Search, RefreshCw, Clock, CheckCircle, XCircle, AlertCircle, Pause } from "lucide-react"
import { TaskCreateModal } from "./task-create-modal"
import { TaskDetailsModal } from "./task-details-modal"
import { TaskControls } from "./task-controls"
import { formatTime } from "@/lib/time-utils"
import { LoadingSpinner } from "./ui/loading-spinner"
import { ProgressBar } from "./ui/progress-bar"
import { StatusIndicator } from "./ui/status-indicator"

const statusIcons = {
  PENDING: <Clock className="h-4 w-4" />,
  RUNNING: <RefreshCw className="h-4 w-4 animate-spin" />,
  COMPLETED: <CheckCircle className="h-4 w-4" />,
  FAILED: <XCircle className="h-4 w-4" />,
  CANCELLED: <Pause className="h-4 w-4" />,
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

export function TaskDashboard() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const fetchTasks = async () => {
    try {
      setRefreshing(true)
      const fetchedTasks = await TaskAPI.listTasks()
      setTasks(fetchedTasks)
    } catch (error) {
      console.error("Failed to fetch tasks:", error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchTasks()
  }, [])

  // Auto-refresh every 5 seconds for running tasks
  useEffect(() => {
    const interval = setInterval(() => {
      const hasRunningTasks = tasks.some((task) => task.status === "RUNNING")
      if (hasRunningTasks) {
        fetchTasks()
      }
    }, 5000)

    return () => clearInterval(interval)
  }, [tasks])

  const handleTaskCreated = () => {
    setShowCreateModal(false)
    fetchTasks()
  }

  const filteredTasks = tasks.filter((task) => {
    const matchesSearch =
      task.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      task.id.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = statusFilter === "all" || task.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const getTaskStats = () => {
    const stats = {
      total: tasks.length,
      running: tasks.filter((t) => t.status === "RUNNING").length,
      completed: tasks.filter((t) => t.status === "COMPLETED").length,
      failed: tasks.filter((t) => t.status === "FAILED").length,
    }
    return stats
  }

  const stats = getTaskStats()

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex flex-col items-center gap-4">
          <LoadingSpinner size="lg" />
          <p className="text-muted-foreground">加载任务数据中...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-balance">任务管理</h1>
          <p className="text-muted-foreground text-pretty">监控和管理您的后台任务</p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchTasks}
            disabled={refreshing}
            className="hover:bg-accent hover:text-accent-foreground transition-all duration-200 hover:scale-105 active:scale-95 bg-transparent"
          >
            {refreshing ? <LoadingSpinner size="sm" className="mr-2" /> : <RefreshCw className="h-4 w-4 mr-2" />}
            刷新
          </Button>
          <Button
            onClick={() => setShowCreateModal(true)}
            className="hover:bg-primary/90 transition-all duration-200 hover:scale-105 active:scale-95 shadow-md hover:shadow-lg"
          >
            <Plus className="h-4 w-4 mr-2" />
            创建任务
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="hover:shadow-lg transition-all duration-300 hover:-translate-y-1 border-l-4 border-l-muted">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总任务数</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold transition-all duration-300">{stats.total}</div>
          </CardContent>
        </Card>
        <Card className="hover:shadow-lg transition-all duration-300 hover:-translate-y-1 border-l-4 border-l-blue-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">运行中</CardTitle>
            <RefreshCw className="h-4 w-4 text-blue-600 animate-spin" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600 transition-all duration-300">{stats.running}</div>
          </CardContent>
        </Card>
        <Card className="hover:shadow-lg transition-all duration-300 hover:-translate-y-1 border-l-4 border-l-green-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">已完成</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600 transition-all duration-300">{stats.completed}</div>
          </CardContent>
        </Card>
        <Card className="hover:shadow-lg transition-all duration-300 hover:-translate-y-1 border-l-4 border-l-red-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">失败</CardTitle>
            <XCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600 transition-all duration-300">{stats.failed}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="transition-all duration-300 hover:shadow-md">
        <CardHeader>
          <CardTitle>筛选器</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                <Input
                  placeholder="按任务名称或ID搜索..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 hover:border-accent-foreground/20 focus:border-primary transition-all duration-200 focus:ring-2 focus:ring-primary/20"
                />
              </div>
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-48 hover:border-accent-foreground/20 transition-all duration-200 focus:ring-2 focus:ring-primary/20">
                <SelectValue placeholder="按状态筛选" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">所有状态</SelectItem>
                <SelectItem value="PENDING">等待中</SelectItem>
                <SelectItem value="RUNNING">运行中</SelectItem>
                <SelectItem value="COMPLETED">已完成</SelectItem>
                <SelectItem value="FAILED">失败</SelectItem>
                <SelectItem value="CANCELLED">已取消</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Tasks List */}
      <Card className="transition-all duration-300 hover:shadow-md">
        <CardHeader>
          <CardTitle>任务列表</CardTitle>
          <CardDescription>找到 {filteredTasks.length} 个任务</CardDescription>
        </CardHeader>
        <CardContent>
          {filteredTasks.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>未找到任务</p>
              <p className="text-sm">
                {tasks.length === 0 ? "创建您的第一个任务开始使用" : "尝试调整搜索条件或筛选器"}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredTasks.map((task) => (
                <div
                  key={task.id}
                  className="group flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 hover:border-accent-foreground/20 transition-all duration-300 cursor-pointer hover:shadow-md hover:-translate-y-0.5"
                >
                  <div className="flex items-center gap-4 flex-1">
                    <div className="flex items-center gap-3">
                      <StatusIndicator status={task.status} size="sm" />
                      <Badge className={statusColors[task.status]}>{statusLabels[task.status]}</Badge>
                    </div>
                    <div className="flex-1">
                      <h3 className="font-medium group-hover:text-primary transition-colors duration-200">
                        {task.name}
                      </h3>
                      <p className="text-sm text-muted-foreground">ID: {task.id}</p>
                    </div>
                    {task.status === "RUNNING" && task.progress !== undefined && (
                      <div className="flex items-center gap-3 min-w-40">
                        <ProgressBar
                          value={task.progress}
                          size="sm"
                          className="flex-1"
                          variant={task.progress > 80 ? "success" : "default"}
                        />
                        <span className="text-sm text-muted-foreground font-mono">{task.progress.toFixed(1)}%</span>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right text-sm text-muted-foreground">
                      <p>创建时间: {formatTime(task.created_at)}</p>
                      {task.finished_at && <p>完成时间: {formatTime(task.finished_at)}</p>}
                    </div>
                    <TaskControls
                      task={task}
                      onTaskUpdated={fetchTasks}
                      onViewDetails={() => setSelectedTask(task)}
                      compact
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modals */}
      <TaskCreateModal open={showCreateModal} onOpenChange={setShowCreateModal} onTaskCreated={handleTaskCreated} />

      {selectedTask && (
        <TaskDetailsModal
          task={selectedTask}
          open={!!selectedTask}
          onOpenChange={(open) => !open && setSelectedTask(null)}
          onTaskUpdated={fetchTasks}
        />
      )}
    </div>
  )
}
