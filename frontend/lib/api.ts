import type { Task, CreateTaskRequest, Workflow, ScheduledJob, CreateJobRequest, UpdateJobRequest } from "@/types/api"
import { async } from "rxjs"

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api/v1"

const MOCK_TASKS: Task[] = [
  {
    id: "task-001",
    name: "数据处理任务",
    status: "RUNNING",
    progress: 65.5,
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    started_at: new Date(Date.now() - 1.5 * 60 * 60 * 1000).toISOString(),
    workflow_name: "数据分析工作流",
    params: { input_file: "data.csv", batch_size: 1000 },
  },
  {
    id: "task-002",
    name: "报告生成任务",
    status: "COMPLETED",
    progress: 100,
    created_at: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
    started_at: new Date(Date.now() - 3.5 * 60 * 60 * 1000).toISOString(),
    finished_at: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    workflow_name: "报告生成工作流",
    result: { report_url: "/reports/monthly-2024.pdf", pages: 25 },
  },
  {
    id: "task-003",
    name: "邮件发送任务",
    status: "FAILED",
    progress: 30,
    created_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
    started_at: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
    finished_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    workflow_name: "邮件通知工作流",
    error: "SMTP连接超时: 无法连接到邮件服务器 smtp.example.com:587",
  },
  {
    id: "task-004",
    name: "备份任务",
    status: "PENDING",
    progress: 0,
    created_at: new Date(Date.now() - 10 * 60 * 60 * 1000).toISOString(),
    workflow_name: "数据备份工作流",
  },
]

const MOCK_WORKFLOWS: Workflow[] = [
  {
    id: "workflow-001",
    name: "数据分析工作流",
    description: "处理和分析CSV数据文件",
    created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: "workflow-002",
    name: "报告生成工作流",
    description: "生成月度业务报告",
    created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: "workflow-003",
    name: "邮件通知工作流",
    description: "发送系统通知邮件",
    created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
  },
]

const MOCK_JOBS: ScheduledJob[] = [
  {
    job_id: "job-001",
    task_name: "每日数据备份",
    cron: "0 2 * * *",
    tz: "Asia/Shanghai",
    enabled: true,
    created_at: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    last_run_at: new Date(Date.now() - 22 * 60 * 60 * 1000).toISOString(),
    next_run_at: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
    params: { backup_path: "/backups", retention_days: 30 },
  },
  {
    job_id: "job-002",
    task_name: "周报生成",
    cron: "0 9 * * 1",
    tz: "Asia/Shanghai",
    enabled: false,
    created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    last_run_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    params: { report_type: "weekly", recipients: ["admin@example.com"] },
  },
]

