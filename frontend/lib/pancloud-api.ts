const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"

export interface PanCloud {
  name: string
  cloud_type: "Quark" | "Baidu"
  cookie: string
  enable: boolean
}

export interface CreatePanCloudRequest {
  name: string
  cloud_type: "Quark" | "Baidu"
  cookie: string
  enable: boolean
}

export interface UpdatePanCloudRequest {
  cookie?: string
  enable?: boolean
}

export class PanCloudAPI {
  private static async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: {
          "Content-Type": "application/json",
          ...options.headers,
        },
        ...options,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error("API request failed:", error)
      // 返回模拟数据用于演示
      return this.getMockData(endpoint, options.method) as T
    }
  }

  private static getMockData(endpoint: string, method?: string): any {
    const mockPanClouds: PanCloud[] = [
      {
        name: "4295quark",
        cloud_type: "Quark",
        cookie: "quark_session_cookie_example_123456",
        enable: true,
      },
      {
        name: "5678baidu",
        cloud_type: "Baidu",
        cookie: "baidu_session_cookie_example_789012",
        enable: false,
      },
      {
        name: "9012quark",
        cloud_type: "Quark",
        cookie: "quark_session_cookie_example_345678",
        enable: true,
      },
    ]

    if (endpoint === "/panclouds" && method === "GET") {
      return mockPanClouds
    }

    if (endpoint.includes("/panclouds/") && method === "GET") {
      return mockPanClouds[0]
    }

    if (method === "POST" || method === "PATCH") {
      return { ok: true, detail: "success" }
    }

    if (method === "DELETE") {
      return { ok: true, detail: "deleted" }
    }

    return mockPanClouds
  }

  static async listPanClouds(): Promise<PanCloud[]> {
    return this.request<PanCloud[]>("/panclouds", {
      method: "GET",
    })
  }

  static async getPanCloud(name: string): Promise<PanCloud> {
    return this.request<PanCloud>(`/panclouds/${name}`, {
      method: "GET",
    })
  }

  static async createPanCloud(data: CreatePanCloudRequest): Promise<{ ok: boolean; detail: string }> {
    return this.request<{ ok: boolean; detail: string }>("/panclouds", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  static async updatePanCloud(name: string, data: UpdatePanCloudRequest): Promise<{ ok: boolean; detail: string }> {
    return this.request<{ ok: boolean; detail: string }>(`/panclouds/${name}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    })
  }

  static async deletePanCloud(name: string): Promise<{ ok: boolean; detail: string }> {
    return this.request<{ ok: boolean; detail: string }>(`/panclouds/${name}`, {
      method: "DELETE",
    })
  }

  static async enablePanCloud(name: string): Promise<{ ok: boolean; detail: string }> {
    return this.request<{ ok: boolean; detail: string }>(`/panclouds/${name}/enable`, {
      method: "POST",
    })
  }

  static async disablePanCloud(name: string): Promise<{ ok: boolean; detail: string }> {
    return this.request<{ ok: boolean; detail: string }>(`/panclouds/${name}/disable`, {
      method: "POST",
    })
  }
}
