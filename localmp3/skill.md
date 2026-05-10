LocalMusic 本地音乐播放器开发 Skill v1.0
1. Skill Name
LocalMusic 本地 MP3 音乐播放器开发协议
2. Purpose | 目标

本 Skill 用于从 0 开始辅助开发一个 非盈利、自用、本地化的音乐播放器应用。

项目核心目标：

用户通过导入本地 MP3 文件，将歌曲加入本地曲库；
应用自动读取歌曲信息；
用户可以创建、管理、整理歌单；
用户可以播放本地 MP3 音乐；
所有数据仅保存在本机，不联网、不传播、不下载音乐。

该 Skill 的重点不是开发商业级播放器，而是帮助用户完成一个：

本地 MP3 管理器 + 本地音乐播放器 + 歌单整理工具
3. User Background | 用户情况

用户是开发初学者，需要：

1. 从 0 开始搭建项目
2. 每一步都解释清楚
3. 代码要分文件、分模块讲解
4. 每段代码都要说明作用
5. 避免一次性给出过于复杂的大工程
6. 优先让程序能跑，再逐步增强功能

回答风格要求：

中文回答
通俗易懂
一步一步来
尽量像教学一样讲
代码要完整可运行
每一步都告诉用户该放在哪个文件
4. Project Description | 项目描述

项目名称建议：

LocalMusicPlayer

项目定位：

一个用于个人自用的本地 MP3 音乐播放器。
用户可以导入本地 MP3 文件，程序读取歌曲信息并保存到本地数据库。
用户可以创建歌单，把歌曲加入不同歌单，实现本地音乐整理。
5. Core Requirements | 核心需求

必须实现以下功能：

1. 导入本地 MP3 文件
2. 读取 MP3 歌曲信息
3. 保存歌曲信息到本地数据库
4. 显示全部歌曲列表
5. 双击歌曲播放
6. 创建歌单
7. 查看歌单
8. 将歌曲加入歌单
9. 从歌单中移除歌曲
10. 本地保存数据，下次打开仍然存在
6. Non-goals | 暂时不做的功能

第一版不做以下功能：

1. 在线音乐搜索
2. 音乐下载
3. 爬取网易云、QQ 音乐、酷狗等平台
4. 云同步
5. 用户登录
6. 歌曲分享
7. 在线歌词
8. 复杂皮肤系统
9. 推荐算法
10. 商业发布

原因：

这些功能会增加难度，也可能涉及版权和接口问题。
当前项目只做本地 MP3 管理和播放。
7. Tech Stack | 技术栈

推荐技术栈固定为：

Python 3.11 / Python 3.12
Conda 环境管理
PySide6
mutagen
SQLite

各技术作用：

PySide6：制作桌面软件界面，包括窗口、按钮、列表、文件选择框、播放器控件
mutagen：读取 MP3 文件的标题、歌手、专辑、时长等信息
sqlite3：Python 自带，用于保存歌曲、歌单和歌单歌曲关系
QtMultimedia：PySide6 内部模块，用于播放本地 MP3

环境创建方式：

conda create -n localmusic python=3.12 pip -y
conda activate localmusic
python -m pip install --upgrade pip
python -m pip install PySide6 mutagen
8. Project Structure | 项目结构

项目必须使用清晰的文件结构：

LocalMusicPlayer/
├── main.py
├── database.py
├── importer.py
├── player.py
├── requirements.txt
├── music.db
└── ui/
    └── main_window.py

文件职责：

main.py
程序入口，负责启动整个应用。

database.py
负责数据库初始化、保存歌曲、查询歌曲、创建歌单、管理歌单歌曲关系。

importer.py
负责导入 MP3 文件，读取歌曲元数据。

player.py
负责播放、暂停、停止、切换歌曲等播放逻辑。

ui/main_window.py
负责主界面，包括按钮、歌曲列表、歌单列表、播放控制区域。
9. Development Order | 开发顺序

开发时必须按照以下顺序推进：

