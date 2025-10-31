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
readonly ENV_FILE="$BACKEND_DIR/.env"

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

# --- API Key Management ---
check_api_key() {
    # 檢查 .env 文件是否存在
    if [ ! -f "$ENV_FILE" ]; then
        return 1  # .env 文件不存在
    fi
    
    # 檢查是否包含有效的 OPENAI_API_KEY
    if grep -q "^OPENAI_API_KEY=.\+$" "$ENV_FILE" 2>/dev/null; then
        local api_key=$(grep "^OPENAI_API_KEY=" "$ENV_FILE" | cut -d'=' -f2-)
        # 檢查是否為佔位符
        if [ "$api_key" = "YOUR_OPENAI_API_KEY_HERE" ] || [ -z "$api_key" ]; then
            return 1  # API Key 是佔位符或空值
        fi
        return 0  # API Key 存在且有效
    else
        return 1  # 沒有找到 OPENAI_API_KEY
    fi
}

prompt_for_api_key() {
    printf "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    printf "${RED}⚠️  缺少 OpenAI API 金鑰${NC}\n"
    printf "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n\n"
    
    printf "${CYAN}此應用程式需要 OpenAI API 金鑰才能運行。${NC}\n\n"
    
    printf "${BLUE}如何獲取 API 金鑰：${NC}\n"
    printf "1. 前往 ${GREEN}https://platform.openai.com/api-keys${NC}\n"
    printf "2. 登入您的 OpenAI 帳戶\n"
    printf "3. 點擊 'Create new secret key' 創建新的 API 金鑰\n"
    printf "4. 複製生成的金鑰（格式類似：sk-...）\n\n"
    
    printf "${YELLOW}請輸入您的 OpenAI API 金鑰：${NC}\n"
    printf "${CYAN}>${NC} "
    
    # 讀取 API 金鑰（隱藏輸入）
    local api_key=""
    read -r api_key
    
    # 驗證輸入
    if [ -z "$api_key" ]; then
        printf "\n${RED}錯誤：API 金鑰不能為空。${NC}\n"
        return 1
    fi
    
    # 簡單驗證格式（OpenAI API 金鑰通常以 sk- 開頭）
    if [[ ! "$api_key" =~ ^sk- ]]; then
        printf "\n${YELLOW}警告：API 金鑰格式可能不正確（通常以 'sk-' 開頭）${NC}\n"
        printf "${YELLOW}是否仍要繼續？(y/N): ${NC}"
        read -r confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            printf "${RED}已取消。${NC}\n"
            return 1
        fi
    fi
    
    # 創建 .env 文件
    printf "\n${CYAN}正在創建 .env 文件...${NC}\n"
    cat > "$ENV_FILE" << EOF
# OpenAI API Configuration
OPENAI_API_KEY=$api_key

# 其他環境變數可以在此添加
# 例如：
# BACKEND_PORT=8000
# FRONTEND_PORT=5173
EOF
    
    if [ $? -eq 0 ]; then
        printf "${GREEN}✅ .env 文件已成功創建！${NC}\n"
        printf "${CYAN}位置：${ENV_FILE}${NC}\n\n"
        
        # 立即驗證 API 金鑰
        if verify_api_key_with_openai "$api_key"; then
            printf "${YELLOW}注意事項：${NC}\n"
            printf "• .env 文件包含敏感資訊，請勿分享或提交到版本控制系統\n"
            printf "• 如需更新 API 金鑰，可直接編輯 ${ENV_FILE}\n"
            printf "• 或刪除該文件後重新啟動，系統會再次提示輸入\n\n"
            return 0
        else
            printf "${YELLOW}API 金鑰驗證失敗，但 .env 文件已創建。${NC}\n"
            printf "${YELLOW}請檢查金鑰是否正確，或稍後使用 'apikey' 命令更新。${NC}\n\n"
            return 1
        fi
    else
        printf "${RED}❌ 創建 .env 文件失敗。${NC}\n"
        return 1
    fi
}

verify_api_key_with_openai() {
    local api_key="$1"
    printf "${CYAN}正在驗證 API 金鑰有效性...${NC}"
    
    # 使用 OpenAI API 驗證金鑰並獲取模型名單
    local response=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer $api_key" \
        "https://api.openai.com/v1/models" 2>/dev/null)
    
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        # 解析模型名單
        local model_count=$(echo "$body" | grep -o '"id"' | wc -l | tr -d ' ')
        local gpt_models=$(echo "$body" | grep -o '"gpt-[^"]*"' | sort -u | tr -d '"' | head -5)
        
        printf "\r${GREEN}✅ API 金鑰驗證成功！${NC}              \n"
        printf "${CYAN}可用模型數量：${model_count}${NC}\n"
        
        if [ -n "$gpt_models" ]; then
            printf "${CYAN}主要 GPT 模型：${NC}\n"
            echo "$gpt_models" | while read -r model; do
                printf "  • ${GREEN}%s${NC}\n" "$model"
            done
        fi
        printf "\n"
        return 0
    elif [ "$http_code" = "401" ]; then
        printf "\r${RED}❌ API 金鑰無效或已過期${NC}\n"
        return 1
    elif [ "$http_code" = "429" ]; then
        printf "\r${YELLOW}⚠️  API 請求過於頻繁，請稍後再試${NC}\n"
        return 1
    elif [ "$http_code" = "403" ]; then
        printf "\r${RED}❌ API 金鑰權限不足${NC}\n"
        return 1
    else
        printf "\r${YELLOW}⚠️  無法驗證 API 金鑰（HTTP ${http_code}）${NC}\n"
        return 1
    fi
}

