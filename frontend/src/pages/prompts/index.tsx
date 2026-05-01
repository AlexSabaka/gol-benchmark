import { Link } from "react-router"
import { Plus } from "lucide-react"

import { PageHeader } from "@/components/layout/page-header"
import { Button } from "@/components/ui/button"
import { PromptCatalog } from "@/components/prompts/prompt-catalog"

export default function PromptsPage() {
  return (
    <div className="mx-auto w-full max-w-7xl">
      <PageHeader
        title="Prompt Studio"
        description="System Prompts · Manage versioned prompts used as a benchmark axis."
        actions={
          <Button asChild>
            <Link to="/prompts/new">
              <Plus className="size-4" />
              New prompt
            </Link>
          </Button>
        }
      />
      <PromptCatalog />
    </div>
  )
}
