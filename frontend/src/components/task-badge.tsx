import { Badge } from "@/components/ui/badge"

const TASK_COLORS: Record<string, string> = {
  game_of_life: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200",
  arithmetic: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  linda_fallacy: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
  cellular_automata_1d: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
  ascii_shapes: "bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200",
  object_tracking: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  sally_anne: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200",
  carwash: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  inverted_cup: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200",
  strawberry: "bg-rose-100 text-rose-800 dark:bg-rose-900 dark:text-rose-200",
  measure_comparison: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  grid_tasks: "bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200",
  time_arithmetic: "bg-sky-100 text-sky-800 dark:bg-sky-900 dark:text-sky-200",
  misquote: "bg-violet-100 text-violet-800 dark:bg-violet-900 dark:text-violet-200",
  false_premise: "bg-fuchsia-100 text-fuchsia-800 dark:bg-fuchsia-900 dark:text-fuchsia-200",
  family_relations: "bg-lime-100 text-lime-800 dark:bg-lime-900 dark:text-lime-200",
  encoding_cipher: "bg-stone-100 text-stone-800 dark:bg-stone-900 dark:text-stone-200",
  symbol_arithmetic: "bg-zinc-100 text-zinc-800 dark:bg-zinc-900 dark:text-zinc-200",
  picross: "bg-slate-100 text-slate-800 dark:bg-slate-900 dark:text-slate-200",
  fancy_unicode: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  picture_algebra: "bg-neutral-100 text-neutral-800 dark:bg-neutral-900 dark:text-neutral-200",
}

export function TaskBadge({ task }: { task: string }) {
  const color = TASK_COLORS[task] ?? "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200"
  const label = task.replace(/_/g, " ")
  return (
    <Badge variant="outline" className={`text-xs font-medium border-0 ${color}`}>
      {label}
    </Badge>
  )
}
