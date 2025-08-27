import os
import asyncio
import aiofiles.os
import shutil
import json
import aiosqlite
from fastapi import FastAPI, Request, Depends, HTTPException, status, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel

# --- Pydantic Models for Request Bodies ---
class PathRequest(BaseModel):
    path: str = ''
class CreateFolderRequest(PathRequest):
    foldername: str
class CreateFileRequest(PathRequest):
    filename: str
class DeleteRequest(PathRequest):
    filename: str
class SaveRequest(BaseModel):
    filename: str
    content: str

# --- Basic Setup ---
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
app = FastAPI()
templates = Jinja2Templates(directory=template_dir)

# --- Middleware ---
app.add_middleware(SessionMiddleware, secret_key=os.getenv("decryption_key"))

# --- Main Homepage Route ---
@app.get("/", response_class=HTMLResponse, name="home")
async def home(request: Request):
    """Serves the main landing page, which you've set as 404.html."""
    return templates.TemplateResponse("404.html", {"request": request}, status_code=200)


@app.get("/status", status_code=status.HTTP_200_OK)
@app.head("/status", status_code=status.HTTP_200_OK)
async def health_status(request: Request):
    """A simple health check endpoint for uptime monitoring, supports GET and HEAD."""
    return {"status": "ok"}




#panel for admin
@app.get("/admin", response_class=HTMLResponse, name="admin")
async def admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request}, status_code=200)



# --- Authentication ---
users = {'admin': {'password': os.getenv("MDB_pass_shadow")}}

async def get_current_user(request: Request):
    return request.session.get("user")

