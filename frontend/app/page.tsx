"use client"

import { useState } from "react"
import { TaskDashboard } from "@/components/task-dashboard"
import { WorkflowManager } from "@/components/workflow-manager"
import { SchedulerManager } from "@/components/scheduler-manager"
import { TaskMonitor } from "@/components/task-monitor"
import { PanCloudManager } from "@/components/pancloud-manager"
import { MovieManager } from "@/components/movie-manager"
import { SystemConfigManager } from "@/components/system-config-manager"
import { LayoutDashboard, Workflow, Calendar, Activity, Cloud, Film, Settings } from "lucide-react"
import { ThemeToggle } from "@/components/theme-toggle"
import { Sidebar } from "@/components/sidebar"

type ActiveTab = "dashboard" | "workflows" | "scheduler" | "monitoring" | "panclouds" | "movies" | "settings"

export default function Home() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("movies")

  const tabs = [
    { id: "movies" as const, label: "影视管理", icon: Film },

    { id: "dashboard" as const, label: "任务面板", icon: LayoutDashboard },
    { id: "workflows" as const, label: "工作流", icon: Workflow },
    { id: "scheduler" as const, label: "调度器", icon: Calendar },
    { id: "monitoring" as const, label: "实时监控", icon: Activity },
    { id: "panclouds" as const, label: "网盘配置", icon: Cloud },
    { id: "settings" as const, label: "系统配置", icon: Settings },
  ]

  const renderContent = () => {
    switch (activeTab) {
      case "dashboard":
        return <TaskDashboard />
      case "workflows":
        return <WorkflowManager />
      case "scheduler":
        return <SchedulerManager />
      case "monitoring":
        return <TaskMonitor />
      case "panclouds":
        return <PanCloudManager />
      case "movies":
        return <MovieManager />
      case "settings":
        return <SystemConfigManager />
      default:
        return <TaskDashboard />
    }
  }

  return (
    <div className="min-h-screen bg-background flex overflow-hidden">
      <Sidebar tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden" >
        <div className="border-b bg-card">
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold">影视资源管理系统</h1>
                <p className="text-sm text-muted-foreground">自动化影视收集和网盘转存平台</p>
              </div>
              <ThemeToggle />
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-auto">{renderContent()}</div>
      </div>
    </div>
  )
}