第一步：创建 Conda 环境
第二步：创建项目目录结构
第三步：编写 database.py，完成数据库初始化
第四步：编写 importer.py，完成 MP3 信息读取
第五步：编写 main.py 和 ui/main_window.py，打开基础窗口
第六步：实现“导入歌曲”按钮
第七步：实现歌曲列表显示
第八步：实现双击歌曲播放
第九步：实现新建歌单
第十步：实现歌曲加入歌单
第十一步：实现查看歌单歌曲
第十二步：实现删除歌曲、移除歌单歌曲
第十三步：增加搜索、排序、播放控制
第十四步：打包成 exe

每一步必须先保证能运行，再进入下一步。

10. Database Design | 数据库设计

数据库使用 SQLite。

songs 表

用于保存歌曲信息：

CREATE TABLE IF NOT EXISTS songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    artist TEXT,
    album TEXT,
    duration INTEGER,
    file_path TEXT UNIQUE,
    created_at TEXT
);

字段说明：

id：歌曲唯一编号
title：歌名
artist：歌手
album：专辑
duration：歌曲时长，单位秒
file_path：MP3 文件路径，不能重复
created_at：导入时间
playlists 表

用于保存歌单：

CREATE TABLE IF NOT EXISTS playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    created_at TEXT
);

字段说明：

id：歌单编号
name：歌单名称
created_at：创建时间
playlist_songs 表

用于保存歌单和歌曲的关系：

CREATE TABLE IF NOT EXISTS playlist_songs (
    playlist_id INTEGER,
    song_id INTEGER,
    PRIMARY KEY (playlist_id, song_id)
);

含义：

一个歌单可以有多首歌
一首歌也可以加入多个歌单
11. MP3 Import Logic | MP3 导入逻辑

导入 MP3 时按照以下流程：

用户点击“导入歌曲”
        ↓
PySide6 打开文件选择框
        ↓
用户选择一个或多个 .mp3 文件
        ↓
importer.py 使用 mutagen 读取 MP3 信息
        ↓
获取 title、artist、album、duration、file_path
        ↓
如果读取不到 title，则用文件名代替
        ↓
database.py 保存歌曲信息
        ↓
刷新界面歌曲列表

导入时要处理以下情况：

1. 文件不是 MP3，跳过
2. MP3 没有标签，使用文件名作为歌名
3. 文件已经导入过，不重复保存
4. 文件路径不存在时，播放前提示用户
12. UI Design | 界面设计

第一版界面保持简单：

┌─────────────────────────────────────────────┐
│ LocalMusic 本地音乐播放器                    │
├───────────────┬─────────────────────────────┤
│ 歌单列表       │ 歌曲列表                     │
│               │                             │
│ 全部歌曲       │ 夜曲 - 周杰伦                │
│ 我喜欢的       │ 稻香 - 周杰伦                │
│ 学习歌单       │ Numb - Linkin Park           │
├───────────────┴─────────────────────────────┤
│ 当前播放：无                                │
│ [导入歌曲] [新建歌单] [播放/暂停] [下一首]   │
└─────────────────────────────────────────────┘

界面分为三部分：

左侧：歌单列表
右侧：歌曲列表
底部：播放控制区
13. Player Logic | 播放逻辑

播放使用 PySide6 的 QtMultimedia 模块。

基础逻辑：

用户双击歌曲
        ↓
程序获取歌曲 file_path
        ↓
检查文件是否存在
        ↓
QMediaPlayer 加载本地 MP3 文件
        ↓
QAudioOutput 输出声音
        ↓
开始播放
        ↓
底部显示当前播放歌曲

第一版需要实现：

1. 双击播放
2. 播放 / 暂停
3. 停止
4. 下一首

后续再扩展：

1. 上一首
2. 随机播放
3. 单曲循环
4. 音量调节
5. 播放进度条
14. Coding Rules | 代码规则

生成代码时必须遵守：

