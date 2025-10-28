export interface Task {
  id: string
  name: string
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED"
  progress: number
  created_at: string
  started_at?: string
  finished_at?: string
  params?: Record<string, any>
  result?: any
  error?: string
}

export interface TaskCreateRequest {
  name: string
  params?: Record<string, any>
}

export interface TaskListParams {
  status?: string
  name?: string
  limit?: number
  offset?: number
}
