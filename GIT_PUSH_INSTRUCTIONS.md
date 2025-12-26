# Hướng Dẫn Push Lên GitHub

## ✅ Đã Hoàn Thành

- ✅ Khởi tạo Git repository
- ✅ Tạo `.gitignore` file
- ✅ Staged 61 files (39,491 dòng code)
- ✅ Tạo commit với message chi tiết

**Commit hash**: `fe5b039`

## Bước Tiếp Theo: Push Lên GitHub

### Option 1: Push Lên Repository Mới

#### 1. Tạo Repository Trên GitHub

Truy cập: https://github.com/new

- **Repository name**: `vnpt-money-chatbot` (hoặc tên bạn muốn)
- **Description**: "GraphRAG Chatbot for VNPT Money with Neo4j Knowledge Graph"
- **Visibility**: Private (recommended) hoặc Public
- **KHÔNG** chọn "Initialize with README" (đã có rồi)

#### 2. Copy Remote URL

Sau khi tạo, GitHub sẽ cho URL dạng:
```
https://github.com/YOUR_USERNAME/vnpt-money-chatbot.git
```

#### 3. Add Remote và Push

```bash
cd "c:\Users\GIANG\OneDrive - Hanoi University of Science and Technology\Documents\VNPT_Media_Software\Chatbot"

# Add remote
git remote add origin https://github.com/YOUR_USERNAME/vnpt-money-chatbot.git

# Push lần đầu
git push -u origin master
```

Hoặc nếu GitHub repo dùng `main` branch:

```bash
# Rename branch
git branch -M main

# Push
git push -u origin main
```

### Option 2: Push Lên Repository Có Sẵn

Nếu đã có repository:

```bash
cd "c:\Users\GIANG\OneDrive - Hanoi University of Science and Technology\Documents\VNPT_Media_Software\Chatbot"

# Add remote
git remote add origin https://github.com/YOUR_USERNAME/existing-repo.git

# Pull trước (nếu repo không trống)
git pull origin main --allow-unrelated-histories

# Push
git push -u origin main
```

## Xác Thực GitHub

### Nếu dùng HTTPS:

Bạn sẽ được hỏi username và password. **LƯU Ý**: GitHub không còn hỗ trợ password, cần dùng **Personal Access Token**.

#### Tạo Personal Access Token:

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token (classic)"
3. Chọn scopes: `repo` (full control)
4. Copy token (chỉ hiện 1 lần!)

#### Khi push, nhập:
- Username: `your_github_username`
- Password: `ghp_xxxxxxxxxxxxx` (Personal Access Token)

### Nếu dùng SSH:

```bash
# Generate SSH key (nếu chưa có)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy public key
cat ~/.ssh/id_ed25519.pub

# Add vào GitHub: Settings → SSH and GPG keys → New SSH key

# Đổi remote sang SSH
git remote set-url origin git@github.com:YOUR_USERNAME/vnpt-money-chatbot.git

# Push
git push -u origin main
```

## Sau Khi Push Thành Công

### 1. Verify trên GitHub

Truy cập: `https://github.com/YOUR_USERNAME/vnpt-money-chatbot`

Kiểm tra:
- ✅ 61 files đã được push
- ✅ Folder structure: GraphRAG/, TraditionalRAG/
- ✅ README.md hiển thị đẹp
- ✅ Commit message hiển thị đầy đủ

### 2. Add Repository Description

Trên GitHub repo page:
- Click "About" (gear icon)
- Description: "GraphRAG Chatbot for VNPT Money FAQ with Neo4j Knowledge Graph and Case-based Response System"
- Topics: `chatbot`, `rag`, `neo4j`, `graph-database`, `nlp`, `vietnamese`

### 3. Create README Badges (Optional)

Thêm vào đầu GraphRAG/README.md:

```markdown
# GraphRAG Chatbot

![Python](https://img.shields.io/badge/python-3.11-blue)
![Neo4j](https://img.shields.io/badge/neo4j-5.x-green)
![License](https://img.shields.io/badge/license-MIT-yellow)
```

## Files Đã Push

### GraphRAG/ (38 files)
- 27 Python files
- 6 Documentation files
- 2 Folders (data/, database_exports/)

### TraditionalRAG/ (6 files)
- 4 Python files
- 1 README
- 1 requirements.txt

### Root Level (17 files)
- Documentation (3 files)
- Data (4 files)
- Utility scripts (5 files)
- Config files (5 files)

**Total**: 61 files, 39,491 dòng code

## Files KHÔNG Push (trong .gitignore)

- ❌ Archive_Old_Files/ (77 files)
- ❌ graphRAGChatBot_backup.tar.gz (17MB)
- ❌ models/ (embedding models)
- ❌ faiss_index/
- ❌ .env files
- ❌ __pycache__/
- ❌ *.log

## Cập Nhật Sau Này

### Khi có thay đổi:

```bash
# Stage changes
git add .

# Commit
git commit -m "Your commit message"

# Push
git push
```

### Khi thêm Case nodes mới:

```bash
# Run auto create
python GraphRAG/auto_create_case_nodes.py --execute

# Verify
python GraphRAG/verify_all_cases.py

# Commit
git add GraphRAG/
git commit -m "Add new Case nodes for [FAQ topic]"
git push
```

## Troubleshooting

### Lỗi "Repository not found"

**Nguyên nhân**: Sai URL hoặc không có quyền access

**Fix**: Kiểm tra lại URL và permissions

### Lỗi "Authentication failed"

**Nguyên nhân**: Sai username/token

**Fix**: Sử dụng Personal Access Token thay vì password

### Lỗi "Push rejected"

**Nguyên nhân**: Remote có commits mới hơn

**Fix**:
```bash
git pull --rebase origin main
git push
```

### File quá lớn

Nếu có file > 100MB, GitHub sẽ reject.

**Fix**: Add vào `.gitignore` và dùng Git LFS:

```bash
# Install Git LFS
git lfs install

# Track large files
git lfs track "*.tar.gz"
git lfs track "models/**"

# Commit .gitattributes
git add .gitattributes
git commit -m "Add Git LFS tracking"
git push
```

## Best Practices

### 1. Commit Messages

Format: `<type>: <description>`

Types:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `refactor:` - Code refactoring
- `test:` - Add tests
- `chore:` - Maintenance

Example:
```bash
git commit -m "feat: Add Case nodes auto-creation for if-then patterns"
```

### 2. Branch Strategy

```bash
# Create feature branch
git checkout -b feature/new-case-patterns

# Work on feature
# ...

# Commit
git commit -m "feat: Add new case patterns"

# Push branch
git push -u origin feature/new-case-patterns

# Create Pull Request on GitHub
# Merge after review
```

### 3. Regular Backup

```bash
# Create backup before major changes
tar -czf backup_$(date +%Y%m%d).tar.gz GraphRAG/ TraditionalRAG/
```

## Kết Luận

✅ Git repository đã sẵn sàng push

✅ Cấu trúc project rõ ràng, organized

✅ Documentation đầy đủ

✅ .gitignore setup đúng

**Next step**: Tạo GitHub repository và push theo hướng dẫn trên! 🚀
