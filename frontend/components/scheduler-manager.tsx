"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { TaskAPI } from "@/lib/api"
import type { ScheduledJob } from "@/types/api"
import {
  Plus,
  Search,
  RefreshCw,
  Calendar,
  Clock,
  Play,
  Pause,
  Trash2,
  Edit,
  Power,
  PowerOff,
  Activity,
  Timer,
} from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { CreateJobModal } from "./create-job-modal"
import { EditJobModal } from "./edit-job-modal"
import { JobDetailsModal } from "./job-details-modal"
import { formatTime } from "@/lib/time-utils"

type SchedulerStatus = {
  running: boolean
  jobs_count: number
  heap_size: number
  bg_task_active: boolean
  next_run: {
    job_id: string
    task_name: string
    next_run_at: string
    next_run_at_local: string
  } | null
  upcoming: Array<{
    job_id: string
    task_name: string
    next_run_at: string
    next_run_at_local: string
  }>
  tz: string
}

export function SchedulerManager() {
  const [jobs, setJobs] = useState<ScheduledJob[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedJob, setSelectedJob] = useState<ScheduledJob | null>(null)
  const [editingJob, setEditingJob] = useState<ScheduledJob | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [schedulerRunning, setSchedulerRunning] = useState(true)
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null)
  const [loadingStatus, setLoadingStatus] = useState(false)
  const { toast } = useToast()

  const fetchSchedulerStatus = async () => {
    try {
      setLoadingStatus(true)
      const status = await TaskAPI.getSchedulerStatus()
      setSchedulerStatus(status)
      setSchedulerRunning(status.running)
    } catch (error) {
      console.error("Failed to fetch scheduler status:", error)
      toast({
        title: "错误",
        description: "获取调度器状态失败",
        variant: "destructive",
      })
    } finally {
      setLoadingStatus(false)
    }
  }

  const fetchJobs = async () => {
    try {
      setRefreshing(true)
      const fetchedJobs = await TaskAPI.listJobs()
      setJobs(fetchedJobs)
    } catch (error) {
      console.error("Failed to fetch jobs:", error)
      toast({
        title: "错误",
        description: "加载计划任务失败",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchJobs()
    fetchSchedulerStatus()
  }, [])

  const filteredJobs = jobs.filter(
    (job) =>
      job.task_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      job.job_id.toLowerCase().includes(searchTerm.toLowerCase()),
  )

  const handleJobCreated = () => {
    setShowCreateModal(false)
    fetchJobs()
  }

  const handleJobUpdated = () => {
    setEditingJob(null)
    fetchJobs()
  }

  const handleToggleJob = async (job: ScheduledJob) => {
    try {
      if (job.enabled) {
        await TaskAPI.disableJob(job.job_id)
        toast({
          title: "成功",
          description: "任务已禁用",
        })
      } else {
        await TaskAPI.enableJob(job.job_id)
        toast({
          title: "成功",
          description: "任务已启用",
        })
      }
      fetchJobs()
    } catch (error) {
      console.error("Failed to toggle job:", error)
      toast({
        title: "错误",
        description: "切换任务状态失败",
        variant: "destructive",
      })
    }
  }

  const handleRunJob = async (job: ScheduledJob) => {
    try {
      await TaskAPI.runJob(job.job_id)
      toast({
        title: "成功",
        description: "任务执行请求已发送",
      })
    } catch (error) {
      console.error("Failed to run job:", error)
      toast({
        title: "错误",
        description: "运行任务失败",
        variant: "destructive",
      })
    }
  }

  const handleDeleteJob = async (job: ScheduledJob) => {
    if (!confirm(`确定要删除任务 "${job.task_name}" 吗？`)) {
      return
    }

    try {
      await TaskAPI.deleteJob(job.job_id)
      toast({
        title: "成功",
        description: "任务已删除",
      })
      fetchJobs()
    } catch (error) {
      console.error("Failed to delete job:", error)
      toast({
        title: "错误",
        description: "删除任务失败",
        variant: "destructive",
      })
    }
  }

  const handleToggleScheduler = async () => {
    try {
      if (schedulerRunning) {
        await TaskAPI.stopScheduler()
        setSchedulerRunning(false)
        toast({
          title: "成功",
          description: "调度器已停止",
        })
      } else {
        await TaskAPI.startScheduler()
        setSchedulerRunning(true)
        toast({
          title: "成功",
          description: "调度器已启动",
        })
      }
      fetchSchedulerStatus()
    } catch (error) {
      console.error("Failed to toggle scheduler:", error)
      toast({
        title: "错误",
        description: "切换调度器状态失败",
        variant: "destructive",
      })
    }
  }

  const getJobStats = () => {
    const stats = {
      total: jobs.length,
      enabled: jobs.filter((j) => j.enabled).length,
      disabled: jobs.filter((j) => !j.enabled).length,
      recent: jobs.filter((j) => j.last_run_at && new Date(j.last_run_at).getTime() > Date.now() - 24 * 60 * 60 * 1000)
        .length,
    }
    return stats
  }

  const stats = getJobStats()

  const formatNextRun = (nextRun: string | undefined) => {
    if (!nextRun) return "未计划"
    const date = new Date(nextRun)
    const now = new Date()
    const diff = date.getTime() - now.getTime()

    if (diff < 0) return "已过期"
    if (diff < 60 * 1000) return "不到1分钟"
    if (diff < 60 * 60 * 1000) return `${Math.floor(diff / (60 * 1000))}分钟后`
    if (diff < 24 * 60 * 60 * 1000) return `${Math.floor(diff / (60 * 60 * 1000))}小时后`
    return `${Math.floor(diff / (24 * 60 * 60 * 1000))}天后`
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <RefreshCw className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-balance">调度管理</h1>
          <p className="text-muted-foreground text-pretty">管理计划任务和自动化工作流</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Badge variant={schedulerRunning ? "default" : "secondary"} className="flex items-center gap-1">
              {schedulerRunning ? <Power className="h-3 w-3" /> : <PowerOff className="h-3 w-3" />}
              {schedulerRunning ? "运行中" : "已停止"}
            </Badge>
            <Button variant="outline" size="sm" onClick={handleToggleScheduler}>
              {schedulerRunning ? <PowerOff className="h-4 w-4 mr-2" /> : <Power className="h-4 w-4 mr-2" />}
              {schedulerRunning ? "停止" : "启动"}
            </Button>
          </div>
          <Button variant="outline" size="sm" onClick={fetchSchedulerStatus} disabled={loadingStatus}>
            <Activity className={`h-4 w-4 mr-2 ${loadingStatus ? "animate-spin" : ""}`} />
            状态
          </Button>
          <Button variant="outline" size="sm" onClick={fetchJobs} disabled={refreshing}>
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
            刷新
          </Button>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            创建任务
          </Button>
        </div>
      </div>

      {schedulerStatus && (
        <Card className="bg-gradient-to-r from-primary/5 to-secondary/5 border-primary/20">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-3 text-primary">
              <div className="p-2 bg-primary/10 rounded-lg">
                <Activity className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-xl font-bold">调度器状态</h3>
                <p className="text-sm text-muted-foreground font-normal">实时调度器运行状态</p>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <div className="flex items-center gap-3 p-3 bg-background/50 rounded-lg border">
                <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-full">
                  <Calendar className="h-4 w-4 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">任务总数</p>
                  <p className="text-lg font-semibold">{schedulerStatus.jobs_count}</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 bg-background/50 rounded-lg border">
                <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-full">
                  <Activity className="h-4 w-4 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">堆大小</p>
                  <p className="text-lg font-semibold">{schedulerStatus.heap_size}</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 bg-background/50 rounded-lg border">
                <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-full">
                  <Timer className="h-4 w-4 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">后台任务</p>
                  <p className="text-lg font-semibold">{schedulerStatus.bg_task_active ? "活跃" : "非活跃"}</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 bg-background/50 rounded-lg border">
                <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-full">
                  <Clock className="h-4 w-4 text-orange-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">时区</p>
                  <p className="text-lg font-semibold">{schedulerStatus.tz}</p>
                </div>
              </div>
            </div>

            {schedulerStatus.next_run && (
              <div className="mb-4">
                <h4 className="font-medium mb-2 flex items-center gap-2">
                  <Timer className="h-4 w-4" />
                  下次运行任务
                </h4>
                <div className="p-3 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 rounded-lg border border-blue-200/50 dark:border-blue-800/50">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-blue-900 dark:text-blue-100">
                        {schedulerStatus.next_run.task_name}
                      </p>
                      <p className="text-sm text-blue-700 dark:text-blue-300">ID: {schedulerStatus.next_run.job_id}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-blue-600 dark:text-blue-400">本地时间</p>
                      <p className="font-medium text-blue-900 dark:text-blue-100">
                        {new Date(schedulerStatus.next_run.next_run_at_local).toLocaleString("zh-CN")}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {schedulerStatus.upcoming.length > 0 && (
              <div>
                <h4 className="font-medium mb-2 flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  即将运行的任务
                </h4>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {schedulerStatus.upcoming.map((job, index) => (
                    <div
                      key={job.job_id}
                      className="flex items-center justify-between p-2 bg-background/50 rounded border"
                    >
                      <div className="flex-1">
                        <p className="font-medium text-sm">{job.task_name}</p>
                        <p className="text-xs text-muted-foreground">ID: {job.job_id}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground">
                          {new Date(job.next_run_at_local).toLocaleString("zh-CN")}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总任务数</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">已启用</CardTitle>
            <Play className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats.enabled}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">已禁用</CardTitle>
            <Pause className="h-4 w-4 text-gray-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-600">{stats.disabled}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">近期运行</CardTitle>
            <Clock className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats.recent}</div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <Card>
        <CardHeader>
          <CardTitle>搜索任务</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
            <Input
              placeholder="按名称或ID搜索任务..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Jobs List */}
      <Card>
        <CardHeader>
          <CardTitle>计划任务</CardTitle>
          <CardDescription>找到 {filteredJobs.length} 个任务</CardDescription>
        </CardHeader>
        <CardContent>
          {filteredJobs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Calendar className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>未找到计划任务</p>
              <p className="text-sm">{jobs.length === 0 ? "创建您的第一个计划任务开始使用" : "尝试调整搜索条件"}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredJobs.map((job) => (
                <div
                  key={job.job_id}
                  className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-4 flex-1">
                    <div className="flex items-center gap-2">
                      <Switch checked={job.enabled} onCheckedChange={() => handleToggleJob(job)} />
                      <Badge variant={job.enabled ? "default" : "secondary"}>{job.enabled ? "已启用" : "已禁用"}</Badge>
                    </div>
                    <div className="flex-1">
                      <h3 className="font-medium">{job.task_name}</h3>
                      <div className="text-sm text-muted-foreground space-y-1">
                        <p>
                          计划: {job.cron} ({job.tz})
                        </p>
                        <p>下次运行: {formatNextRun(job.next_run_at)}</p>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right text-sm text-muted-foreground">
                      <p>
                        创建时间: {/* Use centralized time formatting */}
                        {formatTime(job.created_at)}
                      </p>
                      {job.last_run_at && (
                        <p>
                          上次运行: {/* Use centralized time formatting */}
                          {formatTime(job.last_run_at)}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="outline" size="sm" onClick={() => setSelectedJob(job)}>
                        查看
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => handleRunJob(job)} disabled={!job.enabled}>
                        <Play className="h-4 w-4" />
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => setEditingJob(job)}>
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => handleDeleteJob(job)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modals */}
      <CreateJobModal open={showCreateModal} onOpenChange={setShowCreateModal} onJobCreated={handleJobCreated} />

      {editingJob && (
        <EditJobModal
          job={editingJob}
          open={!!editingJob}
          onOpenChange={(open) => !open && setEditingJob(null)}
          onJobUpdated={handleJobUpdated}
        />
      )}

      {selectedJob && (
        <JobDetailsModal
          job={selectedJob}
          open={!!selectedJob}
          onOpenChange={(open) => !open && setSelectedJob(null)}
          onJobUpdated={fetchJobs}
        />
      )}
    </div>
  )
}
