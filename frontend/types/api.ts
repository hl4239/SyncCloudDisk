export interface Task {
  id: string
  name: string
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED"
  progress?: number
  created_at: string
  started_at?: string
  finished_at?: string
  params?: Record<string, any>
  result?: {
    message: string
    processed: number
  }
  error?: string | null
  log?: string[]
}

export interface CreateTaskRequest {
  name: string
  params: Record<string, any>
}

export interface Workflow {
  name: string
  params_schema: {
    properties: Record<
      string,
      {
        type: string
        title: string
        default?: any
        description?: string
      }
    >
    required?: string[]
    title: string
    type: string
  }
  params_example: Record<string, any>
  params_model_name: string
  params_model_module: string
}

export interface ScheduledJob {
  job_id: string
  task_name: string
  cron: string
  params: Record<string, any>
  tz: string
  enabled: boolean
  created_at: string
  last_run_at?: string | null
  next_run_at?: string
}

export interface CreateJobRequest {
  task_name: string
  cron: string
  params: Record<string, any>
  tz: string
}

export interface UpdateJobRequest {
  cron?: string
  params?: Record<string, any>
}

export interface ApiResponse<T> {
  data?: T
  error?: string
}
