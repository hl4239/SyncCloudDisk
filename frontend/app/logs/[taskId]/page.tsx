import { LogViewer } from "@/components/log-viewer"
import { Button } from "@/components/ui/button"
import { ArrowLeft } from "lucide-react"
import Link from "next/link"

interface LogsPageProps {
  params: {
    taskId: string
  }
}

export default function LogsPage({ params }: LogsPageProps) {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/">
          <Button variant="outline" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Task Logs</h1>
          <p className="text-muted-foreground">Viewing logs for task: {params.taskId}</p>
        </div>
      </div>

      <LogViewer taskId={params.taskId} />
    </div>
  )
}
