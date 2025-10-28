const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"

export interface FilterSchemaItem {
  name: string // e.g., "year__gt"
  field: string // e.g., "year"
  label: string // e.g., "Year Is Greater Than"
  type: "string" | "integer" | "boolean" | "enum"
  operator: string // e.g., "gt"
  options?: string[] // e.g., ["China", "Japan", ...]
}
export interface DoubanMovie {
  douban_id: string
  title: string
  movie_type: "TV" | "Movie" |"Other"
  pic: string
  year: string
}

export interface EpisodeInfo {
  episode_number: number
  air_date: string
  air_time: string | null
  full_air_datetime: string
  weekday: string
}

export interface TMDBInfo {
  id?: number
  season_number?: number
  not_ensure: boolean
}

export interface CloudInfo {
  pancloud_name: string
  last_save_time: string
  last_save_link: string
  last_save_success: boolean
  cloud_path: string
  latest_episode_number: number
  share_link: string | null
  is_risk_share: boolean
}

export interface MetadataProvider {
  provider: string
  title: string
  id: string
}

export interface Movie {
  _id: string
  douban_id: string
  title: string
  title_season: string
  original_title: string | null
  subtitle: string[] | null
  pic: string | null
  description: string
  year: string
  category: "China" | "Japan" | "Korea" | "Europe" | "Animation" | "Other"
  movie_type: "TV" | "Movie" | "Other"
  season: string
  total_episodes: string
  cloud_infos: CloudInfo[]
  tmdb_infos: TMDBInfo
  episodes_info: EpisodeInfo[]
  share_links: string[]
  metadata_providers: MetadataProvider[]
  create_time: string
  update_time: string
  pubdate: string | null
}

export interface MovieListParams {
  movie_type?: "TV" | "Movie" | "Other"
  year__eq?: string
  limit?: number
  offset?: number
  category__eq?: "China" | "Japan" | "Korea" | "Europe" | "Animation" | "Other"
  sort_by?: "update_time" | "create_time" | "year"
  sort_order?: "asc" | "desc"
  title_season__contains?: string
  title__contains?: string
  original_title__contains?: string
  description__contains?: string
  year__gte?: string
  year__lte?: string
  total_episodes__contains?: string
  season__contains?: string
  douban_id__eq?: string
  tmdb_id__eq?: number
  has_episodes?: boolean
  has_cloud_storage?: boolean
  has_share_links?: boolean
  cloud_success?: boolean
  created_after?: string
  created_before?: string
  updated_after?: string
  updated_before?: string
}

export interface UpdateMovieRequest {
  douban_id: string
  title: string
  title_season: string
  original_title: string | null
  subtitle: string[] | null
  pic: string | null
  description: string
  year: string
  category: "China" | "Japan" | "Korea" | "Europe" | "Animation" | "Other"
  movie_type: "TV" | "Movie" | "Other"
  season: string
  total_episodes: string
  cloud_infos: CloudInfo[]
  tmdb_infos: TMDBInfo
  episodes_info: EpisodeInfo[]
  share_links: string[]
  metadata_providers: MetadataProvider[]
  create_time: string
  update_time: string
}