@app.get("/login", response_class=HTMLResponse, name="login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def handle_login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username in users and users[username]['password'] == password:
        request.session["user"] = {"username": username}
        return RedirectResponse(url=request.url_for('files_root'), status_code=status.HTTP_303_SEE_OTHER)
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"}, status_code=401)

@app.get("/logout", name="logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url=request.url_for('login'))

# --- File Write/Modification Routes ---
@app.post('/create_folder')
async def create_folder(req: CreateFolderRequest, user: dict = Depends(get_current_user)):
    if not user: raise HTTPException(status_code=403)
    full_path = os.path.abspath(os.path.join(base_dir, req.path, req.foldername))
    if not full_path.startswith(base_dir):
        return JSONResponse({"error": "Invalid path"}, status_code=400)
    try:
        await aiofiles.os.makedirs(full_path)
        return JSONResponse({"message": "Folder created successfully"}, status_code=200)
    except FileExistsError:
        return JSONResponse({"error": "Folder already exists"}, status_code=409)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post('/create_file')
async def create_file(req: CreateFileRequest, user: dict = Depends(get_current_user)):
    if not user: raise HTTPException(status_code=403)
    full_path = os.path.abspath(os.path.join(base_dir, req.path, req.filename))
    if not full_path.startswith(base_dir):
        return JSONResponse({"error": "Invalid path"}, status_code=400)
    if await aiofiles.os.path.exists(full_path):
        return JSONResponse({"error": "File already exists"}, status_code=409)
    try:
        async with aiofiles.open(full_path, 'w') as f:
            await f.write('')
        return JSONResponse({"message": "File created"}, status_code=201)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post('/save')
async def save_file(req: SaveRequest, user: dict = Depends(get_current_user)):
    if not user: raise HTTPException(status_code=403)
    abs_path = os.path.abspath(os.path.join(base_dir, req.filename))
    if not abs_path.startswith(base_dir):
        return JSONResponse({"success": False, "message": "Invalid file path"}, status_code=403)
    try:
        async with aiofiles.open(abs_path, 'w', encoding='utf-8') as f:
            await f.write(req.content)
        return JSONResponse({"success": True, "message": "File saved successfully."})
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

@app.post('/delete_file')
async def delete_file(req: DeleteRequest, user: dict = Depends(get_current_user)):
    if not user: raise HTTPException(status_code=403)
    target_path = os.path.abspath(os.path.join(base_dir, req.path, req.filename))
    if not target_path.startswith(base_dir):
        return JSONResponse({"error": "Invalid file path"}, status_code=400)
    try:
        if await aiofiles.os.path.isdir(target_path):
            await asyncio.to_thread(shutil.rmtree, target_path)
        elif await aiofiles.os.path.isfile(target_path):
            await aiofiles.os.remove(target_path)
        else:
            return JSONResponse({"error": "File or directory not found"}, status_code=404)
        return JSONResponse({"message": "Deleted successfully"}, status_code=200)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post('/upload_file')
async def upload_file(path: str = Form(''), file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if not user: raise HTTPException(status_code=403)
    full_dir_path = os.path.abspath(os.path.join(base_dir, path.strip('/')))
    if not full_dir_path.startswith(base_dir):
        return JSONResponse({'error': 'Invalid upload path'}, status_code=400)
    
    filepath = os.path.join(full_dir_path, os.path.basename(file.filename))
    try:
        async with aiofiles.open(filepath, 'wb') as f:
            while content := await file.read(1024 * 1024):
                await f.write(content)
        return JSONResponse({'message': 'File uploaded successfully'}, status_code=200)
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)

# --- File Read/View Routes ---
@app.get('/view/{filepath:path}', name='view_file', response_class=HTMLResponse)
async def view_file(request: Request, filepath: str, user: dict = Depends(get_current_user)):
    if not user: return RedirectResponse(url=request.url_for('login'))
    full_path = os.path.abspath(os.path.join(base_dir, filepath))
    if not full_path.startswith(base_dir) or not await aiofiles.os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    content = ""
    file_extension = (os.path.splitext(filepath)[1] or "").lower()
    
    if file_extension == '.db':
        try:
            db_data = []
            async with aiosqlite.connect(full_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT name FROM sqlite_master WHERE type='table';") as cursor:
                    tables = [row[0] for row in await cursor.fetchall()]
                for table_name in tables:
                    async with db.execute(f"PRAGMA table_info({table_name});") as cursor:
                        columns = [row['name'] for row in await cursor.fetchall()]
                    async with db.execute(f"SELECT * FROM {table_name}") as cursor:
                        rows = [dict(row) for row in await cursor.fetchall()]
                    db_data.append({"name": table_name, "columns": columns, "rows": rows})
            content = json.dumps(db_data)
        except Exception as e:
            content = f"Error reading database: {e}"
    elif file_extension in ['.png', '.jpg', '.jpeg', '.gif', '.svg']:
        pass
    else:
        try:
            async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
                content = await f.read()
        except UnicodeDecodeError:
            content = "Cannot display file: Content is not valid UTF-8 text."
    return templates.TemplateResponse('viewer.html', {"request": request, "filename": filepath, "content": content, "user": user})

@app.get('/edit/{filename:path}', name='edit_file', response_class=HTMLResponse)
async def edit_file(request: Request, filename: str, user: dict = Depends(get_current_user)):
    if not user: return RedirectResponse(url=request.url_for('login'))
    abs_path = os.path.abspath(os.path.join(base_dir, filename))
    if not abs_path.startswith(base_dir) or not await aiofiles.os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        async with aiofiles.open(abs_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        return templates.TemplateResponse("editor.html", {"request": request, "filename": filename, "content": content, "user": user})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {e}")

@app.get('/raw_file/{filepath:path}', name='raw_file')
async def serve_raw_file(filepath: str, user: dict = Depends(get_current_user)):
    if not user: raise HTTPException(status_code=403)
    full_path = os.path.abspath(os.path.join(base_dir, filepath))
    if not full_path.startswith(base_dir) or not os.path.exists(full_path):
        raise HTTPException(status_code=404)
    return FileResponse(full_path)

@app.get('/download/{filepath:path}', name='download_file')
async def download_file(filepath: str, user: dict = Depends(get_current_user)):
    if not user: raise HTTPException(status_code=403)
    full_path = os.path.abspath(os.path.join(base_dir, filepath))
    if not full_path.startswith(base_dir) or not os.path.exists(full_path):
        raise HTTPException(status_code=404)
    return FileResponse(full_path, media_type='application/octet-stream', filename=os.path.basename(filepath))

# --- API Routes ---
async def async_get_file_structure(root_path):
    ignore_list = {'.git', '__pycache__', 'node_modules', '.vscode'}
    # Use a list to hold children found in this level
    children = []
    try:
        # Use asyncio.to_thread for the blocking os.listdir
        items = await asyncio.to_thread(os.listdir, root_path)
        for item_name in items:
            if item_name in ignore_list:
                continue
            path = os.path.join(root_path, item_name)
            try:
                # Use aiofiles.os.path.isdir for non-blocking check
                if await aiofiles.os.path.isdir(path):
                    # Recursively call and append the result
                    children.append({
                        'type': 'folder',
                        'name': item_name,
                        'children': await async_get_file_structure(path)
                    })
                else:
                    children.append({'type': 'file', 'name': item_name})
            except Exception:
                # Ignore files/folders that can't be accessed
                continue
    except Exception:
        # Ignore directories that can't be listed
        pass
    return children

@app.get('/api/files', name='api_files')
async def api_files(user: dict = Depends(get_current_user)):
    if not user: raise HTTPException(status_code=403)
    structure = await async_get_file_structure(base_dir)
    return JSONResponse(structure)

# --- Main File Browser Route ---
@app.get("/files/{req_path:path}", response_class=HTMLResponse)
@app.get("/files", response_class=HTMLResponse, name="files_root")
async def files(request: Request, req_path: str = "", user: dict = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url=request.url_for('login'), status_code=status.HTTP_302_FOUND)

    abs_path = os.path.abspath(os.path.join(base_dir, req_path))
    if not abs_path.startswith(base_dir):
        raise HTTPException(status_code=403, detail="Access Denied 🛑")

    if not os.path.isdir(abs_path):
        return RedirectResponse(url=request.url_for('view_file', filepath=req_path))

    try:
        files_list = await asyncio.to_thread(os.listdir, abs_path)

        async def get_file_info(filename):
            full_path = os.path.join(abs_path, filename)
            try:
                stat_result = await aiofiles.os.stat(full_path)
                is_dir = os.path.isdir(full_path)
                return {"name": filename, "is_dir": is_dir, "size": stat_result.st_size if not is_dir else None}
            except OSError:
                return None

        tasks = [get_file_info(f) for f in files_list]
        results = await asyncio.gather(*tasks)
        file_infos = sorted([r for r in results if r], key=lambda f: (not f['is_dir'], f['name'].lower()))
        parent_path = os.path.dirname(req_path) if req_path else ''
        
        return templates.TemplateResponse("files.html", {
            "request": request,
            "files": file_infos,
            "current_path": req_path,
            "parent_path": parent_path,
            "user": user
        })
    except Exception as e:
        print(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail="Error loading files")