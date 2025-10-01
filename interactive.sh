#!/bin/bash
# 嚴格模式，-e: 命令失敗時退出, -u: 使用未定義變數時退出, -o pipefail: pipeline 中命令失敗時退出
set -uo pipefail

# --- Configuration ---
readonly ROOT_DIR=$(cd "$(dirname "$0")" && pwd)
readonly BACKEND_DIR="$ROOT_DIR/backend"
readonly FRONTEND_DIR="$ROOT_DIR/App/front"
readonly VENV_DIR="$ROOT_DIR/.venv"
readonly RUN_DIR="$ROOT_DIR/run"
readonly REQUIREMENTS_FILE="$ROOT_DIR/requirements.txt"

# --- Runtime Files ---
readonly VENV_HASH_FILE="$RUN_DIR/venv.hash"
readonly BACKEND_PID_FILE="$RUN_DIR/backend.pid"
readonly FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"
readonly BACKEND_LOG_FILE="$RUN_DIR/backend.log"
readonly FRONTEND_LOG_FILE="$RUN_DIR/frontend.log"
readonly FRONTEND_URL_FILE="$RUN_DIR/frontend.url"
readonly BACKEND_PGID_FILE="$RUN_DIR/backend.pgid"
readonly FRONTEND_PGID_FILE="$RUN_DIR/frontend.pgid"

# --- Runtime State ---
LOG_TAIL_PID=""

# --- Service Configuration ---
readonly BACKEND_PORT=8000
readonly FRONTEND_PORT=5173
readonly HEALTH_CHECK_ATTEMPTS=30
readonly HEALTH_CHECK_INTERVAL=1

# --- Colors for output ---
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# --- System specifics ---
# macOS and Linux have different sha256sum commands
if [[ "$OSTYPE" == "darwin"* ]]; then
    readonly HASH_CMD="shasum -a 256"
else
    readonly HASH_CMD="sha256sum"
fi

# --- Ensure run directory exists ---
mkdir -p "$RUN_DIR"

