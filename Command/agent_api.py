from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import subprocess
import asyncio

app = FastAPI(title="Agent Factory API")

# Allow CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
COMMAND_DIR = "/home/imnyj/Command"
CORE_DIR = os.path.join(COMMAND_DIR, "core")

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    dashboard_path = os.path.join(COMMAND_DIR, "agent_dashboard.html")
    with open(dashboard_path, "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html, headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"})



import glob
import datetime

import re


def get_session_info(session_id):
    brain_dir = os.path.expanduser("~/.gemini/antigravity-cli/brain")
    child_to_parent, _ = get_subagent_relations()
    
    is_main = session_id not in child_to_parent
    
    title = "unknown"
    title_file = os.path.join(brain_dir, session_id, ".title")
    if os.path.exists(title_file):
        try:
            with open(title_file, "r", encoding="utf-8") as f:
                title = f.read().strip()
        except:
            pass
            
    if is_main:
        return True, title, title
    else:
        parent_id = child_to_parent[session_id]
        while parent_id in child_to_parent:
            parent_id = child_to_parent[parent_id]
            
        parent_title = "unknown"
        parent_title_file = os.path.join(brain_dir, parent_id, ".title")
        if os.path.exists(parent_title_file):
            try:
                with open(parent_title_file, "r", encoding="utf-8") as f:
                    parent_title = f.read().strip()
            except:
                pass
        return False, parent_title, title

def ensure_session_workspace(session_id, session_title):
    import shutil
    import uuid
    workspace_root = "/home/imnyj/Workspace"
    os.makedirs(workspace_root, exist_ok=True)
    
    session_title_safe = "".join([c for c in session_title if c.isalpha() or c.isdigit() or c in ' _-']).strip()
    if not session_title_safe:
        session_title_safe = session_id[:8]
        
    session_workspace = os.path.join(workspace_root, session_title_safe)
    os.makedirs(session_workspace, exist_ok=True)
    
    agents_list = ["idea", "librarian", "coder", "visualizer", "writer", "critic", "worker"]
    for agent_role in agents_list:
        agent_dir = os.path.join(session_workspace, agent_role)
        os.makedirs(agent_dir, exist_ok=True)
        os.makedirs(os.path.join(agent_dir, "backup"), exist_ok=True)
        
    rules_dir = os.path.join(session_workspace, ".rules")
    os.makedirs(rules_dir, exist_ok=True)
    
    for agent_role in agents_list:
        rule_dest = os.path.join(rules_dir, f"{agent_role}.md")
        if not os.path.exists(rule_dest):
            rule_src = f"/home/imnyj/Command/rules/{agent_role}.md"
            if os.path.exists(rule_src):
                shutil.copy2(rule_src, rule_dest)
                
    # --- Agent Factory: Create and Register Sub-Agents ---
    brain_dir = os.path.expanduser("~/.gemini/antigravity-cli/brain")
    agents_meta_dir = os.path.join(brain_dir, session_id, ".agents")
    os.makedirs(agents_meta_dir, exist_ok=True)
    
    registry_file = os.path.join(agents_meta_dir, "registry.json")
    if not os.path.exists(registry_file):
        agents_map = {}
        for role in agents_list:
            child_uuid = str(uuid.uuid4())
            agents_map[role] = child_uuid
            
            # Create sub-agent session directory
            child_dir = os.path.join(brain_dir, child_uuid)
            os.makedirs(child_dir, exist_ok=True)
            
            # Store agent role in .title file
            title_path = os.path.join(child_dir, ".title")
            with open(title_path, "w", encoding="utf-8") as tf:
                tf.write(role)
                
        registry_data = {
            "session_id": session_id,
            "agents": agents_map
        }
        with open(registry_file, "w", encoding="utf-8") as rf:
            json.dump(registry_data, rf, indent=2)
            
    return session_workspace

