import { useParams, useSearchParams } from "react-router"

import { PromptDetail } from "@/components/prompts/prompt-detail"

export default function PromptDetailPage() {
  const { id = "" } = useParams<{ id: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const versionParam = searchParams.get("v")
  const version = versionParam ? Number(versionParam) : null

  const setVersion = (v: number | null) => {
    const next = new URLSearchParams(searchParams)
    if (v == null) next.delete("v")
    else next.set("v", String(v))
    setSearchParams(next, { replace: true })
  }

  return (
    <div className="mx-auto w-full max-w-7xl">
      <PromptDetail
        promptId={id}
        version={version}
        onVersionChange={setVersion}
      />
    </div>
  )
}
