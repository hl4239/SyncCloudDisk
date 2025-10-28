"use client"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { toast } from "@/hooks/use-toast"
import {
  MovieAPI,
  type Movie,
  type MovieListParams,
  type UpdateMovieRequest,
  type EpisodeInfo,
  type CloudInfo,
  type MetadataProvider,
  type FilterSchemaItem,
} from "@/lib/movie-api"
import { PanCloudAPI, type PanCloud } from "@/lib/pancloud-api"
import { Film, Calendar, Trash2, Plus, Search } from "lucide-react"

import { TodayMovies } from "./movie-tabs/today-movies"
import { AllMovies } from "./movie-tabs/all-movies"
import { DoubanSearch } from "./movie-tabs/douban-search"
import ListString from "@/components/list-string"

const MOCK_FILTER_SCHEMA: FilterSchemaItem[] = [
  { name: "title", label: "标题", type: "string" },
  {
    name: "category",
    label: "分类",
    type: "enum",
    options: ["China", "Japan", "Korea", "Europe", "Animation", "Other"],
  },
  { name: "movie_type", label: "类型", type: "enum", options: ["TV", "Movie", "Other"] },
  { name: "year", label: "年份", type: "string" },
  { name: "season", label: "季信息", type: "string" },
  { name: "total_episodes", label: "总集数", type: "integer" },
  { name: "has_cloud_info", label: "有网盘信息", type: "boolean" },
  { name: "has_episodes", label: "有剧集信息", type: "boolean" },
]

