"""Entry point for `python -m src.web`."""
import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="GoL Benchmark Web UI")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Auto-reload on code changes")
    args = parser.parse_args()

    print(f"🚀 GoL Benchmark Web UI: http://{args.host}:{args.port}")
    uvicorn.run(
        "src.web.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
