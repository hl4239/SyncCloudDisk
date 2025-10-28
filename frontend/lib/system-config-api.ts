const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"
// System Configuration API Client
export interface SystemConfig {
  _id: string
  system: string
  version: string
  open_ai_config: {
    default_source_name: string
    sources: AISource[]
  }
  split_title_season_patterns: TitlePattern[]
}

export interface AISource {
  _id: string | null
  name: string
  key: string
  base_url: string
  models: string[]
  extra_body: Record<string, any>
}

export interface TitlePattern {
  _id: string | null
  regular: string
  description: string
}

class SystemConfigAPI {
  private baseUrl = API_BASE

  async getSystemConfig(): Promise<SystemConfig> {
    try {
      const response = await fetch(`${this.baseUrl}/systemconfigs`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const configs = await response.json()
      return configs[0] // API returns array but only has 1 element
    } catch (error) {
      console.warn("Failed to fetch system config, using mock data:", error)
      return this.getMockSystemConfig()
    }
  }

async updateSystemConfig(configId: string, updates: Partial<SystemConfig>): Promise<SystemConfig> {
  try {
    // 过滤掉 _id，避免触发 MongoDB 的 immutable 错误
    const { _id, ...safeUpdates } = updates as any

    const response = await fetch(`${this.baseUrl}/systemconfigs/${configId}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(safeUpdates),
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  } catch (error) {
    console.warn("Failed to update system config, using mock response:", error)
    return { ...this.getMockSystemConfig(), ...updates, _id: configId }
  }
}


  private getMockSystemConfig(): SystemConfig {
    return {
      _id: "68d165a3e2b088a9a4f27fd2",
      system: "影视管理系统",
      version: "2.0",
      open_ai_config: {
        default_source_name: "yuanbao",
        sources: [
          {
            _id: null,
            name: "copilot",
            key: "demo-key-copilot",
            base_url: "http://192.168.31.2:5005/v1",
            models: ["gpt-4", "gpt-3.5-turbo"],
            extra_body: {},
          },
          {
            _id: null,
            name: "yuanbao",
            key: "demo-key-yuanbao",
            base_url: "http://192.168.31.3:8003/v1/",
            models: ["deepseek-v3"],
            extra_body: {
              hy_source: "web",
              hy_user: "03e48e8dacd641ab9772423140d03ab0",
              agent_id: "naQivTmsDa",
              should_remove_conversation: false,
            },
          },
        ],
      },
      split_title_season_patterns: [
        {
          _id: null,
          regular: "^(.*?) (第.+季)$",
          description: '结尾是 "第X季"',
        },
        {
          _id: null,
          regular: "^(.*?) Season (\\d+)$",
          description: "英文季度格式",
        },
      ],
    }
  }
}

export const systemConfigAPI = new SystemConfigAPI()