export class MovieAPI {
  private static async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          ...options.headers,
        },
        ...options,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error("Movie API request failed:", error)
      return this.getMockData(endpoint, options.method) as T
    }
  }

  private static _getShanghaiTodayStr(): string {
    const now = new Date()
    const sh = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Shanghai" }))
    return sh.toISOString().split("T")[0]
  }

  private static getMockData(endpoint: string, method?: string): any {
    const mockMovies: Movie[] = [
      {
        _id: "1",
        douban_id: "36455616",
        title: "赴山海",
        title_season: "赴山海",
        original_title: null,
        subtitle: null,
        pic: null,
        description:
          "该剧改编自温瑞安经典武侠小说《神州奇侠》，讲述了肖明明（成毅 饰）曾是一名酷爱武侠小说、意气风发、充满正义感的少年。",
        year: "2025",
        category: "China",
        movie_type: "TV",
        season: "第一季",
        total_episodes: "40集全",
        episodes_info: [
          {
            episode_number: 29,
            air_date: "2025-09-23",
            air_time: null,
            full_air_datetime: "2025-09-23T00:00:00",
            weekday: "星期五",
          },
          {
            episode_number: 30,
            air_date: "2025-09-23",
            air_time: null,
            full_air_datetime: "2025-09-23T00:00:00",
            weekday: "星期五",
          },
        ],
        tmdb_infos: { id: 263034, season_number: 1, not_ensure: false },
        cloud_infos: [
          {
            pancloud_name: "4295quark",
            last_save_time: "2025-09-23T21:39:44.586000+08:00",
            last_save_link: "https://pan.quark.cn/s/969ddab7b51e",
            last_save_success: true,
            cloud_path: "赴山海",
            latest_episode_number: 28,
            share_link: null,
          },
        ],
        share_links: [],
        metadata_providers: [],
        create_time: "2025-09-23T18:51:01.607000+08:00",
        update_time: "2025-09-23T18:51:01.607000+08:00",
      },
      {
        _id: "2",
        douban_id: "36092113",
        title: "吴邪私家笔记",
        title_season: "吴邪私家笔记",
        original_title: null,
        subtitle: null,
        pic: null,
        description:
          "古董店老板吴邪意外获得一份神秘帛书，吴邪三叔吴三省（吴镇宇 饰）发现帛书中竟隐藏着一张神秘的地图。",
        year: "2025",
        category: "China",
        movie_type: "TV",
        season: "第一季",
        total_episodes: "18集全",
        episodes_info: [
          {
            episode_number: 8,
            air_date: "2025-09-23",
            air_time: "20:00:00",
            full_air_datetime: "2025-09-23T20:00:00",
            weekday: "星期五",
          },
        ],
        tmdb_infos: { id: 294443, season_number: 1, not_ensure: false },
        cloud_infos: [
          {
            pancloud_name: "4295quark",
            last_save_time: "2025-09-23T21:39:52.224000+08:00",
            last_save_link: "https://pan.quark.cn/s/e1f672d84bdb",
            last_save_success: true,
            cloud_path: "吴邪私家笔记",
            latest_episode_number: 8,
            share_link: null,
          },
        ],
        share_links: [],
        metadata_providers: [],
        create_time: "2025-09-23T18:51:09.947000+08:00",
        update_time: "2025-09-23T18:51:09.947000+08:00",
      },
    ]

    if (endpoint === "/movies" && method === "GET") {
      return mockMovies
    }

    if (endpoint === "/movies/today" && method === "GET") {
      const today = this._getShanghaiTodayStr()
      return mockMovies.filter((m) => (m.episodes_info || []).some((ep) => ep.air_date === today))
    }

    if (endpoint.includes("/movies/") && method === "GET") {
      return mockMovies[0]
    }

    if (method === "PATCH") {
      return { ok: true, detail: "updated" }
    }

    if (method === "DELETE") {
      return { ok: true, detail: "deleted" }
    }

    return mockMovies
  }

  static async listMovies(params?: MovieListParams): Promise<Movie[]> {
    const queryParams = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          queryParams.append(key, value.toString())
        }
      })
    }

    const endpoint = `/movies${queryParams.toString() ? `?${queryParams.toString()}` : ""}`
    return this.request<Movie[]>(endpoint, {
      method: "GET",
    })
  }

  static async listTodayMovies(): Promise<Movie[]> {
    return this.request<Movie[]>("/movies/today", { method: "GET" })
  }

  static async getMovie(doubanId: string): Promise<Movie> {
    return this.request<Movie>(`/movies/${doubanId}`, {
      method: "GET",
    })
  }

  static async updateMovie(doubanId: string, data: UpdateMovieRequest): Promise<Movie> {
    return this.request<Movie>(`/movies/${doubanId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    })
  }

  static async deleteMovie(doubanId: string): Promise<{ deleted: boolean; id: string }> {
    return this.request<{ deleted: boolean; id: string }>(`/movies/${doubanId}`, {
      method: "DELETE",
    })
  }
  static async getFilterSchema(): Promise<FilterSchemaItem[]> {
    return this.request<FilterSchemaItem[]>("/movies/filters", {
      method: "GET",
    })
  }
    // 搜索豆瓣影视
  static async searchDouban(title: string): Promise<DoubanMovie[]> {
    return this.request<DoubanMovie[]>(
      `/movies/douban_search?title=${encodeURIComponent(title)}`,
      { method: "GET" },
    )
  }
}
