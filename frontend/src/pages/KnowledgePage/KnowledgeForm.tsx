import { useState, useEffect } from "react"
import { Loader2 } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import type { KnowledgeItem, KnowledgeType, LearningItem } from "@/store/knowledgeSlice"

interface KnowledgeFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  item: KnowledgeItem | null
  onSave: (data: Partial<KnowledgeItem> & { type: KnowledgeType }) => Promise<void>
}

interface FormState {
  type: KnowledgeType
  // Metric fields
  name: string
  definition: string
  sql_template: string
  unit: string
  owner: string
  caveats: string
  // Rule fields
  title: string
  description: string
  // Query fields
  sql: string
  // Shared fields
  tags: string
  applies_to_tables: string
  tables_used: string
}

const initialFormState: FormState = {
  type: "metric",
  name: "",
  definition: "",
  sql_template: "",
  unit: "",
  owner: "",
  caveats: "",
  title: "",
  description: "",
  sql: "",
  tags: "",
  applies_to_tables: "",
  tables_used: "",
}

const typeLabels: Record<KnowledgeType, string> = {
  metric: "Metric",
  rule: "Rule",
  query: "Query",
  learning: "Learning",
}

export function KnowledgeForm({ open, onOpenChange, item, onSave }: KnowledgeFormProps) {
  const [form, setForm] = useState<FormState>(initialFormState)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isEdit = !!item
  const isLearning = form.type === "learning" || item?.type === "learning"

  useEffect(() => {
    if (item) {
      // Map item fields to form state based on type
      const formData: FormState = {
        ...initialFormState,
        type: item.type,
        tags: item.tags?.join(", ") || "",
      }

      if (item.type === "metric") {
        formData.name = item.name || ""
        formData.definition = item.definition || ""
        formData.sql_template = item.sql_template || ""
        formData.unit = item.unit || ""
        formData.owner = item.owner || ""
        formData.caveats = item.caveats || ""
      } else if (item.type === "rule") {
        formData.title = item.title || ""
        formData.description = item.description || ""
        formData.applies_to_tables = item.applies_to_tables?.join(", ") || ""
      } else if (item.type === "query") {
        formData.name = item.name || ""
        formData.description = item.description || ""
        formData.sql = item.sql || ""
        formData.tables_used = item.tables_used?.join(", ") || ""
      }

      setForm(formData)
    } else {
      setForm(initialFormState)
    }
    setError(null)
  }, [item, open])

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const handleTypeChange = (value: string) => {
    setForm((prev) => ({ ...prev, type: value as KnowledgeType }))
  }

  const parseCommaSeparated = (value: string): string[] => {
    return value
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      // Build type-specific data object
      // We use 'any' here because the union type makes it hard to build dynamically
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const data: any = {
        type: form.type,
        tags: parseCommaSeparated(form.tags),
      }

      // Add type-specific fields
      if (form.type === "metric") {
        data.name = form.name
        data.definition = form.definition || undefined
        data.sql_template = form.sql_template
        data.unit = form.unit || undefined
        data.owner = form.owner || undefined
        data.caveats = form.caveats || undefined
      } else if (form.type === "rule") {
        data.title = form.title
        data.description = form.description || undefined
        data.applies_to_tables = parseCommaSeparated(form.applies_to_tables)
      } else if (form.type === "query") {
        data.name = form.name
        data.description = form.description || undefined
        data.sql = form.sql
        data.tables_used = parseCommaSeparated(form.tables_used)
      }

      await onSave(data)
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save knowledge item")
    } finally {
      setLoading(false)
    }
  }

  // Learning items are view-only
  if (isLearning && item && item.type === "learning") {
    const learningItem = item as LearningItem
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Learning Details</DialogTitle>
            <DialogDescription>
              This learning was automatically captured. You can promote it to a rule or query.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {learningItem.description && (
              <div className="space-y-2">
                <Label>Description</Label>
                <div className="rounded-md border p-3 bg-muted/50 text-sm">
                  {learningItem.description}
                </div>
              </div>
            )}

            {learningItem.corrected_sql && (
              <div className="space-y-2">
                <Label>Corrected SQL</Label>
                <div className="rounded-md border p-3 bg-muted/50 text-sm font-mono">
                  {learningItem.corrected_sql}
                </div>
              </div>
            )}

            {learningItem.original_error && (
              <div className="space-y-2">
                <Label>Original Error</Label>
                <div className="rounded-md border p-3 bg-muted/50 text-sm text-destructive">
                  {learningItem.original_error}
                </div>
              </div>
            )}

            {learningItem.confidence_score !== undefined && (
              <div className="space-y-2">
                <Label>Confidence</Label>
                <div className="flex items-center gap-2">
                  <div className="h-2 flex-1 rounded-full bg-muted">
                    <div
                      className="h-2 rounded-full bg-primary"
                      style={{ width: `${learningItem.confidence_score * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium">
                    {Math.round(learningItem.confidence_score * 100)}%
                  </span>
                </div>
              </div>
            )}

            {learningItem.applies_to_tables && learningItem.applies_to_tables.length > 0 && (
              <div className="space-y-2">
                <Label>Related Tables</Label>
                <div className="flex flex-wrap gap-1">
                  {learningItem.applies_to_tables.map((table) => (
                    <Badge key={table} variant="outline">
                      {table}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {learningItem.promoted_to && (
              <div className="rounded-md border border-green-200 bg-green-50 p-3 dark:border-green-800 dark:bg-green-900/20">
                <p className="text-sm text-green-800 dark:text-green-400">
                  This learning has been promoted to: <strong>{learningItem.promoted_to}</strong>
                </p>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? `Edit ${typeLabels[form.type]}` : "New Knowledge Item"}
          </DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Update the knowledge item details"
              : "Add a new metric, rule, or query to your knowledge base"}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          {error && (
            <div className="mb-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}

          <div className="space-y-4">
            {/* Type selector (only for create) */}
            {!isEdit && (
              <div className="space-y-2">
                <Label htmlFor="type">Type</Label>
                <Select value={form.type} onValueChange={handleTypeChange}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="metric">Metric</SelectItem>
                    <SelectItem value="rule">Rule</SelectItem>
                    <SelectItem value="query">Query</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Name field (for all types) */}
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                name="name"
                value={form.name}
                onChange={handleChange}
                placeholder={`Enter ${form.type} name`}
                required
              />
            </div>

            {/* Metric-specific fields */}
            {form.type === "metric" && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="definition">Definition</Label>
                  <Textarea
                    id="definition"
                    name="definition"
                    value={form.definition}
                    onChange={handleChange}
                    placeholder="Describe what this metric measures"
                    rows={2}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sql_template">SQL Template</Label>
                  <Textarea
                    id="sql_template"
                    name="sql_template"
                    value={form.sql_template}
                    onChange={handleChange}
                    placeholder="SELECT COUNT(*) FROM orders WHERE ..."
                    rows={4}
                    className="font-mono text-sm"
                  />
                  <p className="text-xs text-muted-foreground">
                    Use placeholders like {"{start_date}"} for dynamic values
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="unit">Unit</Label>
                    <Input
                      id="unit"
                      name="unit"
                      value={form.unit}
                      onChange={handleChange}
                      placeholder="e.g., USD, %, count"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="owner">Owner</Label>
                    <Input
                      id="owner"
                      name="owner"
                      value={form.owner}
                      onChange={handleChange}
                      placeholder="Team or person"
                    />
                  </div>
                </div>
              </>
            )}

            {/* Rule-specific fields */}
            {form.type === "rule" && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="title">Title</Label>
                  <Input
                    id="title"
                    name="title"
                    value={form.title}
                    onChange={handleChange}
                    placeholder="Rule title"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    name="description"
                    value={form.description}
                    onChange={handleChange}
                    placeholder="Always use LEFT JOIN when joining with optional tables..."
                    rows={3}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="applies_to_tables">Applies to Tables</Label>
                  <Input
                    id="applies_to_tables"
                    name="applies_to_tables"
                    value={form.applies_to_tables}
                    onChange={handleChange}
                    placeholder="users, orders, products"
                  />
                  <p className="text-xs text-muted-foreground">
                    Comma-separated list of tables this rule applies to
                  </p>
                </div>
              </>
            )}

            {/* Query-specific fields */}
            {form.type === "query" && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    name="description"
                    value={form.description}
                    onChange={handleChange}
                    placeholder="What this query does"
                    rows={2}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sql">SQL</Label>
                  <Textarea
                    id="sql"
                    name="sql"
                    value={form.sql}
                    onChange={handleChange}
                    placeholder="SELECT * FROM ..."
                    rows={4}
                    className="font-mono text-sm"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tables_used">Tables Used</Label>
                  <Input
                    id="tables_used"
                    name="tables_used"
                    value={form.tables_used}
                    onChange={handleChange}
                    placeholder="users, orders, products"
                  />
                  <p className="text-xs text-muted-foreground">
                    Comma-separated list of tables used in the query
                  </p>
                </div>
              </>
            )}

            {/* Tags (for all types) */}
            <div className="space-y-2">
              <Label htmlFor="tags">Tags</Label>
              <Input
                id="tags"
                name="tags"
                value={form.tags}
                onChange={handleChange}
                placeholder="reporting, sales, monthly"
              />
              <p className="text-xs text-muted-foreground">
                Comma-separated list of tags for categorization
              </p>
            </div>
          </div>

          <DialogFooter className="mt-6">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isEdit ? "Save Changes" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

interface PromoteDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  item: KnowledgeItem | null
  onPromote: (data: { promote_to: "business_rule" | "verified_query" }) => Promise<void>
}

export function PromoteDialog({ open, onOpenChange, item, onPromote }: PromoteDialogProps) {
  const [targetType, setTargetType] = useState<"business_rule" | "verified_query">("business_rule")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (item) {
      setTargetType("business_rule")
    }
    setError(null)
  }, [item, open])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      await onPromote({ promote_to: targetType })
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to promote learning")
    } finally {
      setLoading(false)
    }
  }

  if (!item || item.type !== "learning") return null

  const learningItem = item as LearningItem

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Promote Learning</DialogTitle>
          <DialogDescription>
            Convert this learning into a permanent business rule or verified query
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          {error && (
            <div className="mb-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}

          {/* Original learning content */}
          <div className="mb-4 space-y-3">
            {learningItem.description && (
              <div className="rounded-md border bg-muted/50 p-3">
                <Label className="text-xs text-muted-foreground">Description</Label>
                <p className="mt-1 text-sm">{learningItem.description}</p>
              </div>
            )}
            {learningItem.corrected_sql && (
              <div className="rounded-md border bg-muted/50 p-3">
                <Label className="text-xs text-muted-foreground">Corrected SQL</Label>
                <p className="mt-1 text-sm font-mono">{learningItem.corrected_sql}</p>
              </div>
            )}
          </div>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="target_type">Promote To</Label>
              <Select value={targetType} onValueChange={(v) => setTargetType(v as "business_rule" | "verified_query")}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="business_rule">Business Rule</SelectItem>
                  <SelectItem value="verified_query">Verified Query</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {targetType === "business_rule"
                  ? "Creates a business rule from this learning's description"
                  : "Creates a verified query from this learning's corrected SQL"}
              </p>
            </div>
          </div>

          <DialogFooter className="mt-6">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Promote to {targetType === "business_rule" ? "Business Rule" : "Verified Query"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
