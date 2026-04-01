import { Component, type ErrorInfo, type ReactNode } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { AlertTriangle } from "lucide-react"

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      if (this.props.fallback) return this.props.fallback

      return (
        <Card className="m-4">
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <AlertTriangle className="h-10 w-10 text-destructive opacity-60" />
            <div className="text-center">
              <p className="text-lg font-medium">Something went wrong</p>
              <p className="mt-1 text-sm text-muted-foreground max-w-md">
                {this.state.error.message}
              </p>
            </div>
            <Button variant="outline" onClick={() => this.setState({ error: null })}>
              Try again
            </Button>
          </CardContent>
        </Card>
      )
    }

    return this.props.children
  }
}
