"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { Plus, Trash2, Save, RotateCcw, Settings, Bot, FileText, TestTube } from "lucide-react"
import { systemConfigAPI, type SystemConfig, type AISource, type TitlePattern } from "@/lib/system-config-api"
import { useToast } from "@/hooks/use-toast"

export function SystemConfigManager() {
  const [config, setConfig] = useState<SystemConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testString, setTestString] = useState("权力的游戏 第八季")
  const { toast } = useToast()

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      setLoading(true)
      const data = await systemConfigAPI.getSystemConfig()
      setConfig(data)
    } catch (error) {
      toast({
        title: "加载失败",
        description: "无法加载系统配置",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const saveConfig = async () => {
    if (!config) return

    try {
      setSaving(true)
      await systemConfigAPI.updateSystemConfig(config._id, config)
      toast({
        title: "保存成功",
        description: "系统配置已更新",
      })
    } catch (error) {
      toast({
        title: "保存失败",
        description: "无法保存系统配置",
        variant: "destructive",
      })
    } finally {
      setSaving(false)
    }
  }

  const addAISource = () => {
    if (!config) return
    const newSource: AISource = {
      _id: null,
      name: "",
      key: "",
      base_url: "",
      models: [],
      extra_body: {},
    }
    setConfig({
      ...config,
      open_ai_config: {
        ...config.open_ai_config,
        sources: [...config.open_ai_config.sources, newSource],
      },
    })
  }

  const removeAISource = (index: number) => {
    if (!config) return
    const newSources = config.open_ai_config.sources.filter((_, i) => i !== index)
    setConfig({
      ...config,
      open_ai_config: {
        ...config.open_ai_config,
        sources: newSources,
      },
    })
  }

  const updateAISource = (index: number, field: keyof AISource, value: any) => {
    if (!config) return
    const newSources = [...config.open_ai_config.sources]
    newSources[index] = { ...newSources[index], [field]: value }
    setConfig({
      ...config,
      open_ai_config: {
        ...config.open_ai_config,
        sources: newSources,
      },
    })
  }

  const addTitlePattern = () => {
    if (!config) return
    const newPattern: TitlePattern = {
      _id: null,
      regular: "",
      description: "",
    }
    setConfig({
      ...config,
      split_title_season_patterns: [...config.split_title_season_patterns, newPattern],
    })
  }

  const removeTitlePattern = (index: number) => {
    if (!config) return
    const newPatterns = config.split_title_season_patterns.filter((_, i) => i !== index)
    setConfig({
      ...config,
      split_title_season_patterns: newPatterns,
    })
  }

  const updateTitlePattern = (index: number, field: keyof TitlePattern, value: string) => {
    if (!config) return
    const newPatterns = [...config.split_title_season_patterns]
    newPatterns[index] = { ...newPatterns[index], [field]: value }
    setConfig({
      ...config,
      split_title_season_patterns: newPatterns,
    })
  }

  const testRegexPattern = (pattern: string) => {
    try {
      const regex = new RegExp(pattern)
      const match = testString.match(regex)
      return match ? match.slice(1) : null
    } catch (error) {
      return null
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Settings className="h-8 w-8 animate-spin mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground">加载系统配置中...</p>
          </div>
        </div>
      </div>
    )
  }

  if (!config) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center">
          <p className="text-destructive">无法加载系统配置</p>
          <Button onClick={loadConfig} className="mt-4">
            <RotateCcw className="h-4 w-4 mr-2" />
            重试
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">系统配置</h1>
          <p className="text-muted-foreground">管理系统基本信息、AI集成和标题解析规则</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadConfig}>
            <RotateCcw className="h-4 w-4 mr-2" />
            重置
          </Button>
          <Button onClick={saveConfig} disabled={saving}>
            <Save className="h-4 w-4 mr-2" />
            {saving ? "保存中..." : "保存配置"}
          </Button>
        </div>
      </div>

      <Tabs defaultValue="basic" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="basic" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            基本信息
          </TabsTrigger>
          <TabsTrigger value="ai" className="flex items-center gap-2">
            <Bot className="h-4 w-4" />
            AI配置
          </TabsTrigger>
          <TabsTrigger value="patterns" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            标题解析
          </TabsTrigger>
        </TabsList>

        {/* Basic Information */}
        <TabsContent value="basic">
          <Card>
            <CardHeader>
              <CardTitle>系统基本信息</CardTitle>
              <CardDescription>配置系统名称和版本信息</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="system-name">系统名称</Label>
                  <Input
                    id="system-name"
                    value={config.system}
                    onChange={(e) => setConfig({ ...config, system: e.target.value })}
                    placeholder="输入系统名称"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="system-version">系统版本</Label>
                  <Input
                    id="system-version"
                    value={config.version}
                    onChange={(e) => setConfig({ ...config, version: e.target.value })}
                    placeholder="输入版本号"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* AI Configuration */}
        <TabsContent value="ai">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>默认AI源</CardTitle>
                <CardDescription>选择默认使用的AI源</CardDescription>
              </CardHeader>
              <CardContent>
                <Select
                  value={config.open_ai_config.default_source_name}
                  onValueChange={(value) =>
                    setConfig({
                      ...config,
                      open_ai_config: {
                        ...config.open_ai_config,
                        default_source_name: value,
                      },
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择默认AI源" />
                  </SelectTrigger>
                  <SelectContent>
                    {config.open_ai_config.sources.map((source, index) => (
                      <SelectItem key={index} value={source.name}>
                        {source.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-lg">AI源配置</CardTitle>
                    <CardDescription>管理OpenAI兼容的API源</CardDescription>
                  </div>
                  <Button onClick={addAISource} size="sm">
                    <Plus className="h-4 w-4 mr-2" />
                    添加AI源
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                {config.open_ai_config.sources.map((source, index) => (
                  <Card key={index} className="border-l-4 border-l-primary">
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-lg">AI源 #{index + 1}</CardTitle>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => removeAISource(index)}
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label>源名称</Label>
                          <Input
                            value={source.name}
                            onChange={(e) => updateAISource(index, "name", e.target.value)}
                            placeholder="输入源名称"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>API密钥</Label>
                          <Input
                            
                            value={source.key}
                            onChange={(e) => updateAISource(index, "key", e.target.value)}
                            placeholder="输入API密钥"
                          />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label>Base URL</Label>
                        <Input
                          value={source.base_url}
                          onChange={(e) => updateAISource(index, "base_url", e.target.value)}
                          placeholder="输入API基础URL"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>支持的模型</Label>
                        <Input
                          value={source.models.join(", ")}
                          onChange={(e) =>
                            updateAISource(
                              index,
                              "models",
                              e.target.value
                                .split(",")
                                .map((m) => m.trim())
                                .filter(Boolean),
                            )
                          }
                          placeholder="输入模型名称，用逗号分隔"
                        />
                        <div className="flex flex-wrap gap-1 mt-2">
                          {source.models.map((model, modelIndex) => (
                            <Badge key={modelIndex} variant="secondary">
                              {model}
                            </Badge>
                          ))}
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label>额外参数 (extra_body)</Label>
                        <Textarea
                          value={JSON.stringify(source.extra_body, null, 2)}
                          onChange={(e) => {
                            try {
                              const parsed = JSON.parse(e.target.value)
                              updateAISource(index, "extra_body", parsed)
                            } catch (error) {
                              // Keep the invalid JSON in the textarea for user to fix
                              // We'll validate on blur or save
                            }
                          }}
                          placeholder='{"key": "value"}'
                          className="font-mono text-sm min-h-[100px]"
                          onBlur={(e) => {
                            try {
                              const parsed = JSON.parse(e.target.value)
                              updateAISource(index, "extra_body", parsed)
                            } catch (error) {
                              toast({
                                title: "JSON格式错误",
                                description: "请检查extra_body的JSON格式",
                                variant: "destructive",
                              })
                              // Reset to valid JSON
                              e.target.value = JSON.stringify(source.extra_body, null, 2)
                            }
                          }}
                        />
                        <p className="text-xs text-muted-foreground">输入有效的JSON格式，用于API请求的额外参数</p>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Title Patterns */}
        <TabsContent value="patterns">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TestTube className="h-5 w-5" />
                  正则表达式测试
                </CardTitle>
                <CardDescription>测试正则表达式的匹配效果</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>测试字符串</Label>
                  <Input
                    value={testString}
                    onChange={(e) => setTestString(e.target.value)}
                    placeholder="输入要测试的标题"
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>标题解析规则</CardTitle>
                    <CardDescription>配置用于分离标题和季度的正则表达式</CardDescription>
                  </div>
                  <Button onClick={addTitlePattern} size="sm">
                    <Plus className="h-4 w-4 mr-2" />
                    添加规则
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {config.split_title_season_patterns.map((pattern, index) => (
                  <Card key={index} className="border-l-4 border-l-accent">
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-lg">规则 #{index + 1}</CardTitle>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => removeTitlePattern(index)}
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="space-y-2">
                        <Label>正则表达式</Label>
                        <Input
                          value={pattern.regular}
                          onChange={(e) => updateTitlePattern(index, "regular", e.target.value)}
                          placeholder="输入正则表达式"
                          className="font-mono"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>描述</Label>
                        <Input
                          value={pattern.description}
                          onChange={(e) => updateTitlePattern(index, "description", e.target.value)}
                          placeholder="输入规则描述"
                        />
                      </div>
                      {pattern.regular && (
                        <div className="space-y-2">
                          <Label>测试结果</Label>
                          <div className="p-3 bg-muted rounded-md">
                            {(() => {
                              const result = testRegexPattern(pattern.regular)
                              if (result) {
                                return (
                                  <div className="space-y-1">
                                    <p className="text-sm text-green-600">✓ 匹配成功</p>
                                    <div className="flex flex-wrap gap-2">
                                      {result.map((match, i) => (
                                        <Badge key={i} variant="outline">
                                          组{i + 1}: {match}
                                        </Badge>
                                      ))}
                                    </div>
                                  </div>
                                )
                              } else {
                                return <p className="text-sm text-muted-foreground">✗ 无匹配</p>
                              }
                            })()}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