const simulateApiCall = async <T>(data: T, delay = 500)
: Promise<T> =>
{
  await new Promise((resolve) => setTimeout(resolve, delay))

  // Simulate occasional network errors (5% chance)
  if (Math.random() < 0.05) {
    throw new Error("网络连接错误")
  }

  return data;
}
export class TaskAPI {
  // Task Management
  static async createTask(data: CreateTaskRequest): Promise<Task> {
    try {
      const response = await fetch(`${API_BASE}/tasks`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      })

      if (!response.ok) {
        throw new Error(`Failed to create task: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.warn("API not available, using mock data:", error)
      const newTask: Task = {
        id: `task-${Date.now()}`,
        name: data.name,
        status: "PENDING",
        progress: 0,
        created_at: new Date().toISOString(),
        workflow_name: data.workflow_name || "默认工作流",
        params: data.params,
      }
      return simulateApiCall(newTask)
    }
  }

  static async listTasks(): Promise<Task[]> {
    try {
      const response = await fetch(`${API_BASE}/tasks`)

      if (!response.ok) {
        throw new Error(`Failed to fetch tasks: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.warn("API not available, using mock data:", error)
      return simulateApiCall(MOCK_TASKS)
    }
  }

  static async getTask(taskId: string): Promise<Task> {
    try {
      const response = await fetch(`${API_BASE}/tasks/${taskId}`)

      if (!response.ok) {
        throw new Error(`Failed to fetch task: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.warn("API not available, using mock data:", error)
      const task = MOCK_TASKS.find((t) => t.id === taskId)
      if (!task) {
        throw new Error(`Task ${taskId} not found`)
      }
      return simulateApiCall(task)
    }
  }

  static async getTasks(): Promise<{ tasks: Task[] }> {
    try {
      const tasks = await this.listTasks()
      return { tasks }
    } catch (error) {
      console.warn("API not available, using mock data:", error)
      return simulateApiCall({ tasks: MOCK_TASKS })
    }
  }

  static async getTaskLogs(taskId: string, tailLines = 100): Promise<string[]> {
    try {
      const response = await fetch(`${API_BASE}/tasks/${taskId}/log?tail=${tailLines}`)

      if (!response.ok) {
        throw new Error(`Failed to fetch task logs: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.warn("API not available, using mock data:", error)
      const mockLogs = [
        `[${new Date(Date.now() - 5 * 60 * 1000).toISOString()}] 任务开始执行`,
        `[${new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString()}] 正在初始化工作环境...`,
        `[${new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString()}] 开始处理数据文件`,
        `[${new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()}] 已处理 1000 条记录`,
        `[${new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString()}] 已处理 2500 条记录`,
        `[${new Date().toISOString()}] 当前进度: 65.5%`,
      ]
      return simulateApiCall(mockLogs)
    }
  }

  static async cancelTask(taskId: string): Promise<{ cancel_requested: boolean }> {
    try {
      const response = await fetch(`${API_BASE}/tasks/${taskId}`, {
        method: "DELETE",
      })

      if (!response.ok) {
        throw new Error(`Failed to cancel task: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.warn("API not available, using mock data:", error)
      return simulateApiCall({ cancel_requested: true })
    }
  }

  // Workflow Management
  static async listWorkflows(): Promise<Workflow[]> {
    try {
      const response = await fetch(`${API_BASE}/workflows`)

      if (!response.ok) {
        throw new Error(`Failed to fetch workflows: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.warn("API not available, using mock data:", error)
      return simulateApiCall(MOCK_WORKFLOWS)
    }
  }

  // Scheduler Management
  static async listJobs(): Promise<ScheduledJob[]> {
    try {
      const response = await fetch(`${API_BASE}/scheduler/jobs`)

      if (!response.ok) {
        throw new Error(`Failed to fetch jobs: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.warn("API not available, using mock data:", error)
      return simulateApiCall(MOCK_JOBS)
    }
  }

  static async createJob(data: CreateJobRequest): Promise<ScheduledJob> {
    try {
      const response = await fetch(`${API_BASE}/scheduler/jobs`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      })

      if (!response.ok) {
        throw new Error(`Failed to create job: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.warn("API not available, using mock data:", error)
      const newJob: ScheduledJob = {
        job_id: `job-${Date.now()}`,
        task_name: data.task_name,
        cron: data.cron,
        tz: data.tz || "Asia/Shanghai",
        enabled: data.enabled ?? true,
        created_at: new Date().toISOString(),
        params: data.params,
      }
      return simulateApiCall(newJob)
    }
  }

  static async getJob(jobId: string): Promise<ScheduledJob> {
    try {
      const response = await fetch(`${API_BASE}/scheduler/jobs/${jobId}`)

      if (!response.ok) {
        throw new Error(`Failed to fetch job: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.warn("API not available, using mock data:", error)
      const job = MOCK_JOBS.find((j) => j.job_id === jobId)
      if (!job) {
        throw new Error(`Job ${jobId} not found`)
      }
      return simulateApiCall(job)
    }
  }

  static async updateJob(jobId: string, data: UpdateJobRequest): Promise<ScheduledJob> {
    try {
      const response = await fetch(`${API_BASE}/scheduler/jobs/${jobId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      })

      if (!response.ok) {
        throw new Error(`Failed to update job: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.warn("API not available, using mock data:", error)
      const job = MOCK_JOBS.find((j) => j.job_id === jobId)
      if (!job) {
        throw new Error(`Job ${jobId} not found`)
      }
      const updatedJob = { ...job, ...data }
      return simulateApiCall(updatedJob)
    }
  }

  static async deleteJob(jobId: string): Promise<{ ok: boolean; detail: string }> {
    try {
      const response = await fetch(`${API_BASE}/scheduler/jobs/${jobId}`, {
        method: "DELETE",
      })

      if (!response.ok) {
        throw new Error(`Failed to delete job: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.warn("API not available, using mock data:", error)
      return simulateApiCall({ ok: true, detail: "Job deleted successfully" })
    }
  }

  static async enableJob(jobId: string): Promise<{ ok: boolean; detail: string }> {
    try {
      const response = await fetch(`${API_BASE}/scheduler/jobs/${jobId}/enable`, {
        method: "POST",
      })

      if (!response.ok) {
        throw new Error(`Failed to enable job: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.warn("API not available, using mock data:", error)
      return simulateApiCall({ ok: true, detail: "Job enabled successfully" })
    }
  }

  static async disableJob(jobId: string): Promise<{ ok: boolean; detail: string }> {
    try {
      const response = await fetch(`${API_BASE}/scheduler/jobs/${jobId}/disable`, {
        method: "POST",
      })

      if (!response.ok) {
        throw new Error(`Failed to disable job: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.warn("API not available, using mock data:", error)
      return simulateApiCall({ ok: true, detail: "Job disabled successfully" })
    }
  }

  static async runJob(jobId: string): Promise<{ ok: boolean; detail: string }> {
    try {
      const response = await fetch(`${API_BASE}/scheduler/jobs/${jobId}/run`, {
        method: "POST",
      })

      if (!response.ok) {
        throw new Error(`Failed to run job: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.warn("API not available, using mock data:", error)
      return simulateApiCall({ ok: true, detail: "Job execution requested" })
    }
  }

  static async startScheduler(): Promise<{ ok: boolean; detail: string }> {
    try {
      const response = await fetch(`${API_BASE}/scheduler/start`, {
        method: "POST",
      })

      if (!response.ok) {
        throw new Error(`Failed to start scheduler: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.warn("API not available, using mock data:", error)
      return simulateApiCall({ ok: true, detail: "Scheduler started successfully" })
    }
  }

  static async stopScheduler(waitRunning = true): Promise<{ ok: boolean; detail: string }> {
    try {
      const params = new URLSearchParams()
      params.append("wait_running", waitRunning.toString())

      const response = await fetch(`${API_BASE}/scheduler/stop?${params}`, {
        method: "POST",
      })

      if (!response.ok) {
        throw new Error(`Failed to stop scheduler: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.warn("API not available, using mock data:", error)
      return simulateApiCall({ ok: true, detail: "Scheduler stopped successfully" })
    }
  }
  
  static async getSchedulerStatus(): Promise<{
    running: boolean
    jobs_count: number
    heap_size: number
    bg_task_active: boolean
    next_run: {
      job_id: string
      task_name: string
      next_run_at: string
      next_run_at_local: string
    } | null
    upcoming: Array<{
      job_id: string
      task_name: string
      next_run_at: string
      next_run_at_local: string
    }>
    tz: string
  }> {
    try {
      const response = await fetch(`${API_BASE}/scheduler/status`)

      if (!response.ok) {
        throw new Error(`Failed to fetch scheduler status: ${response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.warn("API not available, using mock data:", error)
      const mockStatus = {
        running: true,
        jobs_count: 3,
        heap_size: 3,
        bg_task_active: true,
        next_run: {
          job_id: "6f853106834c42dbb500a627c0aa1bbc",
          task_name: "同步今日可更新影视资源到网盘",
          next_run_at: "2025-09-28T14:30:00Z",
          next_run_at_local: "2025-09-28T22:30:00+08:00",
        },
        upcoming: [
          {
            job_id: "6f853106834c42dbb500a627c0aa1bbc",
            task_name: "同步今日可更新影视资源到网盘",
            next_run_at: "2025-09-28T14:30:00Z",
            next_run_at_local: "2025-09-28T22:30:00+08:00",
          },
          {
            job_id: "90b4c4751ea04215ae16907f8bb420b7",
            task_name: "豆瓣热门影视采集",
            next_run_at: "2025-09-28T15:00:00Z",
            next_run_at_local: "2025-09-28T23:00:00+08:00",
          },
          {
            job_id: "c2e99644883b4e45970ae3659962985d",
            task_name: "获取今日新的影视，从人人视频抓取",
            next_run_at: "2025-09-28T15:00:00Z",
            next_run_at_local: "2025-09-28T23:00:00+08:00",
          },
        ],
        tz: "Asia/Shanghai",
      }
      return simulateApiCall(mockStatus)
    }
  }
}
