"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/hooks/use-toast"
import { PanCloudAPI, type PanCloud, type CreatePanCloudRequest } from "@/lib/pancloud-api"
import { Plus, Edit, Trash2, Power, PowerOff, Cloud, HardDrive } from "lucide-react"

export function PanCloudManager() {
  const [panClouds, setPanClouds] = useState<PanCloud[]>([])
  const [loading, setLoading] = useState(true)
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [editingPanCloud, setEditingPanCloud] = useState<PanCloud | null>(null)
  const { toast } = useToast()

  const [createForm, setCreateForm] = useState<CreatePanCloudRequest>({
    name: "",
    cloud_type: "Quark",
    cookie: "",
    enable: true,
  })

  const [editForm, setEditForm] = useState({
    cookie: "",
    enable: true,
  })

  useEffect(() => {
    loadPanClouds()
  }, [])

  const loadPanClouds = async () => {
    try {
      setLoading(true)
      const data = await PanCloudAPI.listPanClouds()
      setPanClouds(data)
    } catch (error) {
      toast({
        title: "加载失败",
        description: "无法加载网盘配置列表",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async () => {
    try {
      await PanCloudAPI.createPanCloud(createForm)
      toast({
        title: "创建成功",
        description: "网盘配置已成功创建",
      })
      setIsCreateDialogOpen(false)
      setCreateForm({
        name: "",
        cloud_type: "Quark",
        cookie: "",
        enable: true,
      })
      loadPanClouds()
    } catch (error) {
      toast({
        title: "创建失败",
        description: "无法创建网盘配置",
        variant: "destructive",
      })
    }
  }

  const handleEdit = async () => {
    if (!editingPanCloud) return

    try {
      await PanCloudAPI.updatePanCloud(editingPanCloud.name, editForm)
      toast({
        title: "更新成功",
        description: "网盘配置已成功更新",
      })
      setIsEditDialogOpen(false)
      setEditingPanCloud(null)
      loadPanClouds()
    } catch (error) {
      toast({
        title: "更新失败",
        description: "无法更新网盘配置",
        variant: "destructive",
      })
    }
  }

  const handleDelete = async (name: string) => {
    if (!confirm("确定要删除这个网盘配置吗？")) return

    try {
      await PanCloudAPI.deletePanCloud(name)
      toast({
        title: "删除成功",
        description: "网盘配置已成功删除",
      })
      loadPanClouds()
    } catch (error) {
      toast({
        title: "删除失败",
        description: "无法删除网盘配置",
        variant: "destructive",
      })
    }
  }

  const handleToggleEnable = async (panCloud: PanCloud) => {
    try {
      if (panCloud.enable) {
        await PanCloudAPI.disablePanCloud(panCloud.name)
        toast({
          title: "已禁用",
          description: `${panCloud.cloud_type} 网盘已禁用`,
        })
      } else {
        await PanCloudAPI.enablePanCloud(panCloud.name)
        toast({
          title: "已启用",
          description: `${panCloud.cloud_type} 网盘已启用`,
        })
      }
      loadPanClouds()
    } catch (error) {
      toast({
        title: "操作失败",
        description: "无法切换网盘状态",
        variant: "destructive",
      })
    }
  }

  const openEditDialog = (panCloud: PanCloud) => {
    setEditingPanCloud(panCloud)
    setEditForm({
      cookie: panCloud.cookie,
      enable: panCloud.enable,
    })
    setIsEditDialogOpen(true)
  }

  const getCloudIcon = (cloudType: string) => {
    return cloudType === "Quark" ? <Cloud className="h-4 w-4" /> : <HardDrive className="h-4 w-4" />
  }

  const getCloudColor = (cloudType: string) => {
    return cloudType === "Quark"
      ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300"
      : "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300"
  }

  if (loading) {
    return (
      <div className="container mx-auto px-6 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">加载网盘配置中...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-3xl font-bold">网盘配置管理</h2>
          <p className="text-muted-foreground mt-2">管理用于转存影视资源的网盘账户配置</p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button className="flex items-center gap-2">
              <Plus className="h-4 w-4" />
              添加网盘
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>添加网盘配置</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">网盘名称</Label>
                <Input
                  id="name"
                  placeholder="如: 4295quark"
                  value={createForm.name}
                  onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="cloud_type">网盘类型</Label>
                <Select
                  value={createForm.cloud_type}
                  onValueChange={(value: "Quark" | "Baidu") => setCreateForm({ ...createForm, cloud_type: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Quark">夸克网盘</SelectItem>
                    <SelectItem value="Baidu">百度网盘</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="cookie">Cookie</Label>
                <Textarea
                  id="cookie"
                  placeholder="请输入网盘的认证Cookie..."
                  value={createForm.cookie}
                  onChange={(e) => setCreateForm({ ...createForm, cookie: e.target.value })}
                  rows={4}
                />
              </div>
              <div className="flex items-center space-x-2">
                <Switch
                  id="enable"
                  checked={createForm.enable}
                  onCheckedChange={(checked) => setCreateForm({ ...createForm, enable: checked })}
                />
                <Label htmlFor="enable">启用此网盘</Label>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                取消
              </Button>
              <Button onClick={handleCreate}>创建</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {panClouds.map((panCloud) => (
          <Card key={panCloud.name} className="hover:shadow-lg transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {getCloudIcon(panCloud.cloud_type)}
                  <CardTitle className="text-lg">{panCloud.name}</CardTitle>
                </div>
                <Badge className={getCloudColor(panCloud.cloud_type)}>{panCloud.cloud_type}</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">网盘名称:</span>
                  <span className="font-mono">{panCloud.name}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">状态:</span>
                  <Badge variant={panCloud.enable ? "default" : "secondary"}>
                    {panCloud.enable ? "已启用" : "已禁用"}
                  </Badge>
                </div>
                <div className="space-y-1">
                  <span className="text-sm text-muted-foreground">Cookie:</span>
                  <div className="text-xs font-mono bg-muted p-2 rounded truncate">
                    {panCloud.cookie.substring(0, 50)}...
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleToggleEnable(panCloud)}
                  className="flex items-center gap-1"
                >
                  {panCloud.enable ? (
                    <>
                      <PowerOff className="h-3 w-3" />
                      禁用
                    </>
                  ) : (
                    <>
                      <Power className="h-3 w-3" />
                      启用
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => openEditDialog(panCloud)}
                  className="flex items-center gap-1"
                >
                  <Edit className="h-3 w-3" />
                  编辑
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDelete(panCloud.name)}
                  className="flex items-center gap-1 text-destructive hover:text-destructive"
                >
                  <Trash2 className="h-3 w-3" />
                  删除
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {panClouds.length === 0 && (
        <div className="text-center py-12">
          <Cloud className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">暂无网盘配置</h3>
          <p className="text-muted-foreground mb-4">开始添加您的第一个网盘配置</p>
          <Button onClick={() => setIsCreateDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            添加网盘
          </Button>
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>编辑网盘配置</DialogTitle>
          </DialogHeader>
          {editingPanCloud && (
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>网盘类型</Label>
                <div className="flex items-center gap-2 p-2 bg-muted rounded">
                  {getCloudIcon(editingPanCloud.cloud_type)}
                  <span>{editingPanCloud.cloud_type}</span>
                  <Badge className={getCloudColor(editingPanCloud.cloud_type)}>{editingPanCloud.cloud_type}</Badge>
                </div>
              </div>
              <div className="space-y-2">
                <Label>网盘名称</Label>
                <div className="p-2 bg-muted rounded font-mono">{editingPanCloud.name}</div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit_cookie">Cookie</Label>
                <Textarea
                  id="edit_cookie"
                  placeholder="请输入网盘的认证Cookie..."
                  value={editForm.cookie}
                  onChange={(e) => setEditForm({ ...editForm, cookie: e.target.value })}
                  rows={4}
                />
              </div>
              <div className="flex items-center space-x-2">
                <Switch
                  id="edit_enable"
                  checked={editForm.enable}
                  onCheckedChange={(checked) => setEditForm({ ...editForm, enable: checked })}
                />
                <Label htmlFor="edit_enable">启用此网盘</Label>
              </div>
            </div>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleEdit}>保存更改</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