# --- Utility Functions ---
show_spinner() {
    local pid=$1
    local message=$2
    local spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local i=0
    while ps -p "$pid" > /dev/null 2>&1; do
        i=$(( (i+1) % ${#spin} ))
        printf "\r${CYAN}%s${NC} %s" "${spin:$i:1}" "$message"
        sleep 0.1
    done
    printf "\r%80s\r" " " # Clear the line
}

# --- Venv & Hash Management ---
get_requirements_hash() {
    if [ -f "$REQUIREMENTS_FILE" ]; then
        $HASH_CMD "$REQUIREMENTS_FILE" | cut -d' ' -f1
    else
        echo "no-requirements-file"
    fi
}

check_venv_needs_rebuild() {
    if [ ! -d "$VENV_DIR" ]; then return 0; fi
    if [ ! -f "$VENV_HASH_FILE" ]; then return 0; fi
    local current_hash=$(get_requirements_hash)
    local stored_hash=$(cat "$VENV_HASH_FILE")
    if [ "$current_hash" != "$stored_hash" ]; then return 0; fi
    return 1 # Does not need rebuild
}

rebuild_venv() {
    printf "${YELLOW}虛擬環境需要更新，正在重建...${NC}\n"
    rm -rf "$VENV_DIR"
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip >/dev/null 2>&1
    pip install -r "$REQUIREMENTS_FILE"
    deactivate
    get_requirements_hash > "$VENV_HASH_FILE"
    printf "${GREEN}虛擬環境已建立。${NC}\n"
}

# --- Health Checks ---
check_backend_health() {
    printf "${CYAN}等待後端服務啟動...${NC}"
    for ((i=1; i<=$HEALTH_CHECK_ATTEMPTS; i++)); do
        if curl -s -f "http://127.0.0.1:$BACKEND_PORT/docs" > /dev/null 2>&1; then
            printf "\r${GREEN}後端服務已就緒!${NC}              \n"
            return 0
        fi
        printf "."
        sleep $HEALTH_CHECK_INTERVAL
    done
    printf "\n${RED}後端健康檢查失敗。${NC}\n"
    return 1
}

check_frontend_health() {
    printf "${CYAN}等待前端服務啟動...${NC}"
    for ((i=1; i<=$HEALTH_CHECK_ATTEMPTS; i++)); do
        if grep -q "ready in" "$FRONTEND_LOG_FILE"; then
            printf "\r${GREEN}前端服務已就緒!${NC}              \n"
            return 0
        fi
        printf "."
        sleep $HEALTH_CHECK_INTERVAL
    done
    printf "\n${RED}前端健康檢查失敗。${NC}\n"
    return 1
}


# --- Backend Process Functions ---
check_backend() {
    if [ -f "$BACKEND_PID_FILE" ] && ps -p "$(cat "$BACKEND_PID_FILE")" > /dev/null; then
        return 0 # Is running
    else
        rm -f "$BACKEND_PID_FILE"
        return 1 # Is not running
    fi
}

start_backend() {
    if check_backend; then
        printf "${YELLOW}Backend 已經在運行 (PID: $(cat "$BACKEND_PID_FILE")).${NC}\n"
        return
    fi

    if check_venv_needs_rebuild; then
        rebuild_venv
    fi

    printf "正在啟動 Backend...\n"
    (
        source "$VENV_DIR/bin/activate"
        cd "$BACKEND_DIR"
        exec uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT
    ) > "$BACKEND_LOG_FILE" 2>&1 &

    echo $! > "$BACKEND_PID_FILE"
    # 記錄 PGID，用於安全停止
    if BACKEND_PGID=$(ps -o pgid= "$(cat "$BACKEND_PID_FILE")" 2>/dev/null | tr -d ' '); then
        printf "%s" "$BACKEND_PGID" > "$BACKEND_PGID_FILE"
    fi

    if ! check_backend_health; then
        printf "${RED}啟動 Backend 失敗. 請檢查日誌: $BACKEND_LOG_FILE${NC}\n"
        return
    fi
    printf "${GREEN}Backend 已啟動 (PID: $(cat "$BACKEND_PID_FILE")).${NC}\n"
    printf "✅ Backend URL: ${GREEN}http://localhost:%s${NC}\n" "$BACKEND_PORT"
}

stop_backend() {
    if ! check_backend; then
        printf "${YELLOW}Backend 未運行.${NC}\n"
        return
    fi
    printf "正在停止 Backend...\n"
    self_pgid=$(ps -o pgid= $$ | tr -d ' ')
    target_pid=$(cat "$BACKEND_PID_FILE")
    target_pgid=""
    if [ -f "$BACKEND_PGID_FILE" ]; then
        target_pgid=$(cat "$BACKEND_PGID_FILE")
    else
        target_pgid=$(ps -o pgid= "$target_pid" 2>/dev/null | tr -d ' ')
    fi

    if [ -n "$target_pgid" ] && [ "$target_pgid" != "$self_pgid" ]; then
        kill -TERM -- "-@$target_pgid" 2>/dev/null || kill -TERM -- "-""$target_pgid" 2>/dev/null
        sleep 1
        kill -9 -- "-@$target_pgid" 2>/dev/null || kill -9 -- "-""$target_pgid" 2>/dev/null
    else
        pkill -TERM -P "$target_pid" 2>/dev/null || true
        sleep 1
        kill -TERM "$target_pid" 2>/dev/null || true
        sleep 1
        pkill -9 -P "$target_pid" 2>/dev/null || true
        kill -9 "$target_pid" 2>/dev/null || true
    fi
    rm -f "$BACKEND_PID_FILE" "$BACKEND_PGID_FILE"
    printf "${GREEN}Backend 已停止.${NC}\n"
}

# --- Frontend Process Functions ---
check_frontend() {
    if [ -f "$FRONTEND_PID_FILE" ] && ps -p "$(cat "$FRONTEND_PID_FILE")" > /dev/null; then
        return 0 # Is running
    else
        rm -f "$FRONTEND_PID_FILE"
        return 1 # Is not running
    fi
}

start_frontend() {
    if check_frontend; then
        printf "${YELLOW}Frontend 已經在運行 (PID: $(cat "$FRONTEND_PID_FILE")).${NC}\n"
        return
    fi
    printf "正在啟動 Frontend...\n"
    (
        cd "$FRONTEND_DIR"
        npm install --silent
        exec npm run dev -- --port $FRONTEND_PORT
    ) > "$FRONTEND_LOG_FILE" 2>&1 &

    echo $! > "$FRONTEND_PID_FILE"
    # 記錄 PGID，用於安全停止
    if FRONTEND_PGID=$(ps -o pgid= "$(cat "$FRONTEND_PID_FILE")" 2>/dev/null | tr -d ' '); then
        printf "%s" "$FRONTEND_PGID" > "$FRONTEND_PGID_FILE"
    fi

    if ! check_frontend_health; then
        printf "${RED}啟動 Frontend 失敗. 請檢查日誌: $FRONTEND_LOG_FILE${NC}\n"
        return
    fi

    local FRONTEND_URL="http://localhost:$FRONTEND_PORT/"
    # 從日誌擷取實際啟動網址
    if grep -q "Local:" "$FRONTEND_LOG_FILE"; then
        FRONTEND_URL=$(grep -Eo "Local:\s+https?://localhost:[0-9]+/?" "$FRONTEND_LOG_FILE" | tail -n 1 | awk '{print $2}')
    fi

    printf "${GREEN}Frontend 已啟動 (PID: $(cat "$FRONTEND_PID_FILE")).${NC}\n"
    echo "$FRONTEND_URL" > "$FRONTEND_URL_FILE"
    printf "✅ Frontend URL: ${GREEN}%s${NC}\n" "$FRONTEND_URL"
}

stop_frontend() {
    if ! check_frontend; then
        printf "${YELLOW}Frontend 未運行.${NC}\n"
        return
    fi
    printf "正在停止 Frontend...\n"
    self_pgid=$(ps -o pgid= $$ | tr -d ' ')
    target_pid=$(cat "$FRONTEND_PID_FILE")
    target_pgid=""
    if [ -f "$FRONTEND_PGID_FILE" ]; then
        target_pgid=$(cat "$FRONTEND_PGID_FILE")
    else
        target_pgid=$(ps -o pgid= "$target_pid" 2>/dev/null | tr -d ' ')
    fi

    if [ -n "$target_pgid" ] && [ "$target_pgid" != "$self_pgid" ]; then
        kill -TERM -- "-@$target_pgid" 2>/dev/null || kill -TERM -- "-""$target_pgid" 2>/dev/null
        sleep 1
        kill -9 -- "-@$target_pgid" 2>/dev/null || kill -9 -- "-""$target_pgid" 2>/dev/null
    else
        pkill -TERM -P "$target_pid" 2>/dev/null || true
        sleep 1
        kill -TERM "$target_pid" 2>/dev/null || true
        sleep 1
        pkill -9 -P "$target_pid" 2>/dev/null || true
        kill -9 "$target_pid" 2>/dev/null || true
    fi
    rm -f "$FRONTEND_PID_FILE" "$FRONTEND_PGID_FILE"
    printf "${GREEN}Frontend 已停止.${NC}\n"
}

# --- Status Display Functions ---
show_status() {
    printf "\n${CYAN}=== 服務狀態 ===${NC}\n"
    if check_backend; then
        printf "Backend:  ${GREEN}RUNNING${NC} (PID: $(cat "$BACKEND_PID_FILE"))\n"
        printf "  └─ URL: ${GREEN}http://localhost:%s${NC}\n" "$BACKEND_PORT"
    else
        printf "Backend:  ${RED}STOPPED${NC}\n"
    fi
    
    if check_frontend; then
        printf "Frontend: ${GREEN}RUNNING${NC} (PID: $(cat "$FRONTEND_PID_FILE"))\n"
        if [ -f "$FRONTEND_URL_FILE" ]; then
            FRONTEND_URL=$(cat "$FRONTEND_URL_FILE")
            printf "  └─ URL: ${GREEN}%s${NC}\n" "$FRONTEND_URL"
        fi
    else
        printf "Frontend: ${RED}STOPPED${NC}\n"
    fi
    printf "${CYAN}================${NC}\n\n"
}

show_help() {
    printf "\n${BLUE}=== 可用指令 ===${NC}\n"
    printf "${YELLOW}start${NC}     - 啟動所有服務\n"
    printf "${YELLOW}stop${NC}      - 停止所有服務\n"
    printf "${YELLOW}restart${NC}   - 重新啟動所有服務\n"
    printf "${YELLOW}status${NC}    - 顯示服務狀態\n"
    printf "${YELLOW}logs${NC}      - 顯示即時日誌\n"
    printf "${YELLOW}backend${NC}   - 只啟動後端\n"
    printf "${YELLOW}frontend${NC}  - 只啟動前端\n"
    printf "${YELLOW}help${NC}      - 顯示此說明\n"
    printf "${YELLOW}exit${NC}      - 離開程式\n"
    printf "${BLUE}================${NC}\n\n"
}

show_logs() {
    printf "\n${CYAN}=== 即時日誌 (按 Ctrl+C 停止) ===${NC}\n"
    printf "${YELLOW}正在監控日誌檔案...${NC}\n\n"
    
    # 使用 tail -f 監控兩個日誌檔案
    if [ -f "$BACKEND_LOG_FILE" ] && [ -f "$FRONTEND_LOG_FILE" ]; then
        tail -f "$BACKEND_LOG_FILE" "$FRONTEND_LOG_FILE" &
        LOG_TAIL_PID=$!

        # 暫存既有的 SIGINT trap，避免 Ctrl+C 直接結束管理器
        local PREV_SIGINT_TRAP
        PREV_SIGINT_TRAP=$(trap -p SIGINT)

        trap '__logs_sigint_handler' SIGINT

        __logs_wait_for_tail

        # 還原原本的 SIGINT trap
        if [ -n "$PREV_SIGINT_TRAP" ]; then
            eval "$PREV_SIGINT_TRAP"
        else
            trap - SIGINT
        fi
        LOG_TAIL_PID=""
    else
        printf "${RED}日誌檔案不存在${NC}\n"
    fi
}

__logs_wait_for_tail() {
    if [ -n "$LOG_TAIL_PID" ]; then
        wait "$LOG_TAIL_PID" 2>/dev/null
    fi
}

__logs_sigint_handler() {
    printf "\n${YELLOW}停止監控日誌。${NC}\n"
    if [ -n "$LOG_TAIL_PID" ]; then
        kill -TERM "$LOG_TAIL_PID" 2>/dev/null || true
        sleep 0.1
        kill -9 "$LOG_TAIL_PID" 2>/dev/null || true
    fi
}

# --- 清理函數 ---
cleanup() {
    printf "\n\n${YELLOW}正在清理並停止所有服務...${NC}\n"
    stop_frontend
    stop_backend
    printf "${GREEN}停止成功！${NC}\n"
    exit 0
}

# 設定 Ctrl+C 處理
trap cleanup SIGINT

# --- 主程式 ---
printf "${GREEN}🚀 互動式服務管理器${NC}\n"
printf "${BLUE}輸入 'help' 查看可用指令${NC}\n"

# 自動啟動服務
printf "\n${YELLOW}正在自動啟動服務...${NC}\n"
start_backend
start_frontend
show_status

# 主迴圈
while true; do
    printf "${CYAN}服務管理器 >${NC} "
    if ! read -r command; then
        # Handle Ctrl+D (EOF)
        cleanup
    fi
    
    case "$command" in
        start)
            start_backend
            start_frontend
            show_status
            ;;
        stop)
            stop_frontend
            stop_backend
            show_status
            ;;
        restart)
            printf "${YELLOW}--- 正在重啟服務 ---${NC}\n"
            stop_frontend
            stop_backend
            printf "等待服務關閉...\n"
            sleep 2
            start_backend
            start_frontend
            show_status
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        backend)
            start_backend
            show_status
            ;;
        frontend)
            start_frontend
            show_status
            ;;
        help)
            show_help
            ;;
        exit|quit|q)
            cleanup
            ;;
        "")
            # 空輸入，重新顯示狀態
            show_status
            ;;
        *)
            printf "${RED}未知指令: %s${NC}\n" "$command"
            printf "輸入 'help' 查看可用指令\n"
            ;;
    esac
done