export function MovieManager() {
  const [movies, setMovies] = useState<Movie[]>([])
  const [todayMovies, setTodayMovies] = useState<Movie[]>([])
  const [panclouds, setPanclouds] = useState<PanCloud[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingToday, setLoadingToday] = useState(true)
  const [editingMovie, setEditingMovie] = useState<Movie | null>(null)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)

  const [filterSchema, setFilterSchema] = useState<FilterSchemaItem[]>(MOCK_FILTER_SCHEMA)
  const [filters, setFilters] = useState<MovieListParams>({ sort_by: "-pubdate" })

  const [selectedMovies, setSelectedMovies] = useState<Set<string>>(new Set())
  const [selectAll, setSelectAll] = useState(false)

  const [formData, setFormData] = useState<UpdateMovieRequest>({
    douban_id: "",
    title: "",
    title_season: "",
    original_title: null,
    subtitle: null,
    pic: null,
    description: "",
    year: "",
    category: "China",
    movie_type: "TV",
    season: "",
    total_episodes: "",
    cloud_infos: [],
    tmdb_infos: { id: 0, season_number: 1, not_ensure: false },
    episodes_info: [],
    share_links: [],
    metadata_providers: [],
    create_time: "",
    update_time: "",
  })

  const [batchTimeSettings, setBatchTimeSettings] = useState({
    airTime: "",
    applyToAll: true,
    selectedEpisodes: [] as number[],
  })
  const [showBatchTimeDialog, setShowBatchTimeDialog] = useState(false)

  const getShanghaiTodayStr = () => {
    const now = new Date()
    const sh = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Shanghai" }))
    return sh.toISOString().split("T")[0]
  }

  const getCloudProgress = (movie: Movie) => {
    if (!movie.cloud_infos || movie.cloud_infos.length === 0) {
      return null
    }

    const totalEpisodes = movie.episodes_info?.length || 0
    if (totalEpisodes === 0) return null

    const cloudInfo = movie.cloud_infos[0]
    const latestEpisode = cloudInfo.latest_episode_number || 0
    const progress = Math.round((latestEpisode / totalEpisodes) * 100)

    return {
      current: latestEpisode,
      total: totalEpisodes,
      progress,
      cloudInfo,
    }
  }

  useEffect(() => {
    loadMovies()
    loadPanclouds()
    loadTodayMovies()
    loadFilterSchema()
  }, [filters])
  const loadFilterSchema = async () => {
    try {
      const schema = await MovieAPI.getFilterSchema()
      setFilterSchema(schema)
    } catch (error) {
      console.log("[v0] Filter schema API failed, using mock data")
      setFilterSchema(MOCK_FILTER_SCHEMA)
      toast({
        title: "筛选器加载失败",
        description: "使用默认筛选选项，部分功能可能受限",
        variant: "destructive",
      })
    }
  }
  const loadMovies = async () => {
    try {
      setLoading(true)
      const data = await MovieAPI.listMovies(filters)
      setMovies(data)
    } catch (error) {
      toast({
        title: "加载失败",
        description: "无法加载影视列表",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const loadTodayMovies = async () => {
    try {
      setLoadingToday(true)
      const data = await MovieAPI.listTodayMovies()
      setTodayMovies(data)
    } catch (error) {
      console.error("Failed to load today's movies:", error)
    } finally {
      setLoadingToday(false)
    }
  }

  const loadPanclouds = async () => {
    try {
      const data = await PanCloudAPI.listPanClouds()
      setPanclouds(data)
    } catch (error) {
      console.error("Failed to load panclouds:", error)
    }
  }

  const handleEdit = async (movie: Movie) => {
    try {
      const fullMovie = await MovieAPI.getMovie(movie.douban_id)
      setEditingMovie(fullMovie)
      setFormData({
        douban_id: fullMovie.douban_id,
        title: fullMovie.title,
        title_season: fullMovie.title_season,
        original_title: fullMovie.original_title,
        subtitle: fullMovie.subtitle,
        pic: fullMovie.pic,
        description: fullMovie.description,
        year: fullMovie.year,
        category: fullMovie.category,
        movie_type: fullMovie.movie_type,
        season: fullMovie.season,
        total_episodes: fullMovie.total_episodes,
        cloud_infos: fullMovie.cloud_infos,
        tmdb_infos: fullMovie.tmdb_infos,
        episodes_info: fullMovie.episodes_info,
        share_links: fullMovie.share_links,
        metadata_providers: fullMovie.metadata_providers,
        create_time: fullMovie.create_time,
        update_time: fullMovie.update_time,
      })
      setIsEditDialogOpen(true)
    } catch (error) {
      toast({
        title: "加载失败",
        description: "无法加载影视详情",
        variant: "destructive",
      })
    }
  }

  const handleSave = async () => {
    if (!editingMovie) return

    try {
      await MovieAPI.updateMovie(editingMovie.douban_id, formData)
      toast({
        title: "保存成功",
        description: "影视信息已更新",
      })
      setIsEditDialogOpen(false)
      loadMovies()
      loadTodayMovies()
    } catch (error) {
      toast({
        title: "保存失败",
        description: "无法更新影视信息",
        variant: "destructive",
      })
    }
  }

  const handleDelete = async (doubanId: string) => {
    try {
      await MovieAPI.deleteMovie(doubanId)
      toast({
        title: "删除成功",
        description: "影视已删除",
      })
      loadMovies()
      loadTodayMovies()
    } catch (error) {
      toast({
        title: "删除失败",
        description: "无法删除影视",
        variant: "destructive",
      })
    }
  }

  const addEpisode = () => {
    const nextEpisodeNumber = formData.episodes_info.length + 1
    const today = new Date().toISOString().split("T")[0]
    const weekdays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]
    const weekday = weekdays[new Date().getDay()]

    setFormData((prev) => ({
      ...prev,
      episodes_info: [
        ...prev.episodes_info,
        {
          episode_number: nextEpisodeNumber,
          air_date: today,
          air_time: null,
          full_air_datetime: `${today}T00:00:00+08:06`,
          weekday: weekday,
        },
      ],
    }))
  }

  const updateEpisode = (index: number, field: keyof EpisodeInfo, value: any) => {
    setFormData((prev) => ({
      ...prev,
      episodes_info: prev.episodes_info.map((ep, i) => {
        if (i === index) {
          const updated = { ...ep, [field]: value }
          if (field === "air_date" || field === "air_time") {
            const date = field === "air_date" ? value : ep.air_date
            const time = field === "air_time" ? value : ep.air_time
            if (date) {
              const dateObj = new Date(date)
              const weekdays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]
              updated.weekday = weekdays[dateObj.getDay()]
              updated.full_air_datetime = `${date}T${time || "00:00:00"}+08:06`
            }
          }
          return updated
        }
        return ep
      }),
    }))
  }

  const removeEpisode = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      episodes_info: prev.episodes_info.filter((_, i) => i !== index),
    }))
  }

  const applyBatchTimeSettings = () => {
    if (!batchTimeSettings.airTime) {
      toast({
        title: "设置不完整",
        description: "请填写播出时间",
        variant: "destructive",
      })
      return
    }

    const weekdays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]

    setFormData((prev) => ({
      ...prev,
      episodes_info: prev.episodes_info.map((episode, index) => {
        if (!batchTimeSettings.applyToAll && !batchTimeSettings.selectedEpisodes.includes(index)) {
          return episode
        }

        const airDate = episode.air_date || new Date().toISOString().split("T")[0]
        const dateObj = new Date(airDate)
        const weekday = weekdays[dateObj.getDay()]
        const fullAirDatetime = `${airDate}T${batchTimeSettings.airTime}:00+08:06`

        return {
          ...episode,
          air_time: batchTimeSettings.airTime,
          weekday: weekday,
          full_air_datetime: fullAirDatetime,
        }
      }),
    }))

    setShowBatchTimeDialog(false)
    const affectedCount = batchTimeSettings.applyToAll
      ? formData.episodes_info.length
      : batchTimeSettings.selectedEpisodes.length

    toast({
      title: "批量设置成功",
      description: `已为 ${affectedCount} 集设置播出时间`,
    })
  }

  const toggleEpisodeSelection = (index: number) => {
    setBatchTimeSettings((prev) => ({
      ...prev,
      selectedEpisodes: prev.selectedEpisodes.includes(index)
        ? prev.selectedEpisodes.filter((i) => i !== index)
        : [...prev.selectedEpisodes, index].sort(),
    }))
  }

  const addCloudInfo = () => {
    setFormData((prev) => ({
      ...prev,
      cloud_infos: [
        ...prev.cloud_infos,
        {
          pancloud_name: "",
          last_save_time: new Date().toISOString(),
          last_save_link: "",
          last_save_success: true,
          cloud_path: "",
          latest_episode_number: 0,
          share_link: null,
          is_risk_share: false,
          save_suffixes: [],
        },
      ],
    }))
  }

  const updateCloudInfo = (index: number, field: keyof CloudInfo, value: any) => {
    setFormData((prev) => ({
      ...prev,
      cloud_infos: prev.cloud_infos.map((cloud, i) => (i === index ? { ...cloud, [field]: value } : cloud)),
    }))
  }

  const removeCloudInfo = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      cloud_infos: prev.cloud_infos.filter((_, i) => i !== index),
    }))
  }

  const addShareLink = () => {
    setFormData((prev) => ({
      ...prev,
      share_links: [...prev.share_links, ""],
    }))
  }

  const updateShareLink = (index: number, value: string) => {
    setFormData((prev) => ({
      ...prev,
      share_links: prev.share_links.map((link, i) => (i === index ? value : link)),
    }))
  }

  const removeShareLink = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      share_links: prev.share_links.filter((_, i) => i !== index),
    }))
  }

  const addMetadataProvider = () => {
    setFormData((prev) => ({
      ...prev,
      metadata_providers: [...prev.metadata_providers, { provider: "", title: "", id: "" }],
    }))
  }

  const updateMetadataProvider = (index: number, field: keyof MetadataProvider, value: string) => {
    setFormData((prev) => ({
      ...prev,
      metadata_providers: prev.metadata_providers.map((provider, i) =>
        i === index ? { ...provider, [field]: value } : provider,
      ),
    }))
  }

  const removeMetadataProvider = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      metadata_providers: prev.metadata_providers.filter((_, i) => i !== index),
    }))
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case "TV":
        return "bg-blue-100 text-blue-800"
      case "Movie":
        return "bg-green-100 text-green-800"
      case "Other":
        return "bg-gray-100 text-gray-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  const getCategoryColor = (category: string) => {
    switch (category) {
      case "China":
        return "bg-red-100 text-red-800"
      case "Japan":
        return "bg-pink-100 text-pink-800"
      case "Korea":
        return "bg-purple-100 text-purple-800"
      case "Europe":
        return "bg-indigo-100 text-indigo-800"
      case "Animation":
        return "bg-yellow-100 text-yellow-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  const todayStr = getShanghaiTodayStr()

  // --- START: SORTING LOGIC FROM VERSION 1 ---
  const currentSortField = filters.sort_by?.replace(/^-/, "")
  const currentSortOrder = filters.sort_by?.startsWith("-") ? "desc" : "asc"

  const handleSortFieldChange = (newField: string) => {
    if (newField === "none") {
      setFilters((prev) => {
        const { sort_by, ...rest } = prev
        return rest
      })
      return
    }
    const newSortBy = currentSortOrder === "desc" ? `-${newField}` : newField
    setFilters((prev) => ({ ...prev, sort_by: newSortBy as any }))
  }

  const handleSortOrderChange = (newOrder: "asc" | "desc") => {
    const field = currentSortField || "update_time"
    const newSortBy = newOrder === "desc" ? `-${field}` : field
    setFilters((prev) => ({ ...prev, sort_by: newSortBy as any }))
  }
  // --- END: SORTING LOGIC FROM VERSION 1 ---

  const handleSelectMovie = (movieId: string, checked: boolean) => {
    const newSelected = new Set(selectedMovies)
    if (checked) {
      newSelected.add(movieId)
    } else {
      newSelected.delete(movieId)
    }
    setSelectedMovies(newSelected)
    setSelectAll(newSelected.size === movies.length && movies.length > 0)
  }

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedMovies(new Set(movies.map((m) => m.douban_id)))
    } else {
      setSelectedMovies(new Set())
    }
    setSelectAll(checked)
  }

  const handleBatchAction = (action: string) => {
    const selectedCount = selectedMovies.size
    if (selectedCount === 0) {
      toast({
        title: "未选择影视",
        description: "请先选择要操作的影视",
        variant: "destructive",
      })
      return
    }

    toast({
      title: `批量操作: ${action}`,
      description: `将对 ${selectedCount} 部影视执行 ${action} 操作`,
    })
  }

  useEffect(() => {
    setSelectedMovies(new Set())
    setSelectAll(false)
  }, [movies])

  return (
    <div className="h-full flex flex-col">
      <div className="flex-shrink-0 px-6 py-4 border-b bg-background">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">影视管理</h2>
            <p className="text-muted-foreground">管理影视元数据和网盘存储信息</p>
          </div>
        </div>

        <Tabs defaultValue="today" className="mt-4">
          <TabsList className="grid w-full grid-cols-3 max-w-lg">
            <TabsTrigger value="today" className="flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              今日追剧
            </TabsTrigger>
            <TabsTrigger value="all" className="flex items-center gap-2">
              <Film className="h-4 w-4" />
              全部影视
            </TabsTrigger>
            <TabsTrigger value="douban" className="flex items-center gap-2">
              <Search className="h-4 w-4" />
              豆瓣搜索
            </TabsTrigger>
          </TabsList>

          <TabsContent value="today" className="mt-6">
            <TodayMovies onEdit={handleEdit} />
          </TabsContent>

          <TabsContent value="all" className="mt-6 flex-1 overflow-hidden">
            <AllMovies onEdit={handleEdit} onDelete={handleDelete} />
          </TabsContent>

          <TabsContent value="douban" className="mt-6 flex-1 overflow-hidden">
            <DoubanSearch />
          </TabsContent>
        </Tabs>
      </div>

      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-hidden">
          <DialogHeader>
            <DialogTitle>编辑影视信息</DialogTitle>
            <DialogDescription>修改影视的详细信息，包括基本信息、剧集、存储和元数据</DialogDescription>
          </DialogHeader>

          <ScrollArea className="max-h-[70vh] pr-4">
            <Tabs defaultValue="basic" className="space-y-4">
              <TabsList className="grid w-full grid-cols-6">
                <TabsTrigger value="basic">基本信息</TabsTrigger>
                <TabsTrigger value="tmdb">TMDB</TabsTrigger>
                <TabsTrigger value="episodes">剧集</TabsTrigger>
                <TabsTrigger value="storage">存储</TabsTrigger>
                <TabsTrigger value="links">分享链接</TabsTrigger>
                <TabsTrigger value="metadata">元数据</TabsTrigger>
              </TabsList>

              <TabsContent value="basic" className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="title">标题</Label>
                    <Input
                      id="title"
                      value={formData.title}
                      onChange={(e) => setFormData((prev) => ({ ...prev, title: e.target.value }))}
                    />
                  </div>
                  <div>
                    <Label htmlFor="title_season">标题（含季）</Label>
                    <Input
                      id="title_season"
                      value={formData.title_season}
                      onChange={(e) => setFormData((prev) => ({ ...prev, title_season: e.target.value }))}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="original_title">原标题</Label>
                    <Input
                      id="original_title"
                      value={formData.original_title || ""}
                      onChange={(e) => setFormData((prev) => ({ ...prev, original_title: e.target.value || null }))}
                    />
                  </div>
                  <div>
                    <Label htmlFor="pic">海报链接</Label>
                    <Input
                      id="pic"
                      value={formData.pic || ""}
                      onChange={(e) => setFormData((prev) => ({ ...prev, pic: e.target.value || null }))}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label htmlFor="year">年份</Label>
                    <Input
                      id="year"
                      value={formData.year}
                      onChange={(e) => setFormData((prev) => ({ ...prev, year: e.target.value }))}
                    />
                  </div>
                  <div>
                    <Label htmlFor="category">分类</Label>
                    <Select
                      value={formData.category}
                      onValueChange={(value) => setFormData((prev) => ({ ...prev, category: value as any }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="China">中国</SelectItem>
                        <SelectItem value="Japan">日本</SelectItem>
                        <SelectItem value="Korea">韩国</SelectItem>
                        <SelectItem value="Europe">欧美</SelectItem>
                        <SelectItem value="Animation">动画</SelectItem>
                        <SelectItem value="Other">其他</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="movie_type">类型</Label>
                    <Select
                      value={formData.movie_type}
                      onValueChange={(value) => setFormData((prev) => ({ ...prev, movie_type: value as any }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="TV">电视剧</SelectItem>
                        <SelectItem value="Movie">电影</SelectItem>
                        <SelectItem value="Other">其他</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="season">季信息</Label>
                    <Input
                      id="season"
                      value={formData.season}
                      onChange={(e) => setFormData((prev) => ({ ...prev, season: e.target.value }))}
                    />
                  </div>
                  <div>
                    <Label htmlFor="total_episodes">总集数</Label>
                    <Input
                      id="total_episodes"
                      value={formData.total_episodes}
                      onChange={(e) => setFormData((prev) => ({ ...prev, total_episodes: e.target.value }))}
                    />
                  </div>
                </div>

                <div>
                  <Label htmlFor="description">简介</Label>
                  <Textarea
                    id="description"
                    value={formData.description}
                    onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
                    rows={4}
                  />
                </div>

                <div>
                  <Label htmlFor="subtitle">别名 (每行一个)</Label>
                  <Textarea
                    id="subtitle"
                    value={(formData.subtitle || []).join("\n")}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        subtitle: e.target.value.split("\n").filter((s) => s.trim()) || null,
                      }))
                    }
                    rows={3}
                  />
                </div>
              </TabsContent>

              <TabsContent value="tmdb" className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="tmdb_id">TMDB ID</Label>
                    <Input
                      id="tmdb_id"
                      type="number"
                      value={formData.tmdb_infos?.id || ""}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          tmdb_infos: { ...prev.tmdb_infos, id: Number.parseInt(e.target.value) || null },
                        }))
                      }
                    />
                  </div>
                  <div>
                    <Label htmlFor="season_number">季号</Label>
                    <Input
                      id="season_number"
                      type="number"
                      value={formData.tmdb_infos?.season_number || ""}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          tmdb_infos: { ...prev.tmdb_infos, season_number: Number.parseInt(e.target.value) || null },
                        }))
                      }
                    />
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="not_ensure"
                    checked={formData.tmdb_infos?.not_ensure}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        tmdb_infos: { ...prev.tmdb_infos, not_ensure: e.target.checked },
                      }))
                    }
                  />
                  <Label htmlFor="not_ensure">未在TMDB中确认匹配</Label>
                </div>
              </TabsContent>

              <TabsContent value="episodes" className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium">剧集信息</h4>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setShowBatchTimeDialog(true)}
                      disabled={formData.episodes_info.length === 0}
                    >
                      <Calendar className="h-4 w-4 mr-2" />
                      批量设置时间
                    </Button>
                    <Button type="button" variant="outline" size="sm" onClick={addEpisode}>
                      <Plus className="h-4 w-4 mr-2" />
                      添加剧集
                    </Button>
                  </div>
                </div>

                <Dialog open={showBatchTimeDialog} onOpenChange={setShowBatchTimeDialog}>
                  <DialogContent className="max-w-lg">
                    <DialogHeader>
                      <DialogTitle>批量设置剧集时间</DialogTitle>
                      <DialogDescription>
                        为选中的剧集统一设置播出时间。日期来自TMDB保持不变，只设置时间。
                      </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4">
                      <div>
                        <Label htmlFor="batch-air-time">播出时间</Label>
                        <Input
                          id="batch-air-time"
                          type="time"
                          value={batchTimeSettings.airTime}
                          onChange={(e) => setBatchTimeSettings((prev) => ({ ...prev, airTime: e.target.value }))}
                        />
                        <p className="text-xs text-muted-foreground mt-1">设置统一的播出时间（如：20:00）</p>
                      </div>

                      <div>
                        <Label>应用范围</Label>
                        <div className="space-y-2 mt-2">
                          <div className="flex items-center space-x-2">
                            <input
                              type="radio"
                              id="apply-all"
                              name="apply-range"
                              checked={batchTimeSettings.applyToAll}
                              onChange={() => setBatchTimeSettings((prev) => ({ ...prev, applyToAll: true }))}
                            />
                            <Label htmlFor="apply-all" className="text-sm">
                              应用到所有剧集
                            </Label>
                          </div>
                          <div className="flex items-center space-x-2">
                            <input
                              type="radio"
                              id="apply-selected"
                              name="apply-range"
                              checked={!batchTimeSettings.applyToAll}
                              onChange={() => setBatchTimeSettings((prev) => ({ ...prev, applyToAll: false }))}
                            />
                            <Label htmlFor="apply-selected" className="text-sm">
                              仅应用到选中剧集
                            </Label>
                          </div>
                        </div>
                      </div>

                      {!batchTimeSettings.applyToAll && (
                        <div>
                          <Label>选择剧集</Label>
                          <div className="max-h-32 overflow-y-auto border rounded p-2 mt-2">
                            {formData.episodes_info.map((episode, index) => (
                              <div key={index} className="flex items-center space-x-2 py-1">
                                <input
                                  type="checkbox"
                                  id={`episode-${index}`}
                                  checked={batchTimeSettings.selectedEpisodes.includes(index)}
                                  onChange={() => toggleEpisodeSelection(index)}
                                />
                                <Label htmlFor={`episode-${index}`} className="text-sm">
                                  第{episode.episode_number}集 ({episode.air_date || "未设置日期"})
                                </Label>
                              </div>
                            ))}
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            已选择 {batchTimeSettings.selectedEpisodes.length} 集
                          </p>
                        </div>
                      )}
                    </div>

                    <div className="flex justify-end gap-2 pt-4">
                      <Button variant="outline" onClick={() => setShowBatchTimeDialog(false)}>
                        取消
                      </Button>
                      <Button onClick={applyBatchTimeSettings}>应用设置</Button>
                    </div>
                  </DialogContent>
                </Dialog>

                <div className="space-y-3 max-h-60 overflow-y-auto">
                  {formData.episodes_info.map((episode, index) => (
                    <div key={index} className="flex items-center gap-2 p-3 border rounded">
                      <div className="flex-1 grid grid-cols-3 gap-2">
                        <Input
                          type="number"
                          placeholder="集数"
                          value={episode.episode_number}
                          onChange={(e) => updateEpisode(index, "episode_number", Number.parseInt(e.target.value) || 1)}
                        />
                        <Input
                          type="date"
                          placeholder="播出日期"
                          value={episode.air_date || ""}
                          onChange={(e) => updateEpisode(index, "air_date", e.target.value || null)}
                        />
                        <Input
                          type="time"
                          placeholder="播出时间"
                          value={episode.air_time || ""}
                          onChange={(e) => updateEpisode(index, "air_time", e.target.value || null)}
                        />
                      </div>
                      <Button type="button" variant="outline" size="sm" onClick={() => removeEpisode(index)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </TabsContent>

              <TabsContent value="storage" className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium">网盘存储</h4>
                  <Button type="button" variant="outline" size="sm" onClick={addCloudInfo}>
                    <Plus className="h-4 w-4 mr-2" />
                    添加存储
                  </Button>
                </div>

                <div className="space-y-3">
                  {formData.cloud_infos.map((cloud, index) => (
                    <div key={index} className="p-3 border rounded space-y-3">
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <Label>网盘名称</Label>
                          <Select
                            value={cloud.pancloud_name || ""}
                            onValueChange={(value) => updateCloudInfo(index, "pancloud_name", value)}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="选择网盘" />
                            </SelectTrigger>
                            <SelectContent>
                              {panclouds.map((pancloud) => (
                                <SelectItem key={pancloud.name} value={pancloud.name}>
                                  {pancloud.name} ({pancloud.cloud_type})
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label>目录名称</Label>
                          <Input
                            placeholder="存储目录名"
                            value={cloud.cloud_path}
                            onChange={(e) => updateCloudInfo(index, "cloud_path", e.target.value)}
                          />
                        </div>
                        <div className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            id={`risk_share_${index}`}
                            checked={!!cloud.is_risk_share}
                            onChange={(e) => updateCloudInfo(index, "is_risk_share", e.target.checked)}
                          />
                          <Label htmlFor={`risk_share_${index}`}>风险链接</Label>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <Label>网盘分享链接</Label>
                          <Input
                            placeholder="网盘分享链接"
                            value={cloud.share_link || ""}
                            onChange={(e) => updateCloudInfo(index, "share_link", e.target.value || null)}
                          />
                        </div>
                        <div>
                          <Label>最后保存链接</Label>
                          <Input
                            placeholder="最后保存的分享链接"
                            value={cloud.last_save_link}
                            onChange={(e) => updateCloudInfo(index, "last_save_link", e.target.value)}
                          />
                        </div>
                      </div>
                      <div>
                        <Label>存储后缀</Label>
                        <ListString items={(cloud as any).save_suffixes} />
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <Label>最新集数</Label>
                          <Input
                            type="number"
                            placeholder="网盘最新集数"
                            value={cloud.latest_episode_number}
                            onChange={(e) =>
                              updateCloudInfo(index, "latest_episode_number", Number.parseInt(e.target.value) || 0)
                            }
                          />
                        </div>
                        <div className="flex items-center space-x-2 pt-6">
                          <input
                            type="checkbox"
                            id={`save_success_${index}`}
                            checked={cloud.last_save_success}
                            onChange={(e) => updateCloudInfo(index, "last_save_success", e.target.checked)}
                          />
                          <Label htmlFor={`save_success_${index}`}>保存成功</Label>
                        </div>
                      </div>
                      <div className="flex justify-end">
                        <Button type="button" variant="outline" size="sm" onClick={() => removeCloudInfo(index)}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </TabsContent>

              <TabsContent value="links" className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium">分享链接</h4>
                  <Button type="button" variant="outline" size="sm" onClick={addShareLink}>
                    <Plus className="h-4 w-4 mr-2" />
                    添加链接
                  </Button>
                </div>

                <div className="space-y-3">
                  {formData.share_links.map((link, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <Input
                        placeholder="分享链接URL"
                        value={link}
                        onChange={(e) => updateShareLink(index, e.target.value)}
                      />
                      <Button type="button" variant="outline" size="sm" onClick={() => removeShareLink(index)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </TabsContent>

              <TabsContent value="metadata" className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium">元数据提供者</h4>
                  <Button type="button" variant="outline" size="sm" onClick={addMetadataProvider}>
                    <Plus className="h-4 w-4 mr-2" />
                    添加提供者
                  </Button>
                </div>

                <div className="space-y-3">
                  {formData.metadata_providers.map((provider, index) => (
                    <div key={index} className="p-3 border rounded space-y-3">
                      <div className="grid grid-cols-3 gap-2">
                        <div>
                          <Label>提供者</Label>
                          <Input
                            placeholder="如：人人视频"
                            value={provider.provider}
                            onChange={(e) => updateMetadataProvider(index, "provider", e.target.value)}
                          />
                        </div>
                        <div>
                          <Label>标题</Label>
                          <Input
                            placeholder="提供者中的标题"
                            value={provider.title}
                            onChange={(e) => updateMetadataProvider(index, "title", e.target.value)}
                          />
                        </div>
                        <div>
                          <Label>ID</Label>
                          <Input
                            placeholder="提供者中的ID"
                            value={provider.id}
                            onChange={(e) => updateMetadataProvider(index, "id", e.target.value)}
                          />
                        </div>
                      </div>
                      <div className="flex justify-end">
                        <Button type="button" variant="outline" size="sm" onClick={() => removeMetadataProvider(index)}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </TabsContent>
            </Tabs>
          </ScrollArea>

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave}>保存更改</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
