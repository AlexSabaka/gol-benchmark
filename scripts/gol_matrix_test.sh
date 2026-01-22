#!/usr/bin/env bash
# A simple script to run matrix tests on the gol_eval module
# gol_eval script options available for matrix testing:
#   --difficulty {easy,medium,hard,nightmare}
#   --temperature TEMPERATURE
#   --ctx-len CTX_LEN
#   --num-predict NUM_PREDICT
#   --top-k TOP_K (default: 40)
#   --min-k MIN_K (default: 1)
#   --min-p MIN_P (default: 0.05)
#   --prompt-style {linguistic,symbolic,examples,casual,minimal}
#   --live-dead-cell-markers LIVE_DEAD_CELL_MARKERS (comma separated, default: "1,0")
#   --prompt-language {en,fr,es,de,zh,ua}
# All other script options should be passed as-is

set -euo pipefail

# Default values
DEFAULT_TOP_K=40
DEFAULT_MIN_K=1
DEFAULT_MIN_P=0.05
DEFAULT_MARKERS="1,0"

# Arrays for matrix testing
MODELS=()
DIFFICULTIES=("easy" "medium" "hard" "nightmare")
TEMPERATURES=()
CTX_LENS=()
NUM_PREDICTS=()
TOP_K_VALUES=("$DEFAULT_TOP_K")
MIN_K_VALUES=("$DEFAULT_MIN_K")
MIN_P_VALUES=("$DEFAULT_MIN_P")
PROMPT_STYLES=("linguistic" "symbolic" "examples" "casual" "minimal")
MARKERS=("$DEFAULT_MARKERS")
LANGUAGES=("en" "fr" "es" "de" "zh" "ua")

# Function to show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS] --model MODEL [MODEL ...] -- [gol_eval_options]

Matrix test runner for gol_eval module.

Required:
  --model, -m MODEL [MODEL ...]     Models to test (required)

Matrix Options:
  --difficulty {easy,medium,hard,nightmare}  Difficulty levels to test
  --temperature TEMPERATURE         Temperature values to test
  --ctx-len CTX_LEN                 Context length values to test
  --num-predict NUM_PREDICT         Number of predictions to test
  --top-k TOP_K                     Top-K values to test (default: $DEFAULT_TOP_K)
  --min-k MIN_K                     Min-K values to test (default: $DEFAULT_MIN_K)
  --min-p MIN_P                     Min-P values to test (default: $DEFAULT_MIN_P)
  --prompt-style {linguistic,symbolic,examples,casual,minimal}  Prompt styles to test
  --live-dead-cell-markers MARKERS  Cell markers to test (comma separated, default: "$DEFAULT_MARKERS")
  --prompt-language {en,fr,es,de,zh,ua}  Languages to test

All other gol_eval options should be passed after -- separator.
EOF
}

# Parse command line arguments
GOL_EVAL_ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -m|--model)
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                MODELS+=("$1")
                shift
            done
            ;;
        --difficulty)
            DIFFICULTIES=()
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                DIFFICULTIES+=("$1")
                shift
            done
            ;;
        --temperature)
            TEMPERATURES=()
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                TEMPERATURES+=("$1")
                shift
            done
            ;;
        --ctx-len)
            CTX_LENS=()
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                CTX_LENS+=("$1")
                shift
            done
            ;;
        --num-predict)
            NUM_PREDICTS=()
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                NUM_PREDICTS+=("$1")
                shift
            done
            ;;
        --top-k)
            TOP_K_VALUES=()
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                TOP_K_VALUES+=("$1")
                shift
            done
            ;;
        --min-k)
            MIN_K_VALUES=()
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                MIN_K_VALUES+=("$1")
                shift
            done
            ;;
        --min-p)
            MIN_P_VALUES=()
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                MIN_P_VALUES+=("$1")
                shift
            done
            ;;
        --prompt-style)
            PROMPT_STYLES=()
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                PROMPT_STYLES+=("$1")
                shift
            done
            ;;
        --live-dead-cell-markers)
            MARKERS=()
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                MARKERS+=("$1")
                shift
            done
            ;;
        --prompt-language)
            LANGUAGES=()
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                LANGUAGES+=("$1")
                shift
            done
            ;;
        --)
            shift
            GOL_EVAL_ARGS=("$@")
            break
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Function to run a single test
run_test() {
    local difficulty="$1"
    local temperature="$2"
    local ctx_len="$3"
    local num_predict="$4"
    local top_k="$5"
    local min_k="$6"
    local min_p="$7"
    local prompt_style="$8"
    local markers="${9}"
    local language="${10}"
    
    # echo "Running test:"
    # echo "  Difficulty: $difficulty"
    # echo "  Temperature: $temperature"
    # echo "  Context Length: $ctx_len"
    # echo "  Num Predict: $num_predict"
    # echo "  Top-K: $top_k"
    # echo "  Min-K: $min_k"
    # echo "  Min-P: $min_p"
    # echo "  Prompt Style: $prompt_style"
    # echo "  Markers: $markers"
    # echo "  Language: $language"
    # echo "  Additional Args: ${GOL_EVAL_ARGS[*]}"
    # echo ""
    
    # Build the command
    local cmd=(python -m src.benchmarks.gol_eval )
    
    [[ -n "$difficulty" ]] && cmd+=(--difficulty "$difficulty")
    [[ -n "$temperature" ]] && cmd+=(--temperature "$temperature")
    [[ -n "$ctx_len" ]] && cmd+=(--ctx-len "$ctx_len")
    [[ -n "$num_predict" ]] && cmd+=(--num-predict "$num_predict")
    [[ -n "$top_k" ]] && cmd+=(--top-k "$top_k")
    [[ -n "$min_k" ]] && cmd+=(--min-k "$min_k")
    [[ -n "$min_p" ]] && cmd+=(--min-p "$min_p")
    [[ -n "$prompt_style" ]] && cmd+=(--prompt-style "$prompt_style")
    [[ -n "$markers" ]] && cmd+=(--live-dead-cell-markers "$markers")
    [[ -n "$language" ]] && cmd+=(--prompt-language "$language")
    
    # Add additional arguments
    cmd+=("${GOL_EVAL_ARGS[@]}")
    
    # Run the command
    echo "Executing: ${cmd[*]}"
    "${cmd[@]}"
    echo "----------------------------------------"
}

