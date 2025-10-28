import { cn } from "@/lib/utils"

interface ProgressBarProps {
  value: number
  max?: number
  className?: string
  showLabel?: boolean
  size?: "sm" | "md" | "lg"
  variant?: "default" | "success" | "warning" | "error"
}

export function ProgressBar({
  value,
  max = 100,
  className,
  showLabel = false,
  size = "md",
  variant = "default",
}: ProgressBarProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)

  const sizeClasses = {
    sm: "h-1",
    md: "h-2",
    lg: "h-3",
  }

  const variantClasses = {
    default: "bg-primary",
    success: "bg-green-500",
    warning: "bg-yellow-500",
    error: "bg-red-500",
  }

  return (
    <div className={cn("w-full bg-muted rounded-full overflow-hidden", sizeClasses[size], className)}>
      <div
        className={cn("h-full rounded-full transition-all duration-500 ease-out", variantClasses[variant])}
        style={{ width: `${percentage}%` }}
      />
      {showLabel && <div className="text-xs text-muted-foreground mt-1 text-center">{percentage.toFixed(1)}%</div>}
    </div>
  )
}
