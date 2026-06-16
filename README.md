# 🎙️ Voice Helper — 全局语音输入工具

![platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue)
![python](https://img.shields.io/badge/python-3.10%2B-3776ab)
![engines](https://img.shields.io/badge/engines-Whisper%20%7C%20SenseVoice%20%7C%20Paraformer-9cf)
![license](https://img.shields.io/badge/license-MIT-green)

> **Local, cross-platform push-to-talk dictation.** Hold a hotkey, speak, release —
> your speech is transcribed **on-device** and pasted into whatever field has focus,
> in any app. Three switchable engines (Whisper / SenseVoice / Paraformer with live
> hotword biasing). Runs on macOS (Apple GPU) and Windows (CPU). No cloud, no cost.

一个常驻的「按住说话」语音输入工具:在**任意 App** 的输入框里,按住快捷键说话,松开后自动把语音转成文字插入光标处。支持**多识别引擎可切换**(Whisper / SenseVoice / Paraformer),**跨平台**(macOS / Windows),**纯本地、零成本**。

> 为 Claude Code CLI 的语音输入而搭建,但对所有 App 通用。

---

## 〇、快速开始(跨平台,Git 仓库)

任意 Python 3.10+ 即可,安装脚本会自建 `.venv` 并装好对应平台的依赖、配置开机自启。

> ⚠️ **(Windows 重要)放在纯英文路径**,如 `D:\voice-helper`、`C:\voice-helper`。
> **不要**放在含中文/空格的目录(如 `D:\智能运维\...`)——funasr 的分词器在非ASCII路径下会报「模型 Not Found」。已装在中文路径的,跑 `bash voicectl.sh fixpath` 一键补救(见第⑨节)。

```bash
git clone https://github.com/KimiRaikking/voice-helper.git   # 到纯英文路径!
cd voice-helper
python install.py          # Windows 也可用 py install.py
```

- **Windows**:`python install.py` 自动建环境、装 `faster-whisper`(CPU)+ SenseVoice、并在「启动」文件夹放一个隐藏启动项。装完即生效、开机自启。手动启动双击 `run.bat`,看报错用 `run-debug.bat`。
- **macOS**:同一条命令,装 `mlx-whisper`(GPU)+ SenseVoice,并配 LaunchAgent。**额外需在系统设置授权**(见第⑧节)。
- 改配置:编辑 `voice.env`(引擎/热键/语言),然后重启服务(见第⑥/⑦节)。

> 首次说话会自动下载模型(SenseVoice 从 ModelScope,Whisper 从 HuggingFace),稍等片刻。

跨平台差异一览:

| 模块 | macOS | Windows |
|------|-------|---------|
| Whisper 后端 | `mlx-whisper`(Apple GPU) | `faster-whisper`(CPU,int8) |
| SenseVoice | funasr(通用) | funasr(通用) |
| 状态指示 | 顶部菜单栏 emoji(rumps) | 右下角系统托盘 emoji(pystray + Segoe UI Emoji) |
| 粘贴 | Cmd+V | Ctrl+V |
| 开机自启 | LaunchAgent | 启动文件夹 VBS(隐藏) |
| 系统授权 | 需输入监控/辅助功能/麦克风 | 无需特殊授权 |
| 日志 | `voiced.log` | `voiced.log`(pythonw 无控制台,已自动重定向) |

---

## 一、它能做什么

- **全局可用**:任何能接受粘贴的输入框(终端、浏览器、微信、备忘录、邮件……)都能用。
- **按住说话**:按住热键(默认右 Option / 右 Alt)录音,松开即转写并自动粘贴。
- **多引擎可切换**:Whisper(多语言)/ SenseVoice(中文优化),通过 `VOICE_ENGINE` 一键切换,模型都在本地、互不替换。
- **状态可见**:状态图标实时显示(mac 菜单栏 / Windows 系统托盘),并标注当前引擎。
- **强制简体中文**:偶尔输出繁体时自动转简体(不影响英文)。
- **开机自启**:后台服务,开机自动运行、崩溃自动重启,无需手动开启。

**例外**:密码输入框(系统安全键盘机制屏蔽模拟粘贴)、全屏独占键盘的 App 可能用不了。

---

## 二、目录与文件结构

| 路径 | 说明 |
|------|------|
| `voiced.py` | 主程序:常驻「按住说话」守护进程 + 状态图标 + 多引擎转写 |
| `vplatform.py` | 平台抽象层(剪贴板/粘贴键/声音/通知,mac↔win 差异都在这) |
| `tray.py` | 状态图标抽象(mac=rumps 菜单栏,win/linux=pystray 托盘) |
| `install.py` | 跨平台一键安装(建 venv、装依赖、配自启) |
| `voice.env` / `voice.env.example` | 配置文件(引擎/热键/语言);voiced 启动时自动读取 |
| `requirements-*.txt` | 分平台依赖清单(common / macos / windows / sensevoice) |
| `run.bat` / `run-debug.bat` | Windows 手动启动 / 调试启动 |
| `dictate.py` | 备用:一次性录音 → 转写 → 复制到剪贴板(不常驻) |
| `.venv/` | Python 虚拟环境(所有依赖装在这里) |
| `voiced.log` | 运行日志 |

**自启配置文件位置**

- macOS:`~/Library/LaunchAgents/com.voicehelper.dictation.plist`
- Windows:`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\voice-helper.vbs`

**技术栈**

| 组件 | 用途 | 平台 |
|------|------|------|
| `mlx-whisper` | Whisper 引擎(Apple MLX,吃满 GPU) | macOS |
| `faster-whisper` | Whisper 引擎(CTranslate2,CPU int8) | Windows / Linux |
| `funasr`+`modelscope`+`torchaudio` | SenseVoice 中文引擎 | 通用 |
| `sounddevice` | 麦克风录音 | 通用 |
| `pynput` | 全局热键 + 模拟粘贴 | 通用 |
| `rumps` / `pystray`+`pillow` | 菜单栏 / 系统托盘图标 | mac / win |
| `pyperclip` | 跨平台剪贴板 | 通用 |
| `opencc` | 繁体强制转简体 | 通用 |

**模型缓存位置**

| 引擎 | macOS | Windows |
|------|-------|---------|
| Whisper | `~/.cache/huggingface/` | `%USERPROFILE%\.cache\huggingface\` |
| SenseVoice | `~/.cache/modelscope/hub/models/iic/SenseVoiceSmall` | `%USERPROFILE%\.cache\modelscope\hub\models\iic\SenseVoiceSmall` |

---

## 三、日常使用

1. 把光标放进任意输入框。
2. **按住热键**(默认右 Option / 右 Alt)→ 说话 → **松开**。
3. 文字自动转写并粘贴到光标处。

点开图标的菜单可见:**状态** / **最近识别文字**(点击可复制) / **切换引擎**(Whisper/SenseVoice/Paraformer,当前打勾,点一下**即时热切换、无需重启**) / 退出。

- **macOS**:图标在屏幕**最顶部菜单栏**(靠近刘海一侧)。
- **Windows**:图标在**右下角系统托盘**(若被折叠,点任务栏的 `^` 展开);**右键**图标看菜单。

mac 和 Windows 都用同一套 emoji 图标:

| 图标 | 含义 |
|------|------|
| 🎤 | 待命 |
| 🔴 | 录音中 |
| ⏳ | 转写中 |
| ✅ | 完成 |
| ⚠️ | 太短 / 失败 |

> Windows 用 Segoe UI Emoji 渲染同款彩色 emoji;个别老系统渲染不了时自动退回彩色圆点。

---

## 四、识别引擎

通过 `VOICE_ENGINE` 选择,模型都在本地,可随时切换:

| 引擎 | `VOICE_ENGINE` | 特点 | 适用 |
|------|----------------|------|------|
| **Whisper** | `whisper`(默认) | 多语言,中英混说友好 | 通用、英文多 |
| **SenseVoice** | `sensevoice` | 阿里达摩院,中文/方言优化,带智能标点,非自回归极快 | 中文为主 |
| **Paraformer** | `paraformer` | SeACo-Paraformer,中文最准 + **热词偏置** + **标点**(VOICE_PUNC) | 中文 + 专业术语多 |

> **关于准确度**:中文「技术同音词」(时延 / 实验 / 食言)对**通用模型**(Whisper / SenseVoice)都是难点——会默认挑最常见的词。真正对症的是 **Paraformer 的热词偏置**:把常错的词喂进去,强制优先匹配(见第⑩节)。

---

## 五、配置项

所有配置写在 **`voice.env`**(`voice.env.example` 复制而来),voiced 启动时自动读取;两个平台通用。

| 环境变量 | 作用 | 默认值 |
|---------|------|--------|
| `VOICE_ENGINE` | 识别引擎:`whisper` / `sensevoice` / `paraformer` | `whisper` |
| `VOICE_KEY` | 说话热键:`alt_r`/`alt_l`/`ctrl_r`/`cmd_r`/`f5`… | `alt_r`(右 Option/Alt) |
| `VOICE_LANG` | 强制语言,如 `zh`/`en`;留空=自动识别 | 空(自动) |
| `WHISPER_MODEL` | Whisper 模型(见下表,mac/win 取值不同) | 见下 |
| `SENSEVOICE_MODEL` | SenseVoice 模型 | `iic/SenseVoiceSmall` |
| `VOICE_PROMPT` | Whisper 专用,热词/上下文提示(`initial_prompt`) | 空 |
| `VOICE_HOTWORD` | Paraformer 静态热词(空格分隔;动态词用 `hotwords.txt`,见第⑩节) | 空 |
| `VOICE_SOUND` | 设为任意值=开启声音提示 | 关 |
| `VOICE_NOTIFY` | 设为 `1`=完成时弹通知显示识别文字 | 关 |
| `VOICE_NO_PASTE` | 设为任意值=只复制到剪贴板,不自动粘贴 | 关(自动粘贴) |

### Whisper 模型选项

**macOS(mlx,默认 `mlx-community/whisper-large-v3-turbo`)**

| 模型 | 大小 | 速度 | 精度 |
|------|------|------|------|
| `mlx-community/whisper-small-mlx` | ~0.5GB | 很快 | 中 |
| `mlx-community/whisper-large-v3-turbo` | ~1.6GB | 快 | 高 |
| `mlx-community/whisper-large-v3-mlx` | ~3GB | 稍慢 | 最高 |

**Windows(faster-whisper,默认 `small`)** — 直接填规格名即可:

| `WHISPER_MODEL` | 大小 | CPU 速度 | 精度 |
|------|------|------|------|
| `small` ← 默认 | ~0.5GB | 快 | 中 |
| `medium` | ~1.5GB | 中 | 中高 |
| `large-v3` | ~3GB | 慢 | 最高 |

> CPU 上 `medium` 是精度/速度较好的折中;追求准确用 `large-v3`(慢)。中文优先建议直接用 SenseVoice 引擎。

> 💡 **本地模型目录**:`WHISPER_MODEL` 也可填一个**本地文件夹路径**(含 `config.json` + 权重)。当 HF 在线下载卡死时,可手动把模型拉到 `models/` 下再指过去(见第⑨节「下载卡 0.00B」)。

> ⚙️ **配置优先级**:`voice.env` 是配置的唯一来源(mac 的 LaunchAgent plist 已不再写环境变量)。若进程环境里真的设了同名变量,则它优先于 `voice.env`。

---

## 六、如何修改配置

通用:编辑 `voice.env` → 保存 → **重启服务**(见下)。

**macOS**

```bash
open -e ~/voice-helper/voice.env     # 或任意编辑器
launchctl kickstart -k gui/$(id -u)/com.voicehelper.dictation   # 重启生效
```

**Windows**(在仓库目录,双击或命令行运行 `.bat` 即可)

```bat
notepad voice.env
restart.bat      :: 重启生效(= 停止 + 重新启动)
```

---

## 七、开机自启 / 服务管理

### macOS(LaunchAgent)

`RunAtLoad=true`(登录即启动)、`KeepAlive=true`(崩溃自动重启)。

```bash
launchctl list | grep voicehelper                                  # 是否在跑
launchctl kickstart -k gui/$(id -u)/com.voicehelper.dictation       # 重启
launchctl unload ~/Library/LaunchAgents/com.voicehelper.dictation.plist   # 关闭
launchctl load   ~/Library/LaunchAgents/com.voicehelper.dictation.plist   # 开启
tail -f ~/voice-helper/voiced.log                                   # 看日志
```

### Windows(启动文件夹 VBS)

`install.py` 在启动文件夹放了 `voice-helper.vbs`,用 `pythonw` 隐藏窗口运行,登录即起。仓库带了几个一键脚本(双击即可):

| 脚本 | 作用 |
|------|------|
| `status.bat` | **查看是否在运行 + 日志末尾**(确认有没有生效用这个) |
| `restart.bat` | 重启(停止 + 启动) |
| `stop.bat` | 停止 |
| `run.bat` | 手动启动 |
| `run-debug.bat` | 前台调试(显示控制台、看实时报错) |

```bat
status.bat       :: 是否在跑 + 日志
restart.bat      :: 重启

:: 关闭自启:删掉启动文件夹里的 vbs
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\voice-helper.vbs"

:: 看日志
type voiced.log
```

> 调试时直接跑 `run-debug.bat`(显示控制台,能看到实时报错),Ctrl+C 退出。

**在 Git Bash 里用 `voicectl.sh`** —— 全部子命令速查:

| 命令 | 作用 |
|------|------|
| `bash voicectl.sh status` | 是否在跑 + 本次启动以来的日志 |
| `bash voicectl.sh start` / `stop` / `restart` | 启动 / 停止 / 重启 |
| `bash voicectl.sh log` | 实时跟踪日志(Ctrl+C 退出) |
| `bash voicectl.sh doctor` | 一键诊断(venv/运行/引擎/模型/网络/加载路径) |
| `bash voicectl.sh selftest` | 基础自测(加载/推理/纠正/剪贴板,不需麦克风) |
| `bash voicectl.sh curldl [all]` | curl 断点续传下模型(烂网络/代理稳) |
| `bash voicectl.sh checkmodel` | 比对配置期望文件名 vs 实际文件 |
| `bash voicectl.sh fixpath` | 中文路径修复:模型挪到纯英文路径 |
| `bash voicectl.sh clean` | 清掉卡住的下载进程 + 锁 |
| `bash voicectl.sh hot 时延 推理` | 加热词(Paraformer,即时生效) |
| `bash voicectl.sh fix 食盐 时延` | 加自动纠正规则(所有引擎,即时生效) |

> 装完先跑 `bash voicectl.sh selftest` 验证链路;全 ✅ 再按热键说话。

---

## 八、系统权限

### macOS(必做)

后台进程需三项权限,授给那个 Python 解释器二进制(路径见 `which python` 或 venv 里的 `.venv/bin/python` 解析后的真实路径):

| 权限 | 用途 |
|------|------|
| **输入监控 (Input Monitoring)** | 监听热键 |
| **辅助功能 (Accessibility)** | 模拟 Cmd-V 自动粘贴 |
| **麦克风 (Microphone)** | 录音 |

在 **系统设置 → 隐私与安全性** 里逐项添加;文件选择框灰掉无法选中时,改用「从 Finder 拖拽」该二进制。授权后需重启服务。

### Windows(基本无需)

- 不需要输入监控/辅助功能这类授权。
- 首次录音若 Win11 弹**麦克风**询问,允许即可;或到 **设置 → 隐私和安全性 → 麦克风**,打开「允许桌面应用访问麦克风」。
- 首次运行 SmartScreen/杀软可能提示未知发布者,选「仍要运行」。

---

## 九、常见问题 / 诊断排查

### ⚡ 一键诊断(出问题先跑这个)

Git Bash,仓库目录:

```bash
bash voicectl.sh doctor
```

输出 8 行(`200`=通,`000`=连不上)+ 日志最后报错:

```
1 venv环境 有/无
2 正在运行 是/否
3 当前引擎 ...
4 中文模型SenseVoice 有/无
5 热词模型Paraformer 有/无
6 连GitHub 返回 200/000
7 连魔搭ModelScope 返回 200/000
8 连抱抱脸HuggingFace 返回 200/000
```

### 🔍 手动逐项检查

```bash
# venv 是否装好(应输出 python.exe 路径,不报 No such file)
ls ~/voice-helper/.venv/Scripts/python.exe

# 模型是否真的下好(总大小应约 900M~1G,且有 model.pt)
# 两个可能的位置:① modelscope 缓存(download)② 本地 models/(curldl)
du -sh ~/.cache/modelscope/hub/models/iic/* 2>/dev/null
du -sh ~/voice-helper/models/* 2>/dev/null
# 最省事:直接看 doctor 的第 4/5 行(两个位置都查)
bash voicectl.sh doctor

# 是否在运行 + 日志末尾
bash voicectl.sh status
tail -n 30 ~/voice-helper/voiced.log

# 网络连通性(200=通,000=连不上/被代理拦)
curl -s -m 8 -o /dev/null -w "%{http_code}\n" https://www.modelscope.cn
curl -s -m 8 -o /dev/null -w "%{http_code}\n" https://huggingface.co
```

### 🏢 公司网络:连接全 000 / `authentication required`

需要走**带认证的代理**。但注意:

- **日常用 SenseVoice 不需要网络** —— 模型一旦下好(上面 `du` 显示约 900M),就纯本地运行,断网也能用。直接按住热键说话测试即可。
- **让 SenseVoice 彻底离线**(避免加载时碰网):`voice.env` 里指向本地目录(把 `<用户名>` 换成你的):
  ```
  SENSEVOICE_MODEL=C:\Users\<用户名>\.cache\modelscope\hub\models\iic\SenseVoiceSmall
  ```
  然后 `bash voicectl.sh restart`。
- **下模型走代理(推荐)**:把 git 用的代理填进 `voice.env`,工具会自动用它下模型。
  ```bash
  # 1) 看 git 用的代理(复制它的输出)
  git config --global --get http.proxy
  # 2) 编辑 voice.env,加一行(把值换成上一步的输出):
  #    VOICE_PROXY=http://用户:密码@IP:端口
  # 3) 下载当前引擎的模型(走 voice.env 里的代理,有进度)
  bash voicectl.sh download
  # 4) 重启
  bash voicectl.sh restart
  ```
  > `download all` 可一次下 SenseVoice + Paraformer 两个。
- **下载反复断 / `model.pt` 越滚越大(涨爆)** —— modelscope 的 python 下载在烂代理上续传是坏的(断线后往同一文件追加)。改用 **curl 断点续传**(真 HTTP-Range,不会涨爆),下到本地目录、自动改好 `voice.env` 指过去:
  ```bash
  bash voicectl.sh clean                  # 先杀掉卡住的进程
  rm -rf ~/.cache/modelscope/hub/models/._____temp   # 删掉涨爆的临时文件
  bash voicectl.sh curldl all             # curl 续传下 SenseVoice+Paraformer+标点
  bash voicectl.sh restart
  ```
  > 下到 `~/voice-helper/models/` 下(已 gitignore),`voice.env` 会自动指向本地目录,funasr 直接读、不再联网。
- **报 `self signed certificate in certificate chain`**(代理做 TLS 拦截):需信任公司根证书。
  ```bash
  # 1) 看 git 用的证书路径(复制输出)
  git config --global --get http.sslCAInfo
  # 2) 在 voice.env 加一行(值换成上一步路径):
  #    VOICE_CA=C:\path\to\company-ca.pem
  # 3) 重新下载
  bash voicectl.sh download
  ```
  > 第 1 步没输出(git 用的是 `http.sslVerify=false`)且实在拿不到证书时,应急在 voice.env 写 `VOICE_INSECURE=1`(跳过校验,不安全,仅内网临时用)。
- **没有可用代理/证书?从已下好的机器拷贝**:把源机器(如你的 Mac)上 `~/.cache/modelscope/hub/models/iic/SenseVoiceSmall` 整个文件夹,拷到本机相同路径 `C:\Users\<用户名>\.cache\modelscope\hub\models\iic\SenseVoiceSmall`,即可离线用。

### 常见现象

**(Windows)怎么确认它装好/生效了?**
仓库目录里**双击 `status.bat`**,会显示:① 进程是否在跑(`running, PID …` / `NOT running`)② `voiced.log` 末尾(能看到模型加载或报错)。
其次:看**右下角系统托盘**有没有彩色圆点图标(被折叠就点 `^` 展开)。最后:把光标放输入框,**按住右 Alt 说句话**——出字就是生效了。
- 显示 `NOT running` → 双击 `run.bat` 手动启动;要看报错用 `run-debug.bat`(前台控制台)。

**按了没反应 / 录音失效?**
- **macOS** 日志报 `PaErrorCode -9986`:音频设备变了(插拔耳机、切换输出)导致 PortAudio 缓存失效。重启服务:
  `launchctl kickstart -k gui/$(id -u)/com.voicehelper.dictation`
- **Windows**:切换音频设备后,双击 **`restart.bat`** 重启。
- 还不行 → 看「权限」:mac 缺输入监控/辅助功能;Windows 缺麦克风权限。

**状态图标看不到?**
- macOS:在屏幕**最顶部菜单栏**,刘海可能挡住;按住热键说话时盯顶栏看变化。
- Windows:在**右下角托盘**,可能被折叠 → 点任务栏 `^` 展开;可拖到常驻区。

**有识别但没自动粘贴?**
- macOS:缺「辅助功能」权限。
- Windows:目标窗口可能拦截了模拟按键;先确认 `voice.env` 没设 `VOICE_NO_PASTE`,文字其实已在剪贴板,手动 Ctrl+V 可粘。

**(Windows)模型文件明明在,却报 `Not Found ...bpe.model`?**
项目路径里有**中文/非ASCII目录**(如 `D:\智能运维\...`)时,funasr 的 SentencePiece 分词器(C++ 库)打不开中文路径的文件 → 假性 Not Found。一条命令修(把模型挪到纯英文路径、自动改好 voice.env,repo/venv 不动):
```bash
bash voicectl.sh fixpath
bash voicectl.sh restart
```
> 根治:项目本身也放在纯英文路径(`D:\voice-helper` 这种),别放带中文的目录。

**输出繁体字?** 已用 OpenCC 强制转简体;若仍出现,确认 `opencc`(或 `opencc-python-reimplemented`)在 venv 里。

**改了 `voiced.py` / `voice.env` 不生效?** 需重启服务(见第⑥/⑦节)。

**下载 Whisper 大模型一直卡在 `0.00B`?**
HF 大文件改用了 Xet 后端,国内网络经常卡死。先试**禁用 Xet 走旧通道**:
```bash
HF_HUB_DISABLE_XET=1 ~/voice-helper/.venv/bin/python -c "from huggingface_hub import snapshot_download; print(snapshot_download('mlx-community/whisper-large-v3-mlx'))"
```
若 `large-v3`(权重 `weights.npz` ~3GB)**仍然卡死**(实测国内网络 huggingface_hub 客户端对 3GB 文件极不稳定),改用**最可靠的办法:curl 国内镜像直接拉到本地目录**(绕开整个 huggingface_hub/Xet,纯 HTTP + 断点续传):
```bash
DIR=~/voice-helper/models/whisper-large-v3-mlx
mkdir -p "$DIR" && cd "$DIR"
# 大权重(2.9GB,断点续传、自动重试)
curl -L -C - --retry 30 --retry-delay 5 --retry-all-errors -o weights.npz \
  "https://hf-mirror.com/mlx-community/whisper-large-v3-mlx/resolve/main/weights.npz"
# 小配置
curl -L -o config.json \
  "https://hf-mirror.com/mlx-community/whisper-large-v3-mlx/resolve/main/config.json"
```
然后在 `voice.env` 里把 `WHISPER_MODEL` 指向这个**本地目录**(mlx 支持直接加载本地路径):
```
WHISPER_MODEL=/Users/<你>/voice-helper/models/whisper-large-v3-mlx
```
> `models/` 已在 `.gitignore` 里,大模型不会进 Git。Windows 上 faster-whisper 模型同理可换镜像/手动下。

SenseVoice 走 ModelScope(国内快),一般不受此问题影响——**中文场景直接用 SenseVoice 引擎通常更省事**。

---

## 十、热词偏置:动态喂词(治技术同音词)✅

针对「技术同音词」(时延/实验、推理/椎离),`paraformer` 引擎用 **SeACo-Paraformer** 做**热词偏置**:给它一份词清单,遇同音歧义时强制优先匹配。模型从 ModelScope 下载(国内快)。

**启用**:`voice.env` 设 `VOICE_ENGINE=paraformer` → 重启服务。

**动态喂词(核心)**:热词放在 `hotwords.txt`(每行一个),**引擎每次转写都实时读取,加词无需重启**。所以工作流是:

> 说一句 → 发现某个词转错了 → 立刻把正确词喂进去 → 再说一遍就对了。

```bash
# 加词(任意目录可用)
addhot 时延 推理 吞吐量
# 或
python ~/voice-helper/add_hotword.py 时延 推理
# 查看当前热词
addhot
```

- 静态热词也可写在 `voice.env` 的 `VOICE_HOTWORD=时延 推理`(与 `hotwords.txt` 合并)。
- `hotwords.txt` 是**个人词库**,已 gitignore;仓库里带一份起步样例 `hotwords.txt.example`。
- 跨平台通用(Windows 用 `python add_hotword.py …`)。

> 标点:Paraformer 默认通过 `VOICE_PUNC`(ct-punc 模型,`download all` 会一并下)加上标点。不想要标点就在 `voice.env` 设 `VOICE_PUNC=`(留空)。

---

## 十一、字词自动纠正(所有引擎通用)✅

转写完成后,套用一张**纠正表**做替换——适合给 AI agent 用:某些词总被转错,登记一条规则,以后**自动纠正**。和热词互补,**对 SenseVoice / Whisper / Paraformer 都生效**。

规则在 `corrections.txt`,每行 `错词=>对词`,**每次转写实时读取,即改即生效**(无需重启)。工作流:

> agent 场景里发现「时延」老被转成「食盐」→ 登记一条 → 以后自动纠正。

```bash
# 加规则(任意目录)
addfix 食盐 时延
# 或
python ~/voice-helper/add_fix.py 食盐 时延
# 查看所有规则
addfix
```

- 在 Windows Git Bash:`bash voicectl.sh fix 食盐 时延`。
- 长词优先匹配,避免误伤子串;`corrections.txt` 是个人表,已 gitignore(样例 `corrections.txt.example`)。
- 三层叠加最稳:**Paraformer 热词**(转写时偏置)→ **自动纠正表**(转写后兜底)→ 简繁转换。

---

## 十二、卸载

### macOS

```bash
launchctl unload ~/Library/LaunchAgents/com.voicehelper.dictation.plist
rm ~/Library/LaunchAgents/com.voicehelper.dictation.plist
rm -f ~/.local/bin/voiced ~/.local/bin/dictate
rm -rf ~/voice-helper
# 可选:删模型缓存
# rm -rf ~/.cache/huggingface/hub/models--mlx-community--whisper-*
# rm -rf ~/.cache/modelscope/hub/models/iic/SenseVoiceSmall
```

### Windows

```bat
:: 停进程 + 删自启 + 删目录
stop.bat
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\voice-helper.vbs"
cd %USERPROFILE% && rmdir /s /q "%USERPROFILE%\voice-helper"
:: 可选:删模型缓存
:: rmdir /s /q "%USERPROFILE%\.cache\modelscope\hub\models\iic\SenseVoiceSmall"
```

---

## 十三、Windows 部署避坑速查

公司/内网 Windows 上从零部署,按这个顺序最稳:

```bash
# 1) 克隆到纯英文路径(关键!)
git clone https://github.com/KimiRaikking/voice-helper.git   # D:\voice-helper 等
cd /d/voice-helper
# 2) 安装(没网/代理装不上依赖时,见下表“依赖装不上”)
python install.py
# 3) 模型:网络好直接首次说话自动下;烂网络/代理用 curl 断点续传
bash voicectl.sh curldl all
# 4) 自测 + 启动
bash voicectl.sh selftest
bash voicectl.sh restart
```

踩过的坑与解法:

| 现象 | 原因 | 解法 |
|------|------|------|
| 报 `Not Found ...bpe.model`(文件其实在) | 路径含**中文/非ASCII**,SentencePiece 打不开 | 项目放纯英文路径;已装错的跑 `bash voicectl.sh fixpath` |
| 启动日志 `api ... 407` / `authentication required` | 公司代理要鉴权,模型加载去 ping ModelScope API | 模型下到本地后会**离线加载、不调 API**;确保 `doctor` 第9行是“本地路径” |
| 下载报 `self signed certificate in certificate chain` | 公司代理做 TLS 拦截(自签证书) | `voice.env` 设 `VOICE_CA=<公司根证书>`;拿不到证书则 `VOICE_INSECURE=1` |
| 下载全 `000` / 连不上 | 没走代理 | `git config --get http.proxy` 拿到值填 `voice.env` 的 `VOICE_PROXY` |
| `model.pt` 越下越大(涨爆)/ 反复断 | modelscope 的 python 下载在烂代理上续传是坏的 | 改用 `bash voicectl.sh curldl all`(curl 真·断点续传) |
| `seg_dict` 老下不下来 | 它是分词词典,**推理用不到** | 可忽略;curldl 已把它设为可选 |
| 按热键(右 Alt)无反应 | 右 Alt 在多数 Windows 布局是 **AltGr**(pynput 上报 `alt_gr`) | 已自动兼容 `alt_r`+`alt_gr`;仍不行换 `VOICE_KEY=f8` |
| `.bat` 里中文乱码 | cmd 默认 GBK 代码页 | 脚本已改英文提示;或用 Git Bash 跑 `voicectl.sh` |
| `status` 老看到旧报错 | `voiced.log` 是追加写 | `status`/`doctor` 只显示**本次启动以来**(认 `===== voiced 启动 =====` 横幅) |
| 依赖装不上(pip 连不上) | 代理/内网 | `pip` 配公司代理 / 内网 PyPI 镜像;或在通网机器装好 `.venv` 拷过去 |
| 远程按热键有反应但不出字(橙色) | 远程桌面**不转发本地麦克风** | 到真机跟前;或开 RDP「本地资源→远程音频→录制」转发麦克风 |

**配置全在 `voice.env`**,公司机器常用:
```
VOICE_ENGINE=sensevoice        # 或 paraformer(中文最准+热词+标点)
VOICE_PROXY=http://用户:密码@IP:端口   # 同 git 的代理
VOICE_INSECURE=1               # 代理 TLS 拦截、拿不到证书时
```
