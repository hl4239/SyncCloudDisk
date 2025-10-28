"use client"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { Workflow } from "@/types/api"
import { WorkflowIcon, Settings, Code, FileText, Copy, Info } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

interface WorkflowDetailsModalProps {
  workflow: Workflow
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function WorkflowDetailsModal({ workflow, open, onOpenChange }: WorkflowDetailsModalProps) {
  const { toast } = useToast()

  const copyToClipboard = (text: string, description: string) => {
    navigator.clipboard.writeText(text)
    toast({
      title: "Copied",
      description,
    })
  }

  const getParameterTypeColor = (type: string) => {
    switch (type) {
      case "string":
        return "bg-blue-100 text-blue-800 border-blue-200"
      case "integer":
      case "number":
        return "bg-green-100 text-green-800 border-green-200"
      case "boolean":
        return "bg-purple-100 text-purple-800 border-purple-200"
      case "object":
        return "bg-orange-100 text-orange-800 border-orange-200"
      case "array":
        return "bg-pink-100 text-pink-800 border-pink-200"
      default:
        return "bg-gray-100 text-gray-800 border-gray-200"
    }
  }

  const renderParameterSchema = () => {
    const { properties, required = [] } = workflow.params_schema

    if (!properties || Object.keys(properties).length === 0) {
      return (
        <div className="text-center py-8 text-muted-foreground">
          <Settings className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>No parameters defined</p>
        </div>
      )
    }

    return (
      <div className="space-y-4">
        {Object.entries(properties).map(([key, schema]) => {
          const isRequired = required.includes(key)
          return (
            <Card key={key} className={isRequired ? "border-primary/50" : ""}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base flex items-center gap-2">
                    {key}
                    {isRequired && (
                      <Badge variant="destructive" className="text-xs">
                        Required
                      </Badge>
                    )}
                  </CardTitle>
                  <Badge className={getParameterTypeColor(schema.type)}>{schema.type}</Badge>
                </div>
                {schema.title && schema.title !== key && <CardDescription>{schema.title}</CardDescription>}
              </CardHeader>
              <CardContent className="pt-0 space-y-2">
                {schema.description && (
                  <div className="text-sm text-muted-foreground">
                    <Info className="h-4 w-4 inline mr-1" />
                    {schema.description}
                  </div>
                )}
                {schema.default !== undefined && (
                  <div className="text-sm">
                    <span className="font-medium">Default:</span>{" "}
                    <code className="bg-muted px-1 py-0.5 rounded text-xs">{JSON.stringify(schema.default)}</code>
                  </div>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <WorkflowIcon className="h-6 w-6 text-primary" />
              <div>
                <DialogTitle className="text-xl">
                  {workflow.name.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                </DialogTitle>
                <DialogDescription>
                  {workflow.params_model_module} • {workflow.params_model_name}
                </DialogDescription>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="secondary">{workflow.name}</Badge>
            </div>
          </div>
        </DialogHeader>

        <Tabs defaultValue="overview" className="flex-1 overflow-hidden">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="parameters">Parameters</TabsTrigger>
            <TabsTrigger value="example">Example</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4 overflow-y-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Workflow Name</CardTitle>
                  <WorkflowIcon className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-lg font-semibold">{workflow.name}</div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(workflow.name, "Workflow name copied")}
                    className="mt-2 h-8 px-2"
                  >
                    <Copy className="h-3 w-3 mr-1" />
                    Copy
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Model Information</CardTitle>
                  <Code className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="space-y-1 text-sm">
                    <div>
                      <span className="font-medium">Module:</span> {workflow.params_model_module}
                    </div>
                    <div>
                      <span className="font-medium">Model:</span> {workflow.params_model_name}
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Parameters</CardTitle>
                  <Settings className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="space-y-1 text-sm">
                    <div>
                      <span className="font-medium">Total:</span>{" "}
                      {Object.keys(workflow.params_schema.properties || {}).length}
                    </div>
                    <div>
                      <span className="font-medium">Required:</span> {workflow.params_schema.required?.length || 0}
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Schema Type</CardTitle>
                  <FileText className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-lg font-semibold">{workflow.params_schema.type}</div>
                  <div className="text-sm text-muted-foreground">{workflow.params_schema.title}</div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="parameters" className="overflow-y-auto">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  Parameter Schema
                </CardTitle>
                <CardDescription>Detailed parameter definitions for this workflow</CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-96">{renderParameterSchema()}</ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="example" className="overflow-y-auto">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <Code className="h-5 w-5" />
                    Usage Example
                  </CardTitle>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      copyToClipboard(
                        JSON.stringify({ name: workflow.name, params: workflow.params_example }, null, 2),
                        "Example copied to clipboard",
                      )
                    }
                  >
                    <Copy className="h-4 w-4 mr-2" />
                    Copy Example
                  </Button>
                </div>
                <CardDescription>Example task creation payload for this workflow</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <div className="text-sm font-medium mb-2">Task Creation Example:</div>
                    <div className="bg-muted p-4 rounded-lg">
                      <pre className="text-sm overflow-x-auto">
                        {JSON.stringify(
                          {
                            name: workflow.name,
                            params: workflow.params_example,
                          },
                          null,
                          2,
                        )}
                      </pre>
                    </div>
                  </div>

                  {workflow.params_example && Object.keys(workflow.params_example).length > 0 && (
                    <div>
                      <div className="text-sm font-medium mb-2">Parameters Only:</div>
                      <div className="bg-muted p-4 rounded-lg">
                        <pre className="text-sm overflow-x-auto">
                          {JSON.stringify(workflow.params_example, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
