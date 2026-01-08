"""
Process Management Router
==========================

API endpoints for viewing and managing all agent processes.
"""

import psutil
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/processes", tags=["processes"])


class ProcessInfo(BaseModel):
    """Information about a running process."""
    pid: int
    name: str
    cmdline: str
    project_dir: Optional[str] = None
    cpu_percent: float
    memory_mb: float
    status: str
    create_time: float


class ProcessListResponse(BaseModel):
    """Response containing list of processes."""
    processes: List[ProcessInfo]
    total: int


class KillProcessRequest(BaseModel):
    """Request to kill a process."""
    pid: int


class KillProcessResponse(BaseModel):
    """Response after killing a process."""
    success: bool
    message: str
    pid: int


def is_agent_process(proc: psutil.Process) -> bool:
    """Check if a process is an agent process."""
    try:
        cmdline = ' '.join(proc.cmdline())

        # Check for autonomous_agent_demo
        if 'autonomous_agent_demo' in cmdline:
            return True

        # Check for Claude SDK processes
        if 'claude' in cmdline and '--output-format' in cmdline and 'stream-json' in cmdline:
            return True

        # Check for Python processes running agent.py
        if 'python' in cmdline and 'agent.py' in cmdline:
            return True

        return False
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def extract_project_dir(cmdline: str) -> Optional[str]:
    """Extract project directory from command line."""
    try:
        # Look for PROJECT_DIR env var
        if 'PROJECT_DIR=' in cmdline:
            start = cmdline.index('PROJECT_DIR=') + len('PROJECT_DIR=')
            end = cmdline.find(',', start)
            if end == -1:
                end = cmdline.find('"', start)
            if end == -1:
                end = len(cmdline)
            project_dir = cmdline[start:end].strip('\'"')
            return project_dir

        # Look for --project-dir argument
        if '--project-dir' in cmdline:
            parts = cmdline.split('--project-dir')
            if len(parts) > 1:
                after = parts[1].strip().split()[0]
                return after.strip('\'"')

        return None
    except Exception:
        return None


@router.get("", response_model=ProcessListResponse)
async def list_processes():
    """List all running agent processes."""
    processes = []

    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info', 'status', 'create_time']):
        try:
            if is_agent_process(proc):
                cmdline_list = proc.info.get('cmdline', [])
                cmdline = ' '.join(cmdline_list) if cmdline_list else ''

                # Truncate very long command lines
                if len(cmdline) > 200:
                    cmdline = cmdline[:200] + '...'

                memory_mb = proc.info['memory_info'].rss / (1024 * 1024) if proc.info.get('memory_info') else 0

                process_info = ProcessInfo(
                    pid=proc.info['pid'],
                    name=proc.info['name'],
                    cmdline=cmdline,
                    project_dir=extract_project_dir(' '.join(cmdline_list)),
                    cpu_percent=proc.info.get('cpu_percent', 0) or 0,
                    memory_mb=round(memory_mb, 2),
                    status=proc.info.get('status', 'unknown'),
                    create_time=proc.info.get('create_time', 0)
                )
                processes.append(process_info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Sort by create_time (newest first)
    processes.sort(key=lambda p: p.create_time, reverse=True)

    return ProcessListResponse(
        processes=processes,
        total=len(processes)
    )


@router.post("/kill", response_model=KillProcessResponse)
async def kill_process(request: KillProcessRequest):
    """Kill a specific process by PID."""
    try:
        proc = psutil.Process(request.pid)

        # Verify it's an agent process before killing
        if not is_agent_process(proc):
            raise HTTPException(
                status_code=403,
                detail=f"Process {request.pid} is not an agent process"
            )

        # Kill the process and all its children
        try:
            # First try to get children
            children = proc.children(recursive=True)

            # Kill children first
            for child in children:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass

            # Kill the parent
            proc.kill()

            # Wait for termination
            proc.wait(timeout=3)

            return KillProcessResponse(
                success=True,
                message=f"Process {request.pid} killed successfully",
                pid=request.pid
            )
        except psutil.TimeoutExpired:
            return KillProcessResponse(
                success=True,
                message=f"Process {request.pid} kill signal sent (timeout waiting for termination)",
                pid=request.pid
            )
    except psutil.NoSuchProcess:
        raise HTTPException(
            status_code=404,
            detail=f"Process {request.pid} not found"
        )
    except psutil.AccessDenied:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied to kill process {request.pid}"
        )
    except Exception as e:
        logger.error(f"Error killing process {request.pid}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error killing process: {str(e)}"
        )


@router.post("/kill-all", response_model=dict)
async def kill_all_processes():
    """Kill all agent processes."""
    killed = []
    failed = []

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if is_agent_process(proc):
                pid = proc.info['pid']
                try:
                    # Kill children first
                    children = proc.children(recursive=True)
                    for child in children:
                        try:
                            child.kill()
                        except psutil.NoSuchProcess:
                            pass

                    # Kill the parent
                    proc.kill()
                    killed.append(pid)
                except Exception as e:
                    failed.append({
                        'pid': pid,
                        'error': str(e)
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return {
        'success': len(failed) == 0,
        'killed': killed,
        'failed': failed,
        'total_killed': len(killed),
        'total_failed': len(failed)
    }
