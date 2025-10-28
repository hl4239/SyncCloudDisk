import { cn } from "@/lib/utils"
import { Clock, CheckCircle, XCircle, Pause, RefreshCw } from "lucide-react"

interface StatusIndicatorProps {
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED"
  size?: "sm" | "md" | "lg"
  showLabel?: boolean
  className?: string
}

const statusConfig = {
  PENDING: {
    icon: Clock,
    color: "text-yellow-600",
    bgColor: "bg-yellow-100 dark:bg-yellow-900/20",
    label: "等待中",
  },
  RUNNING: {
    icon: RefreshCw,
    color: "text-blue-600",
    bgColor: "bg-blue-100 dark:bg-blue-900/20",
    label: "运行中",
    animate: true,
  },
  COMPLETED: {
    icon: CheckCircle,
    color: "text-green-600",
    bgColor: "bg-green-100 dark:bg-green-900/20",
    label: "已完成",
  },
  FAILED: {
    icon: XCircle,
    color: "text-red-600",
    bgColor: "bg-red-100 dark:bg-red-900/20",
    label: "失败",
  },
  CANCELLED: {
    icon: Pause,
    color: "text-gray-600",
    bgColor: "bg-gray-100 dark:bg-gray-900/20",
    label: "已取消",
  },
}

export function StatusIndicator({ status, size = "md", showLabel = false, className }: StatusIndicatorProps) {
  const config = statusConfig[status]
  const Icon = config.icon

  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-5 w-5",
    lg: "h-6 w-6",
  }

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className={cn("rounded-full p-1.5 transition-colors", config.bgColor)}>
        <Icon className={cn(sizeClasses[size], config.color, config.animate && "animate-spin")} />
      </div>
      {showLabel && <span className={cn("font-medium", config.color)}>{config.label}</span>}
    </div>
  )
}
