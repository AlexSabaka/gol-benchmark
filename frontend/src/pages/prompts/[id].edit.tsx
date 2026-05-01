import { useParams } from "react-router"

import { PromptEditorPage } from "@/components/prompts/prompt-editor-page"

export default function PromptEditPage() {
  const { id = "" } = useParams<{ id: string }>()
  return (
    <div className="mx-auto w-full max-w-5xl">
      <PromptEditorPage mode="edit" promptId={id} />
    </div>
  )
}
