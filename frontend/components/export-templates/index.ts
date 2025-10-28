import type { ExportTemplate } from "./aipan-template"
import { AipanTemplate } from "./aipan-template"

// 导出模板注册表
export const EXPORT_TEMPLATES: ExportTemplate[] = [
  AipanTemplate,
  // 未来可以在这里添加更多导出模板
]

// 根据名称获取导出模板
export function getExportTemplate(name: string): ExportTemplate | undefined {
  return EXPORT_TEMPLATES.find((template) => template.name === name)
}
