"use client"

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import type { ScheduledJob } from "@/types/api"
import { Calendar, Clock, Settings, Copy, Play, Pause } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { formatTime, formatDuration } from "@/lib/time-utils"

interface JobDetailsModalProps {
  job: ScheduledJob
  open: boolean
  onOpenChange: (open: boolean) => void
  onJobUpdated: () => void
}

export function JobDetailsModal({ job, open, onOpenChange }: JobDetailsModalProps) {
  const { toast } = useToast()

  const copyToClipboard = (text: string, description: string) => {
    navigator.clipboard.writeText(text)
    toast({
      title: "已复制",
      description,
    })
  }

  const getNextRunStatus = () => {
    if (!job.next_run_at) return { text: "未计划", color: "text-muted-foreground" }

    const nextRun = new Date(job.next_run_at)
    const now = new Date()
    const diff = nextRun.getTime() - now.getTime()

    if (diff < 0) return { text: "已过期", color: "text-destructive" }
    if (diff < 60 * 1000) return { text: "不到1分钟", color: "text-orange-600" }
    if (diff < 60 * 60 * 1000) return { text: `${Math.floor(diff / (60 * 1000))}分钟后`, color: "text-yellow-600" }
    if (diff < 24 * 60 * 60 * 1000)
      return { text: `${Math.floor(diff / (60 * 60 * 1000))}小时后`, color: "text-blue-600" }
    return { text: `${Math.floor(diff / (24 * 60 * 60 * 1000))}天后`, color: "text-green-600" }
  }

  const nextRunStatus = getNextRunStatus()

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Calendar className="h-6 w-6 text-primary" />
              <div>
                <DialogTitle className="text-xl">{job.task_name}</DialogTitle>
                <DialogDescription>任务ID: {job.job_id}</DialogDescription>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={job.enabled ? "default" : "secondary"}>
                {job.enabled ? (
                  <>
                    <Play className="h-3 w-3 mr-1" />
                    已启用
                  </>
                ) : (
                  <>
                    <Pause className="h-3 w-3 mr-1" />
                    已禁用
                  </>
                )}
              </Badge>
            </div>
          </div>
        </DialogHeader>

        <Tabs defaultValue="overview" className="flex-1 overflow-hidden">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="overview">概览</TabsTrigger>
            <TabsTrigger value="schedule">计划</TabsTrigger>
            <TabsTrigger value="parameters">参数</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4 overflow-y-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">状态</CardTitle>
                  {job.enabled ? (
                    <Play className="h-4 w-4 text-green-600" />
                  ) : (
                    <Pause className="h-4 w-4 text-gray-600" />
                  )}
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{job.enabled ? "已启用" : "已禁用"}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {job.enabled ? "任务将按计划运行" : "任务已暂停，不会运行"}
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">下次运行</CardTitle>
                  <Clock className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className={`text-lg font-semibold ${nextRunStatus.color}`}>{nextRunStatus.text}</div>
                  {job.next_run_at && (
                    <p className="text-xs text-muted-foreground mt-1">
                      {/* Use centralized time formatting */}
                      {formatTime(job.next_run_at)}
                    </p>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">创建时间</CardTitle>
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-sm">
                    {/* Use centralized time formatting */}
                    {formatTime(job.created_at)}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {/* Use centralized duration formatting */}
                    {formatDuration(job.created_at)}前
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">上次运行</CardTitle>
                  <Clock className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  {job.last_run_at ? (
                    <>
                      <div className="text-sm">
                        {/* Use centralized time formatting */}
                        {formatTime(job.last_run_at)}
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        {/* Use centralized duration formatting */}
                        {formatDuration(job.last_run_at)}前
                      </p>
                    </>
                  ) : (
                    <div className="text-sm text-muted-foreground">从未运行</div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="schedule" className="overflow-y-auto">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  计划配置
                </CardTitle>
                <CardDescription>Cron表达式和时区设置</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <div className="text-sm font-medium">Cron表达式</div>
                    <div className="flex items-center gap-2">
                      <code className="bg-muted px-3 py-2 rounded text-sm font-mono flex-1">{job.cron}</code>
                      <Button variant="outline" size="sm" onClick={() => copyToClipboard(job.cron, "Cron表达式已复制")}>
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="text-sm font-medium">时区</div>
                    <div className="flex items-center gap-2">
                      <code className="bg-muted px-3 py-2 rounded text-sm font-mono flex-1">{job.tz}</code>
                      <Button variant="outline" size="sm" onClick={() => copyToClipboard(job.tz, "时区已复制")}>
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-sm font-medium">计划摘要</div>
                  <div className="bg-muted p-3 rounded-lg text-sm">
                    <p>
                      此任务使用Cron表达式 <code>{job.cron}</code> 在 <code>{job.tz}</code> 时区运行。
                    </p>
                    {job.next_run_at && (
                      <p className="mt-2">
                        下次执行: <strong>{formatTime(job.next_run_at)}</strong>
                      </p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="parameters" className="overflow-y-auto">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  任务参数
                </CardTitle>
                <CardDescription>执行任务时传递的参数</CardDescription>
              </CardHeader>
              <CardContent>
                {job.params && Object.keys(job.params).length > 0 ? (
                  <div className="space-y-3">
                    {Object.entries(job.params).map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between p-3 bg-muted rounded-lg">
                        <div>
                          <div className="font-medium">{key}</div>
                          <div className="text-sm text-muted-foreground">{typeof value} 类型</div>
                        </div>
                        <div className="flex items-center gap-2">
                          <code className="bg-background px-2 py-1 rounded text-sm max-w-xs truncate">
                            {JSON.stringify(value)}
                          </code>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => copyToClipboard(JSON.stringify(value), "参数值已复制")}
                          >
                            <Copy className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    ))}

                    <div className="pt-4 border-t">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">完整参数对象</span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => copyToClipboard(JSON.stringify(job.params, null, 2), "所有参数已复制")}
                        >
                          <Copy className="h-4 w-4 mr-2" />
                          复制全部
                        </Button>
                      </div>
                      <div className="bg-background p-3 rounded-lg mt-2">
                        <pre className="text-xs overflow-x-auto">{JSON.stringify(job.params, null, 2)}</pre>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <Settings className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>未配置参数</p>
                    <p className="text-sm">此任务将不带任何参数运行</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
