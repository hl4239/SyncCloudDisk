"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { TaskAPI } from "@/lib/api"
import type { Task } from "@/types/task"
import { MoreVertical, Trash2, RefreshCw, Eye, FileText, Copy, ExternalLink } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import Link from "next/link"

interface TaskControlsProps {
  task: Task
  onTaskUpdated: () => void
  onViewDetails: () => void
  compact?: boolean
}

export function TaskControls({ task, onTaskUpdated, onViewDetails, compact = false }: TaskControlsProps) {
  const [cancelling, setCancelling] = useState(false)
  const [showCancelDialog, setShowCancelDialog] = useState(false)
  const { toast } = useToast()

  const handleCancel = async () => {
    if (task.status !== "RUNNING" && task.status !== "PENDING") {
      toast({
        title: "Cannot Cancel",
        description: "Only running or pending tasks can be cancelled",
        variant: "destructive",
      })
      return
    }

    setCancelling(true)
    try {
      const result = await TaskAPI.cancelTask(task.id)
      if (result.cancel_requested) {
        toast({
          title: "Success",
          description: "Task cancellation requested",
        })
        onTaskUpdated()
      } else {
        toast({
          title: "Warning",
          description: "Task cancellation could not be requested",
          variant: "destructive",
        })
      }
    } catch (error) {
      console.error("Failed to cancel task:", error)
      toast({
        title: "Error",
        description: "Failed to cancel task",
        variant: "destructive",
      })
    } finally {
      setCancelling(false)
      setShowCancelDialog(false)
    }
  }

  const copyTaskId = () => {
    navigator.clipboard.writeText(task.id)
    toast({
      title: "Copied",
      description: "Task ID copied to clipboard",
    })
  }

  const copyTaskDetails = () => {
    const details = {
      id: task.id,
      name: task.name,
      status: task.status,
      progress: task.progress,
      created_at: task.created_at,
      started_at: task.started_at,
      finished_at: task.finished_at,
      params: task.params,
      result: task.result,
      error: task.error,
    }

    navigator.clipboard.writeText(JSON.stringify(details, null, 2))
    toast({
      title: "Copied",
      description: "Task details copied to clipboard",
    })
  }

  const canCancel = task.status === "RUNNING" || task.status === "PENDING"

  if (compact) {
    return (
      <>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem onClick={onViewDetails}>
              <Eye className="h-4 w-4 mr-2" />
              View Details
            </DropdownMenuItem>

            <DropdownMenuItem asChild>
              <Link href={`/logs/${task.id}`}>
                <FileText className="h-4 w-4 mr-2" />
                View Logs
              </Link>
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            <DropdownMenuItem onClick={copyTaskId}>
              <Copy className="h-4 w-4 mr-2" />
              Copy Task ID
            </DropdownMenuItem>

            <DropdownMenuItem onClick={copyTaskDetails}>
              <Copy className="h-4 w-4 mr-2" />
              Copy Details
            </DropdownMenuItem>

            {canCancel && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={() => setShowCancelDialog(true)}
                  className="text-destructive focus:text-destructive"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Cancel Task
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        <AlertDialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Cancel Task</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to cancel this task? This action cannot be undone.
                <br />
                <br />
                <strong>Task:</strong> {task.name}
                <br />
                <strong>ID:</strong> {task.id}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleCancel}
                disabled={cancelling}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {cancelling && <RefreshCw className="h-4 w-4 mr-2 animate-spin" />}
                Cancel Task
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Task Controls</CardTitle>
        <CardDescription>Actions available for this task</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Button variant="outline" onClick={onViewDetails} className="justify-start bg-transparent">
            <Eye className="h-4 w-4 mr-2" />
            View Details
          </Button>

          <Button variant="outline" asChild className="justify-start bg-transparent">
            <Link href={`/logs/${task.id}`}>
              <FileText className="h-4 w-4 mr-2" />
              View Logs
              <ExternalLink className="h-3 w-3 ml-auto" />
            </Link>
          </Button>

          <Button variant="outline" onClick={copyTaskId} className="justify-start bg-transparent">
            <Copy className="h-4 w-4 mr-2" />
            Copy Task ID
          </Button>

          <Button variant="outline" onClick={copyTaskDetails} className="justify-start bg-transparent">
            <Copy className="h-4 w-4 mr-2" />
            Copy Details
          </Button>
        </div>

        {canCancel && (
          <>
            <div className="border-t pt-3">
              <Button
                variant="destructive"
                onClick={() => setShowCancelDialog(true)}
                disabled={cancelling}
                className="w-full justify-start"
              >
                {cancelling ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <Trash2 className="h-4 w-4 mr-2" />}
                Cancel Task
              </Button>
            </div>
          </>
        )}

        <AlertDialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Cancel Task</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to cancel this task? This action cannot be undone.
                <br />
                <br />
                <strong>Task:</strong> {task.name}
                <br />
                <strong>ID:</strong> {task.id}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleCancel}
                disabled={cancelling}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {cancelling && <RefreshCw className="h-4 w-4 mr-2 animate-spin" />}
                Cancel Task
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </CardContent>
    </Card>
  )
}
