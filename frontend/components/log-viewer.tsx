"use client"

import { useState, useEffect, useRef } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { ScrollArea } from "@/components/ui/scroll-area"
import { TaskAPI } from "@/lib/api"
import { RefreshCw, Download, Search, Filter, Copy, Trash2 } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

interface LogViewerProps {
  taskId: string
  autoRefresh?: boolean
  maxLines?: number
}

export function LogViewer({ taskId, autoRefresh = true, maxLines = 100000 }: LogViewerProps) {
  const [logs, setLogs] = useState<string[]>([])
  const [filteredLogs, setFilteredLogs] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState("")
  const [tailLines, setTailLines] = useState<number | undefined>(undefined)
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(autoRefresh)
  const [refreshInterval, setRefreshInterval] = useState(3000)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const { toast } = useToast()

  const fetchLogs = async (showLoading = true) => {
    try {
      if (showLoading) setLoading(true)
      const taskLogs = await TaskAPI.getTaskLogs(taskId, tailLines)
      setLogs(taskLogs)
    } catch (error) {
      console.error("Failed to fetch logs:", error)
      toast({
        title: "Error",
        description: "Failed to fetch task logs",
        variant: "destructive",
      })
    } finally {
      if (showLoading) setLoading(false)
    }
  }

  // Filter logs based on search term
  useEffect(() => {
    if (!searchTerm.trim()) {
      setFilteredLogs(logs)
    } else {
      const filtered = logs.filter((log) => log.toLowerCase().includes(searchTerm.toLowerCase()))
      setFilteredLogs(filtered)
    }
  }, [logs, searchTerm])

  // Auto-refresh functionality
  useEffect(() => {
    if (!autoRefreshEnabled) return

    const interval = setInterval(() => {
      fetchLogs(false) // Don't show loading spinner for auto-refresh
    }, refreshInterval)

    return () => clearInterval(interval)
  }, [autoRefreshEnabled, refreshInterval, taskId, tailLines])

  // Initial load
  useEffect(() => {
    fetchLogs()
  }, [taskId, tailLines])

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector("[data-radix-scroll-area-viewport]")
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight
      }
    }
  }, [filteredLogs])

  const handleDownloadLogs = () => {
    const logContent = logs.join("\n")
    const blob = new Blob([logContent], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `task-${taskId}-logs.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    toast({
      title: "Success",
      description: "Logs downloaded successfully",
    })
  }

  const handleCopyLogs = async () => {
    try {
      await navigator.clipboard.writeText(logs.join("\n"))
      toast({
        title: "Success",
        description: "Logs copied to clipboard",
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to copy logs to clipboard",
        variant: "destructive",
      })
    }
  }

  const clearSearch = () => {
    setSearchTerm("")
  }

  const getLogLevelColor = (log: string) => {
    const lowerLog = log.toLowerCase()
    if (lowerLog.includes("error") || lowerLog.includes("exception")) {
      return "border-l-red-500 bg-red-50/50"
    } else if (lowerLog.includes("warning") || lowerLog.includes("warn")) {
      return "border-l-yellow-500 bg-yellow-50/50"
    } else if (lowerLog.includes("info")) {
      return "border-l-blue-500 bg-blue-50/50"
    } else if (lowerLog.includes("debug")) {
      return "border-l-gray-500 bg-gray-50/50"
    }
    return "border-l-primary/20 bg-muted/30"
  }

  const highlightSearchTerm = (text: string) => {
    if (!searchTerm.trim()) return text

    const regex = new RegExp(`(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi")
    return text.replace(regex, '<mark class="bg-yellow-200 px-1 rounded">$1</mark>')
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Task Logs</CardTitle>
            <CardDescription>
              Real-time logs for task {taskId}
              {filteredLogs.length !== logs.length && (
                <span className="ml-2 text-primary">
                  ({filteredLogs.length} of {logs.length} lines shown)
                </span>
              )}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => fetchLogs()} disabled={loading}>
              {loading ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-2" />}
              Refresh
            </Button>
            <Button variant="outline" size="sm" onClick={handleCopyLogs} disabled={logs.length === 0}>
              <Copy className="h-4 w-4 mr-2" />
              Copy
            </Button>
            <Button variant="outline" size="sm" onClick={handleDownloadLogs} disabled={logs.length === 0}>
              <Download className="h-4 w-4 mr-2" />
              Download
            </Button>
          </div>
        </div>

        {/* Controls */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
          {/* Search */}
          <div className="space-y-2">
            <Label>Search Logs</Label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
              <Input
                placeholder="Search in logs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-10"
              />
              {searchTerm && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute right-1 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0"
                  onClick={clearSearch}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              )}
            </div>
          </div>

          {/* Tail Lines */}
          <div className="space-y-2">
            <Label>Tail Lines (Optional)</Label>
            <Input
              type="number"
              placeholder="All lines"
              value={tailLines || ""}
              onChange={(e) => {
                const value = e.target.value
                setTailLines(value ? Number.parseInt(value) : undefined)
              }}
              min="1"
              max="100000"
            />
          </div>

          {/* Auto-refresh */}
          <div className="space-y-2">
            <Label>Auto-refresh</Label>
            <div className="flex items-center space-x-2">
              <Switch checked={autoRefreshEnabled} onCheckedChange={setAutoRefreshEnabled} />
              <span className="text-sm text-muted-foreground">Every {refreshInterval / 1000}s</span>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 p-0">
        <ScrollArea className="h-96 w-full" ref={scrollAreaRef}>
          {filteredLogs.length > 0 ? (
            <div className="p-4 space-y-1">
              {filteredLogs.map((log, index) => (
                <div key={index} className={`text-sm font-mono p-2 rounded border-l-2 ${getLogLevelColor(log)}`}>
                  <div
                    dangerouslySetInnerHTML={{
                      __html: highlightSearchTerm(log),
                    }}
                  />
                </div>
              ))}
            </div>
          ) : logs.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <div className="text-center p-8">
                <Filter className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No logs available</p>
                <p className="text-sm">Logs will appear here as the task runs</p>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <div className="text-center p-8">
                <Search className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No logs match your search</p>
                <p className="text-sm">Try adjusting your search term</p>
                <Button variant="outline" size="sm" onClick={clearSearch} className="mt-2 bg-transparent">
                  Clear Search
                </Button>
              </div>
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