verify_api_key_with_backend() {
    printf "${CYAN}正在驗證後端服務...${NC}"
    
    # 等待後端啟動
    sleep 2
    
    # 嘗試呼叫健康檢查端點
    local health_response=$(curl -s -f "http://127.0.0.1:$BACKEND_PORT/api/v1/meta/health" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        printf "\r${GREEN}✅ 後端服務運行正常！${NC}              \n"
        return 0
    else
        printf "\r${YELLOW}⚠️  後端服務可能尚未完全啟動${NC}\n"
        return 0  # 仍然返回成功，讓後端繼續啟動
    fi
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

    # 檢查 API 金鑰
    if ! check_api_key; then
        if ! prompt_for_api_key; then
            printf "${RED}無法啟動 Backend：缺少有效的 API 金鑰。${NC}\n"
            return 1
        fi
    else
        printf "${GREEN}✅ 已找到 API 金鑰${NC}\n"
        # 驗證現有的 API 金鑰
        local current_key=$(grep "^OPENAI_API_KEY=" "$ENV_FILE" | cut -d'=' -f2-)
        if ! verify_api_key_with_openai "$current_key"; then
            printf "${YELLOW}API 金鑰驗證失敗，但將繼續啟動後端。${NC}\n"
            printf "${YELLOW}請稍後使用 'apikey' 命令檢查或更新金鑰。${NC}\n"
        fi
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
    printf "${YELLOW}apikey${NC}    - 管理 API 金鑰\n"
    printf "${YELLOW}help${NC}      - 顯示此說明\n"
    printf "${YELLOW}exit${NC}      - 離開程式\n"
    printf "${BLUE}================${NC}\n\n"
}

manage_api_key() {
    printf "\n${CYAN}=== API 金鑰管理 ===${NC}\n\n"
    
    if check_api_key; then
        local masked_key=$(grep "^OPENAI_API_KEY=" "$ENV_FILE" | cut -d'=' -f2- | sed 's/\(.\{7\}\).*/\1.../')
        printf "${GREEN}✅ 目前已設定 API 金鑰：${masked_key}${NC}\n\n"
        
        printf "選項：\n"
        printf "1) 顯示完整金鑰\n"
        printf "2) 驗證 API 金鑰\n"
        printf "3) 更新 API 金鑰\n"
        printf "4) 刪除 API 金鑰\n"
        printf "5) 返回\n\n"
        printf "${CYAN}請選擇 (1-5): ${NC}"
        read -r choice
        
        case "$choice" in
            1)
                local full_key=$(grep "^OPENAI_API_KEY=" "$ENV_FILE" | cut -d'=' -f2-)
                printf "\n${YELLOW}完整 API 金鑰：${NC}\n${full_key}\n\n"
                printf "${RED}注意：請勿與他人分享此金鑰！${NC}\n"
                ;;
            2)
                local current_key=$(grep "^OPENAI_API_KEY=" "$ENV_FILE" | cut -d'=' -f2-)
                printf "\n"
                verify_api_key_with_openai "$current_key"
                ;;
            3)
                printf "\n${YELLOW}正在更新 API 金鑰...${NC}\n"
                rm -f "$ENV_FILE"
                if prompt_for_api_key; then
                    printf "${GREEN}API 金鑰已更新。請重新啟動 Backend 以套用變更。${NC}\n"
                fi
                ;;
            4)
                printf "\n${RED}確定要刪除 API 金鑰嗎？(y/N): ${NC}"
                read -r confirm
                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    rm -f "$ENV_FILE"
                    printf "${GREEN}API 金鑰已刪除。${NC}\n"
                else
                    printf "${YELLOW}已取消。${NC}\n"
                fi
                ;;
            5|*)
                printf "${YELLOW}返回主選單。${NC}\n"
                ;;
        esac
    else
        printf "${RED}❌ 尚未設定 API 金鑰${NC}\n\n"
        printf "${YELLOW}是否要現在設定？(y/N): ${NC}"
        read -r confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            prompt_for_api_key
        fi
    fi
    printf "\n"
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
        apikey)
            manage_api_key
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