1. 不要把所有代码写在一个文件里
2. 每个模块职责清晰
3. 代码要适合初学者阅读
4. 函数名要清楚
5. 变量名要有意义
6. 关键位置添加中文注释
7. 每次只实现一个阶段的功能
8. 给出运行命令
9. 说明代码应该放在哪个文件中
10. 如果可能出错，要告诉用户常见错误和解决方法

示例回答格式：

这一步我们要完成：数据库初始化。

请打开 database.py，写入以下代码：

[代码]

这段代码做了几件事：
1. ...
2. ...
3. ...

运行方式：
python main.py

如果看到 music.db 文件，说明成功。
15. Copyright and Safety Rules | 版权与安全规则

项目必须遵守：

1. 只导入用户自己已有的本地 MP3 文件
2. 不提供下载音乐功能
3. 不爬取音乐平台
4. 不破解音乐平台接口
5. 不分享 MP3 文件
6. 不做公开传播
7. 不规避版权保护
8. 不做商业化音乐分发

项目描述必须保持为：

个人自用的本地 MP3 文件管理器和播放器。
16. Error Handling | 常见错误处理

开发过程中要重点帮助用户解决：

1. conda 环境没有激活
2. pip 安装到了错误环境
3. PySide6 安装失败
4. QtMultimedia 无法播放 MP3
5. mutagen 读取不到歌曲标签
6. SQLite 数据库路径错误
7. 文件路径含中文或空格
8. VS Code 没选对 Python 解释器
9. 双击歌曲没有反应
10. 打包 exe 后找不到数据库文件

解决问题时要先让用户执行：

python --version
where python
conda info --envs
python -m pip show PySide6
python -m pip show mutagen
17. Milestone Plan | 阶段目标
Milestone 1：环境搭建

目标：

Conda 环境创建成功
PySide6 安装成功
mutagen 安装成功
测试窗口能打开
Milestone 2：数据库完成

目标：

程序启动后自动生成 music.db
数据库中有 songs、playlists、playlist_songs 三张表
Milestone 3：导入 MP3

目标：

选择 MP3 文件后，可以读取歌曲名、歌手、专辑、时长
并保存到数据库
Milestone 4：显示歌曲列表

目标：

打开软件后可以看到已导入歌曲
Milestone 5：播放歌曲

目标：

双击歌曲后可以播放本地 MP3
Milestone 6：歌单管理

目标：

可以创建歌单
可以把歌曲加入歌单
可以查看歌单中的歌曲
Milestone 7：功能完善

目标：

搜索歌曲
删除歌曲
移除歌单歌曲
播放暂停
下一首
音量控制
Milestone 8：打包发布

目标：

使用 PyInstaller 打包成 Windows exe
18. Assistant Behavior | AI 辅助开发方式

当用户说：

继续
下一步
开始写代码
写 database.py
写 importer.py
写主界面

AI 应该：

1. 判断当前项目阶段
2. 给出当前阶段目标
3. 生成对应文件代码
4. 解释代码逻辑
5. 告诉用户如何运行
6. 告诉用户运行成功应该看到什么
7. 给出常见报错解决方法

不要一次性把所有模块全部写完，除非用户明确要求。

优先使用这种节奏：

一阶段一个功能
一个功能一个文件
写完就测试
测试通过再继续
19. Recommended First Step | 默认第一步

当用户准备正式开始时，先执行：

conda create -n localmusic python=3.12 pip -y
conda activate localmusic
python -m pip install --upgrade pip
python -m pip install PySide6 mutagen

然后创建项目：

mkdir LocalMusicPlayer
cd LocalMusicPlayer
mkdir ui
type nul > main.py
type nul > database.py
type nul > importer.py
type nul > player.py
type nul > ui\main_window.py
type nul > requirements.txt
20. Skill Summary | 总结

本 Skill 的核心原则：

先能运行，再做复杂
先做本地功能，不碰在线音乐
先做数据库和导入，再做播放和歌单
代码分模块写
每一步都给新手解释清楚

项目最终目标：

完成一个非盈利、自用、本地化的 MP3 音乐播放器，