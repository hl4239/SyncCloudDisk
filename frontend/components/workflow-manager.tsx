"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { TaskAPI } from "@/lib/api"
import type { Workflow } from "@/types/api"
import { Search, RefreshCw, WorkflowIcon, Settings, Code, FileText, Copy } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { WorkflowDetailsModal } from "./workflow-details-modal"

export function WorkflowManager() {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const { toast } = useToast()

  const fetchWorkflows = async () => {
    try {
      setRefreshing(true)
      const fetchedWorkflows = await TaskAPI.listWorkflows()
      setWorkflows(fetchedWorkflows)
    } catch (error) {
      console.error("Failed to fetch workflows:", error)
      toast({
        title: "Error",
        description: "Failed to load workflows",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchWorkflows()
  }, [])

  const filteredWorkflows = workflows.filter((workflow) =>
    workflow.name.toLowerCase().includes(searchTerm.toLowerCase()),
  )

  const copyWorkflowExample = (workflow: Workflow) => {
    const example = {
      name: workflow.name,
      params: workflow.params_example,
    }
    navigator.clipboard.writeText(JSON.stringify(example, null, 2))
    toast({
      title: "Copied",
      description: "Workflow example copied to clipboard",
    })
  }

  const getParameterCount = (workflow: Workflow) => {
    return Object.keys(workflow.params_schema.properties || {}).length
  }

  const getRequiredParameterCount = (workflow: Workflow) => {
    return workflow.params_schema.required?.length || 0
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
          <h1 className="text-3xl font-bold text-balance">Workflow Management</h1>
          <p className="text-muted-foreground text-pretty">Browse and manage available workflows for task automation</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchWorkflows} disabled={refreshing}>
          <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Workflows</CardTitle>
            <WorkflowIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{workflows.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Available</CardTitle>
            <Settings className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{filteredWorkflows.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Parameters</CardTitle>
            <Code className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              {workflows.reduce((total, w) => total + getParameterCount(w), 0)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <Card>
        <CardHeader>
          <CardTitle>Search Workflows</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
            <Input
              placeholder="Search workflows by name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Workflows Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredWorkflows.map((workflow) => (
          <Card key={workflow.name} className="hover:shadow-md transition-shadow">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <WorkflowIcon className="h-5 w-5 text-primary" />
                  {workflow.name.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                </CardTitle>
                <Badge variant="secondary">{workflow.params_model_name}</Badge>
              </div>
              <CardDescription className="text-sm">Module: {workflow.params_model_module}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Parameter Info */}
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-1">
                    <Settings className="h-4 w-4 text-muted-foreground" />
                    <span>{getParameterCount(workflow)} params</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Code className="h-4 w-4 text-destructive" />
                    <span>{getRequiredParameterCount(workflow)} required</span>
                  </div>
                </div>
              </div>

              {/* Example Parameters Preview */}
              {workflow.params_example && Object.keys(workflow.params_example).length > 0 && (
                <div className="space-y-2">
                  <div className="text-sm font-medium">Example Parameters:</div>
                  <ScrollArea className="h-20 w-full">
                    <div className="bg-muted p-2 rounded text-xs font-mono">
                      <pre>{JSON.stringify(workflow.params_example, null, 2)}</pre>
                    </div>
                  </ScrollArea>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-2 pt-2">
                <Button variant="outline" size="sm" onClick={() => setSelectedWorkflow(workflow)} className="flex-1">
                  <FileText className="h-4 w-4 mr-2" />
                  View Details
                </Button>
                <Button variant="outline" size="sm" onClick={() => copyWorkflowExample(workflow)}>
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredWorkflows.length === 0 && (
        <Card>
          <CardContent className="text-center py-12">
            <WorkflowIcon className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
            <h3 className="text-lg font-semibold mb-2">No workflows found</h3>
            <p className="text-muted-foreground">
              {workflows.length === 0
                ? "No workflows are currently available in the system"
                : "Try adjusting your search terms"}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Workflow Details Modal */}
      {selectedWorkflow && (
        <WorkflowDetailsModal
          workflow={selectedWorkflow}
          open={!!selectedWorkflow}
          onOpenChange={(open) => !open && setSelectedWorkflow(null)}
        />
      )}
    </div>
  )
}
