import { PromptEditorPage } from "@/components/prompts/prompt-editor-page"

export default function PromptNewPage() {
  return (
    <div className="mx-auto w-full max-w-5xl">
      <PromptEditorPage mode="new" />
    </div>
  )
}
