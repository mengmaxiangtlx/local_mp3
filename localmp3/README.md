# LocalMusic 本地 MP3 播放器

LocalMusic 是一个个人自用的本地 MP3 音乐播放器。程序只管理和播放用户自己导入的本地 MP3 文件，不提供在线播放、下载、爬取或分享音乐功能。

## 功能

- 导入本地 MP3 文件
- 自动读取歌曲名称、歌手、专辑和时长
- 使用 SQLite 保存歌曲、歌单和播放列表关系
- 双击歌曲播放
- 支持上一首、播放/暂停、下一首
- 支持播放进度条拖动跳转
- 支持顺序播放、随机播放、单曲循环
- 支持歌单创建、收纳、添加歌曲、移除歌曲
- 支持歌曲右键菜单：播放、修改歌名、修改歌手、修改专辑、删除记录
- 修改歌名时同步重命名本地 MP3 文件
- 修改歌曲信息后同步保存到数据库
- 支持按导入时间、歌名、歌手排序
- 支持拖拽调整歌曲顺序
- 支持自定义字体大小、字体颜色、标题颜色、背景图片
- 自绘无边框窗口，支持圆角背景、自定义标题栏和窗口拖拽缩放
- 支持 Windows 任务栏缩略图工具栏：上一首、播放/暂停、下一首

## 项目结构

```text
localmp3/
├── main.py                 # 程序入口
├── database.py             # SQLite 数据库读写
├── importer.py             # MP3 元数据读取
├── player.py               # 播放器控制逻辑
├── taskbar_toolbar.py      # Windows 任务栏缩略图按钮
├── requirements.txt        # Python 依赖
├── music.db                # 本地歌曲数据库，运行后生成/更新
├── settings.ini            # 用户界面设置，运行后生成/更新
├── skill.md                # 项目开发要求说明
└── ui/
    └── main_window.py      # 主界面
```

## 环境要求

- Windows
- Python 3.11 或 Python 3.12
- PySide6
- mutagen

## 安装依赖

建议先创建独立环境：

```powershell
conda create -n localmusic python=3.12 pip -y
conda activate localmusic
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

如果不使用 Conda，也可以在当前 Python 环境中直接安装：

```powershell
python -m pip install -r requirements.txt
```

## 运行

在项目根目录执行：

```powershell
python main.py
```

启动后可以点击“导入歌曲”选择本地 MP3 文件。

## 数据说明

- `music.db` 保存歌曲信息、歌单信息和歌单歌曲关系。
- `settings.ini` 保存窗口大小、界面颜色、背景图片、分栏宽度、表格列宽等用户设置。
- 删除 `music.db` 会清空软件内的歌曲记录和歌单，但不会删除本地 MP3 文件。
- 删除 `settings.ini` 会恢复默认界面设置。

## 常见问题

### 双击歌曲没有播放

先确认歌曲文件路径仍然存在。如果 MP3 文件被移动或删除，软件中的数据库记录会失效，需要重新导入。

### 歌手、专辑或时长显示不正确

程序会优先读取 MP3 文件标签。如果 MP3 没有写入正确标签，可以在歌曲列表中直接编辑歌手和专辑；时长会根据实际 MP3 文件重新读取。

### 修改歌名后文件名变化

这是当前设计：修改歌名时会同步重命名对应的 `.mp3` 文件，方便本地文件和软件内显示保持一致。

### Windows 任务栏按钮没有出现

任务栏缩略图按钮只在 Windows 平台可用，并且需要窗口启动并显示后才会初始化。

## 开发说明

项目按模块拆分：

- 界面相关改动主要在 `ui/main_window.py`
- 播放控制相关改动主要在 `player.py`
- 数据库字段和增删改查主要在 `database.py`
- MP3 信息读取主要在 `importer.py`
- Windows 任务栏缩略图按钮主要在 `taskbar_toolbar.py`

修改代码后可以先运行编译检查：

```powershell
python -m compileall main.py database.py importer.py player.py taskbar_toolbar.py ui
```