# --- Projects DB Logic ---
def get_subagent_relations():
    import re
    brain_dir = os.path.expanduser("~/.gemini/antigravity-cli/brain")
    child_to_parent = {}
    parent_to_children = {}
    if not os.path.exists(brain_dir):
        return child_to_parent, parent_to_children
        
    # 1. Load relationships from agent factory registry.json
    for session_id in os.listdir(brain_dir):
        registry_path = os.path.join(brain_dir, session_id, ".agents", "registry.json")
        if os.path.exists(registry_path):
            try:
                with open(registry_path, "r", encoding="utf-8") as f:
                    reg_data = json.load(f)
                agents_map = reg_data.get("agents", {})
                for role, child_id in agents_map.items():
                    child_to_parent[child_id] = session_id
                    if session_id not in parent_to_children:
                        parent_to_children[session_id] = []
                    if child_id not in parent_to_children[session_id]:
                        parent_to_children[session_id].append(child_id)
            except Exception:
                pass

    # 2. Load relationships from transcript.jsonl (dynamic subagents)
    for session_id in os.listdir(brain_dir):
        transcript_path = os.path.join(brain_dir, session_id, ".system_generated", "logs", "transcript.jsonl")
        if os.path.exists(transcript_path):
            try:
                with open(transcript_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if "sender=" in line and "MESSAGE_PRIORITY_" in line:
                            data = json.loads(line.strip())
                            if data.get("type") == "SYSTEM_MESSAGE":
                                content = data.get("content", "")
                                m = re.search(r"sender=([a-f0-9\-]{36})", content)
                                if m:
                                    child_id = m.group(1)
                                    if child_id != session_id:
                                        child_to_parent[child_id] = session_id
                                        if session_id not in parent_to_children:
                                            parent_to_children[session_id] = []
                                        if child_id not in parent_to_children[session_id]:
                                            parent_to_children[session_id].append(child_id)
            except Exception:
                pass
    return child_to_parent, parent_to_children

def load_real_sessions():
    brain_dir = os.path.expanduser("~/.gemini/antigravity-cli/brain")
    sessions = []
    
    if not os.path.exists(brain_dir):
        return sessions
        
    title_map = {}
    
    # 1. 시스템 프롬프트(CONVERSATION_HISTORY)에서 이름(rename된 이름 포함)을 추출
    for session_id in os.listdir(brain_dir):
        transcript_path = os.path.join(brain_dir, session_id, ".system_generated", "logs", "transcript.jsonl")
        if os.path.exists(transcript_path):
            try:
                with open(transcript_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if "CONVERSATION_HISTORY" in line:
                            data = json.loads(line.strip())
                            if data.get("type") == "CONVERSATION_HISTORY":
                                content = data.get("content", "")
                                matches = re.findall(r"## Conversation ([a-f0-9\-]+): (.*)", content)
                                for match in matches:
                                    title_map[match[0]] = match[1].strip()
            except Exception:
                pass

    child_to_parent, _ = get_subagent_relations()

    # 2. 실제 세션 폴더 조회
    for session_id in os.listdir(brain_dir):
        session_path = os.path.join(brain_dir, session_id)
        if not os.path.isdir(session_path) or session_id == "shared" or session_id in child_to_parent:
            continue
            
        title = None
        title_file = os.path.join(session_path, ".title")
        if os.path.exists(title_file):
            try:
                with open(title_file, "r", encoding="utf-8") as f:
                    title = f.read().strip()
            except Exception:
                pass
                
        if not title:
            title = title_map.get(session_id)
        
        # 이름이 맵핑되지 않았다면 첫 번째 사용자의 프롬프트를 파싱 (XML 태그 제거)
        if not title:
            transcript_path = os.path.join(session_path, ".system_generated", "logs", "transcript.jsonl")
            if os.path.exists(transcript_path):
                try:
                    with open(transcript_path, "r", encoding="utf-8") as f:
                        for line in f:
                            data = json.loads(line.strip())
                            if data.get("type") == "USER_INPUT":
                                content = data.get("content", "")
                                if "<USER_REQUEST>" in content:
                                    m = re.search(r"<USER_REQUEST>\n?(.*?)\n?</USER_REQUEST>", content, re.DOTALL)
                                    if m:
                                        title = m.group(1).strip().split('\n')[0][:30]
                                        break
                                elif content:
                                    title = content.split('\n')[0][:30]
                                    break
                except Exception:
                    pass
                    
        if not title:
            title = session_id[:8]
            
        mtime = os.path.getmtime(session_path)
        dt = datetime.datetime.fromtimestamp(mtime)
        
        ensure_session_workspace(session_id, title)
        sessions.append({
            "id": session_id,
            "title": title,
            "status": "로컬 세션",
            "last_updated": dt.strftime("%Y-%m-%d %H:%M"),
            "mtime": mtime
        })
        
    sessions.sort(key=lambda x: x["mtime"], reverse=True)
    return sessions

@app.get("/api/projects")
async def get_projects():
    projects = load_real_sessions()
    return {"status": "success", "projects": projects}

@app.post("/api/projects")
async def create_project(request: Request):
    # 실제 환경에서는 `antigravity-cli --new` 같은 명령어로 새 폴더를 생성해야 합니다.
    # 지금은 읽기 전용 상태로 응답만 합니다.
    return {"status": "error", "message": "웹에서 직접 세션을 생성하는 것은 아직 지원되지 않습니다."}

@app.get("/api/sessions/{session_id}")
async def get_session_history(session_id: str):
    brain_dir = os.path.expanduser("~/.gemini/antigravity-cli/brain")
    transcript_path = os.path.join(brain_dir, session_id, ".system_generated", "logs", "transcript.jsonl")
    
    history = []
    if os.path.exists(transcript_path):
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    msg_type = data.get("type")
                    if msg_type == "USER_INPUT":
                        content = data.get("content", "")
                        # Remove <USER_REQUEST> tags if present
                        if "<USER_REQUEST>" in content:
                            m = re.search(r"<USER_REQUEST>\n?(.*?)\n?</USER_REQUEST>", content, re.DOTALL)
                            if m: content = m.group(1).strip()
                        history.append({"role": "user", "content": content})
                    elif msg_type == "PLANNER_RESPONSE":
                        content = data.get("content", "")
                        if content:
                            history.append({"role": "agent", "content": content})
                except Exception:
                    pass
    return {"status": "success", "history": history}

import uuid

workspace_data = {}

@app.get("/api/workspace/{session_id}/details")
async def get_workspace_details(session_id: str):
    _, parent_to_children = get_subagent_relations()
    children = parent_to_children.get(session_id, [])
    
    session_title = "메인 대화 세션"
    title_file = os.path.join(os.path.expanduser("~/.gemini/antigravity-cli/brain"), session_id, ".title")
    if os.path.exists(title_file):
        try:
            with open(title_file, "r", encoding="utf-8") as f:
                session_title = f.read().strip()
        except:
            pass
            
    ensure_session_workspace(session_id, session_title)
    if session_id not in workspace_data:
        workspace_data[session_id] = {
            "topic_sessions": {
                "manager": [
                    {"id": session_id, "title": session_title, "status": "메인 주제"}
                ]
            }
        }
        
    topic_sessions = workspace_data[session_id]["topic_sessions"]
            
    agents = [
        {"id": "manager", "name": "👑 최상위 매니저 (Top-Level)", "is_root": True, "parent_id": None, "depth": 0}
    ]
    
    def collect_descendants(current_parent_id, depth):
        children_list = parent_to_children.get(current_parent_id, [])
        for child_id in children_list:
            child_title = f"하위 작업 ({child_id[:8]})"
            child_title_file = os.path.join(os.path.expanduser("~/.gemini/antigravity-cli/brain"), child_id, ".title")
            if os.path.exists(child_title_file):
                try:
                    with open(child_title_file, "r", encoding="utf-8") as f:
                        child_title = f.read().strip()
                except:
                    pass
                    
            p_id = "manager" if current_parent_id == session_id else current_parent_id
            
            # 뎁스에 따른 들여쓰기 기호 추가
            prefix = "└ " if depth > 1 else ""
            
            agents.append({
                "id": child_id,
                "name": f"🤖 {prefix}{child_title}",
                "is_root": False,
                "parent_id": p_id,
                "depth": depth
            })
            
            if child_id not in topic_sessions:
                topic_sessions[child_id] = [
                    {"id": child_id, "title": "메인 주제", "status": "진행 중"}
                ]
                
            collect_descendants(child_id, depth + 1)
            
    collect_descendants(session_id, 1)
        
    return {
        "status": "success",
        "title": session_title,
        "agents": agents,
        "topic_sessions": topic_sessions
    }

@app.post("/api/workspace/{session_id}/topics")
async def create_topic_session(session_id: str, request: Request):
    data = await request.json()
    agent_id = data.get("agent_id", "manager")
    title = data.get("title", "새 주제")
    
    # 36 character UUID with 't' prefix to indicate topic session and avoid conflicts
    new_sub_id = f"t{uuid.uuid4().hex[:35]}"
    
    if session_id in workspace_data:
        if agent_id not in workspace_data[session_id]["topic_sessions"]:
            workspace_data[session_id]["topic_sessions"][agent_id] = []
        workspace_data[session_id]["topic_sessions"][agent_id].append({
            "id": new_sub_id,
            "title": title,
            "status": "새 주제"
        })
        
    return {"status": "success", "topic_id": new_sub_id}

@app.post("/api/workspace/{session_id}/agents")
async def create_agent(session_id: str, request: Request):
    data = await request.json()
    
    # GEMINI.md (절대 룰) 주입
    base_prompt = data.get("system_prompt", "")
    gemini_rules = ""
    try:
        with open("/home/imnyj/GEMINI.md", "r", encoding="utf-8") as f:
            gemini_rules = f.read()
    except Exception:
        pass
        
    final_prompt = f"{base_prompt}\n\n[CRITICAL SYSTEM RULES (GEMINI.md)]\n{gemini_rules}"
    
    new_agent = {
        "id": "agent_" + str(uuid.uuid4())[:8],
        "name": "🤖 " + data.get("name", "새 에이전트"),
        "is_root": False,
        "parent_id": "manager",
        "system_prompt": final_prompt
    }
    if session_id in workspace_data:
        workspace_data[session_id]["agents"].append(new_agent)
    return {"status": "success", "agent": new_agent}

@app.websocket("/ws/sessions/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            prompt = payload.get("prompt", "")
            agent_role = payload.get("agent_role", "manager")
            import shlex
            
            # 주제별 세션(topic session)인 경우, 부모 에이전트의 설정(.agents 폴더)을 복사해와야 합니다.
            # 그래야 동일한 시스템 프롬프트(manager, worker 등)와 도구를 상속받습니다.
            if session_id.startswith("t"):
                parent_agent_id = None
                for proj_id, proj_data in workspace_data.items():
                    if "topic_sessions" in proj_data:
                        for ag_id, topics in proj_data["topic_sessions"].items():
                            for t in topics:
                                if t["id"] == session_id:
                                    parent_agent_id = proj_id if ag_id == "manager" else ag_id
                                    break
                            if parent_agent_id: break
                    if parent_agent_id: break
                
                if parent_agent_id and parent_agent_id != session_id:
                    brain_dir = os.path.expanduser("~/.gemini/antigravity-cli/brain")
                    target_dir = os.path.join(brain_dir, session_id)
                    target_agents_dir = os.path.join(target_dir, ".agents")
                    
                    if not os.path.exists(target_agents_dir):
                        source_agents_dir = os.path.join(brain_dir, parent_agent_id, ".agents")
                        if os.path.exists(source_agents_dir):
                            import shutil
                            os.makedirs(target_dir, exist_ok=True)
                            shutil.copytree(source_agents_dir, target_agents_dir)
            
            is_main, project_name, role = get_session_info(session_id)
            cmd_options = "--sandbox --dangerously-skip-permissions" if is_main else "--dangerously-skip-permissions"
            
            final_prompt = prompt
            if not is_main:
                rules_path = f"/home/imnyj/Workspace/{project_name}/.rules/{role}.md"
                if os.path.exists(rules_path):
                    try:
                        with open(rules_path, "r", encoding="utf-8") as rf:
                            rules_content = rf.read()
                        final_prompt = f"[SYSTEM RULES (DO NOT VIOLATE)]\n{rules_content}\n\n[USER COMMAND]\n{prompt}"
                    except:
                        pass

            # 실제 CLI 호출 명령어 구성
            cmd = f"/home/imnyj/.local/bin/agy {cmd_options} --conversation {shlex.quote(session_id)} --prompt {shlex.quote(final_prompt)}"
            
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            
            await websocket.send_text(json.dumps({"type": "start", "cmd": cmd}))
            
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                text_chunk = line.decode('utf-8')
                await websocket.send_text(json.dumps({"type": "stream", "chunk": text_chunk}))
                
            await process.wait()
            await websocket.send_text(json.dumps({"type": "end"}))
            
    except WebSocketDisconnect:
        pass

@app.post("/api/sessions/{session_id}/rename")
async def rename_session(session_id: str, request: Request):
    data = await request.json()
    new_name = data.get("title") or data.get("name")
    if new_name:
        brain_dir = "/home/imnyj/.gemini/antigravity-cli/brain"
        title_file = os.path.join(brain_dir, session_id, ".title")
        try:
            old_name = None
            if os.path.exists(title_file):
                with open(title_file, "r", encoding="utf-8") as f:
                    old_name = f.read().strip()
            
            with open(title_file, "w", encoding="utf-8") as f:
                f.write(new_name)
                
            if old_name:
                workspace_root = "/home/imnyj/Workspace"
                old_dir = os.path.join(workspace_root, old_name)
                new_dir = os.path.join(workspace_root, new_name)
                if os.path.exists(old_dir) and not os.path.exists(new_dir):
                    os.rename(old_dir, new_dir)
            
            ensure_session_workspace(session_id, new_name)

            if session_id in workspace_data:
                workspace_data[session_id]["title"] = new_name
            return {"status": "success", "title": new_name}
        except Exception as e:
            return {"status": "error", "message": f"파일 저장 오류: {str(e)}"}
    return {"status": "error", "message": "새로운 이름이 제공되지 않았습니다."}

@app.post("/api/sessions/{session_id}/message")
async def send_session_message(session_id: str, request: Request):
    data = await request.json()
    prompt = data.get("prompt", "")
    target_agent = data.get("agent_role", "manager")
    
    # 실제로는 `antigravity-cli resume {session_id} --prompt '{prompt}'` 등을 백그라운드로 실행해야 함.
    # 현재는 PoC 수준이므로 subprocess로 호출했다고 가정하고 더미 응답을 반환합니다.
    # 추후 WebSocket이나 백그라운드 태스크 큐로 연동해야 합니다.
    
    cmd = f"antigravity-cli resume {session_id} --agent {target_agent} --prompt '{prompt}'"
    
    try:
        # 비동기로 CLI 호출 시도 (명령어가 없을 경우 대비)
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        # Timeout 방지를 위해 1초만 기다리거나 바로 백그라운드로 넘깁니다. (여기서는 시뮬레이션)
        # 실제로는 응답을 스트리밍해야 합니다.
        
        return {
            "status": "success", 
            "response_msg": f"에이전트에게 메시지를 전송했습니다. (내부 실행: {cmd}) \n\n*참고: 실제 답변을 기다리는 웹소켓 스트리밍은 다음 단계에서 구현됩니다.*"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/agent/command")
async def send_agent_command(request: Request):
    data = await request.json()
    target_agent = data.get("agent_role", "manager")
    command = data.get("command", "")
    
    # 1. 포맷팅: 특정 에이전트를 지정하여 명령을 전달하는 프롬프트 구성
    cli_command = f"antigravity-cli --agent {target_agent} --prompt '{command}'"
    
    try:
        # 2. 비동기 Subprocess로 로컬 에이전트(CLI) 실제 호출
        process = await asyncio.create_subprocess_shell(
            cli_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            # 성공 시 CLI 출력 결과를 웹 화면으로 반환
            response_msg = stdout.decode('utf-8').strip()
            if not response_msg:
                response_msg = f"[{target_agent.upper()}] 작업이 백그라운드에서 성공적으로 위임되었습니다."
        else:
            # 실패 시 에러 반환
            error_msg = stderr.decode('utf-8').strip()
            response_msg = f"[오류 발생] {target_agent} 호출 실패: {error_msg}"
            
    except Exception as e:
        response_msg = f"[시스템 오류] CLI 연결 실패: {str(e)}"
    
    return {"status": "success", "response": response_msg}

if __name__ == "__main__":
    import uvicorn
    # To run: python agent_api.py
    uvicorn.run(app, host="0.0.0.0", port=8000)