# # Main matrix testing loop
# echo "Starting matrix tests..."
# echo "Difficulties: ${DIFFICULTIES[*]}"
# echo "Temperatures: ${TEMPERATURES[*]:-default}"
# echo "Context Lengths: ${CTX_LENS[*]:-default}"
# echo "Num Predicts: ${NUM_PREDICTS[*]:-default}"
# echo "Top-K Values: ${TOP_K_VALUES[*]}"
# echo "Min-K Values: ${MIN_K_VALUES[*]}"
# echo "Min-P Values: ${MIN_P_VALUES[*]}"
# echo "Prompt Styles: ${PROMPT_STYLES[*]}"
# echo "Markers: ${MARKERS[*]}"
# echo "Languages: ${LANGUAGES[*]}"
# echo "Additional Args: ${GOL_EVAL_ARGS[*]}"
# echo ""

# Run tests for each combination
for difficulty in "${DIFFICULTIES[@]}"; do
    for prompt_style in "${PROMPT_STYLES[@]}"; do
        for language in "${LANGUAGES[@]}"; do
            for marker in "${MARKERS[@]}"; do
                # Handle optional parameters - use first value or empty if not set
                local_temp=${TEMPERATURES[0]:-}
                local_ctx=${CTX_LENS[0]:-}
                local_predict=${NUM_PREDICTS[0]:-}
                local_top_k=${TOP_K_VALUES[0]}
                local_min_k=${MIN_K_VALUES[0]}
                local_min_p=${MIN_P_VALUES[0]}
                
                # If multiple values exist, run tests for each
                if [[ ${#TEMPERATURES[@]} -gt 1 ]]; then
                    for temp in "${TEMPERATURES[@]}"; do
                        run_test "$difficulty" "$temp" "$local_ctx" "$local_predict" "$local_top_k" "$local_min_k" "$local_min_p" "$prompt_style" "$marker" "$language"
                    done
                elif [[ ${#CTX_LENS[@]} -gt 1 ]]; then
                    for ctx in "${CTX_LENS[@]}"; do
                        run_test "$difficulty" "$local_temp" "$ctx" "$local_predict" "$local_top_k" "$local_min_k" "$local_min_p" "$prompt_style" "$marker" "$language"
                    done
                elif [[ ${#NUM_PREDICTS[@]} -gt 1 ]]; then
                    for predict in "${NUM_PREDICTS[@]}"; do
                        run_test "$difficulty" "$local_temp" "$local_ctx" "$predict" "$local_top_k" "$local_min_k" "$local_min_p" "$prompt_style" "$marker" "$language"
                    done
                elif [[ ${#TOP_K_VALUES[@]} -gt 1 ]]; then
                    for top_k in "${TOP_K_VALUES[@]}"; do
                        run_test "$difficulty" "$local_temp" "$local_ctx" "$local_predict" "$top_k" "$local_min_k" "$local_min_p" "$prompt_style" "$marker" "$language"
                    done
                elif [[ ${#MIN_K_VALUES[@]} -gt 1 ]]; then
                    for min_k in "${MIN_K_VALUES[@]}"; do
                        run_test "$difficulty" "$local_temp" "$local_ctx" "$local_predict" "$local_top_k" "$min_k" "$local_min_p" "$prompt_style" "$marker" "$language"
                    done
                elif [[ ${#MIN_P_VALUES[@]} -gt 1 ]]; then
                    for min_p in "${MIN_P_VALUES[@]}"; do
                        run_test "$difficulty" "$local_temp" "$local_ctx" "$local_predict" "$local_top_k" "$local_min_k" "$min_p" "$prompt_style" "$marker" "$language"
                    done
                else
                    # Run single test with default/first values
                    run_test "$difficulty" "$local_temp" "$local_ctx" "$local_predict" "$local_top_k" "$local_min_k" "$local_min_p" "$prompt_style" "$marker" "$language"
                fi
            done
        done
    done
done

echo "Matrix testing completed!"