from html import escape

from bot import config_dict
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.bot_commands import BotCommands


class UsetString:
    CAP = f"""
<b>CUSTOM CAPTION SETTING</b>\n
Set custom caption with <b>HTML</b> style
<i>*Be careful when you use html tag for caption\n
Timeout: 60s.</i>
"""
    DUMP = """
<b>DUMP SETTING</b>\n
Example: <code>-10012345678</code> or <code>username</code>\n
Timeout: 60s.</i>
"""
    RCP = """
<b>RCLONE PATH SETTING</b>\n
Send valid rclone path
Example: <code>mrcc:GDRIVE:HONEY</code>\n
Timeout: 60s.</i>
"""
    GDID = """
<b>GDRIVE ID SETTING</b>\n
Send valid Google Drive ID
Example: <code>0AHrdo0ZYDJTgUk9PVA</code>\n
Timeout: 60s.</i>
"""
    EXT = """
<b>EXTENSION FILTERS SETTING</b>\n
Send any extension you wanna exclude them to upload
Example: <code>html jpg png js txt</code>\n
Timeout: 60s.</i>
"""
    INDX = """
<b>INDEX URL SETTING</b>\n
Send valid index url
Example: <code>https://xx.xxxxxx.workers.dev/0:</code>\n
Timeout: 60s.</i>
"""
    PRE = """
<b>PRENAME SETTING</b>\n
Example: <b>@MyChannel -</b>\n
<b>Org Name:</b>
<code>Batman (2022) [1080p] - H264.mkv</code>
<b>Result:</b>
<code>@MyChannel - Batman (2022) [1080p] - H264.mkv</code>\n
<i>Timeout: 60s.</i>
"""
    SUF = """
<b>SUFNAME SETTING</b>\n
Example: <b>- @MyChannel</b>\n
<b>Org Name:</b>
<code>Batman (2022) [1080p] - H264.mkv</code>
<b>Result:</b>
<code>Batman (2022) [1080p] - H264 - @MyChannel.mkv</code>\n
<i>Timeout: 60s.</i>
"""
    SES = f"""
<b>SESSION STRING SETTING</b>\n
Send valid session string (Pyrogram V2) to download content from restricted Chat/Channel without /{BotCommands.JoinChatCommand}.
<b>For private chat, your account must be a member of the chat.</b>\n
<i>Timeout: 60s.</i>
"""
    REM = """
<b>REMNAME SETTING</b>\n
Example: <code>[</code><b>|</b><code>]</code><b>|</b> <code>-</code> <b>|</b> <code>@webiste.com</code>\n
<b>Org Name:</b>
<code>Batman (2022) [1080p] - H264 @webiste.com.mkv</code>
<b>Result:</b>
<code>Batman (2022) 1080p H264.mkv</code>
<b>Current:</b> <code>{}</code>\n
<i>*Separated by</i> <b>|</b>
<i>Timeout: 60s.</i>
"""
    META = """
<b>METADATA SETTING</b>\n
Send metadata title for video file like <b>Uploaded by @h_oneysingh</b>
<b>Current:</b> <code>{}</code>\n
<i>Timeout: 60s.</i>
"""

    YT = f"""
<b>YT-DLP OPTIONS SETTING</b>\n
Examples:
1. <code>{escape("format:bestvideo[height<=?1080]+bestaudio/best")}</code> this will give best 1080p.
2. <code>{escape("format:bestvideo[height<=?720]+bestaudio/best")}</code> this will give best 720p.
Check all yt-dlp api options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FILE</a> or use this <a href='https://t.me/mltb_official/177'>SCRIPT</a> to convert cli arguments to api options.\n
<i>Timeout: 60s.</i>
"""


class HelpString:
    ARIA = [
        f"/{BotCommands.MirrorCommand[0]} or /{BotCommands.MirrorCommand[1]}: Start mirroring to Cloud using Aria.",
        f"/{BotCommands.LeechCommand[0]} or /{BotCommands.LeechCommand[1]}: Start leeching to Telegram using Aria.",
    ]

    QBIT = [
        f"/{BotCommands.QbMirrorCommand[0]} or /{BotCommands.QbMirrorCommand[1]}: Start Mirroring to Cloud using qBittorrent.",
        f"/{BotCommands.QbLeechCommand[0]} or /{BotCommands.QbLeechCommand[1]}: Start leeching to Telegram using qBittorrent.",
    ]

    JD = [
        f"/{BotCommands.JdMirrorCommand[0]} or /{BotCommands.JdMirrorCommand[1]}: Start Mirroring to Cloud using JDownloader.",
        f"/{BotCommands.JdLeechCommand[0]} or /{BotCommands.JdLeechCommand[1]}: Start leeching to Telegram using JDownloader.",
    ]

    EXTRAML = [
        f"/{BotCommands.BtSelectCommand}: Select files from torrents by gid or reply.",
        f"/{BotCommands.CancelTaskCommand}: Cancel task by gid or reply.",
    ]

    YTDL = [
        f"/{BotCommands.YtdlCommand[0]} or /{BotCommands.YtdlCommand[1]}: Mirror yt-dlp supported link.",
        f"/{BotCommands.YtdlLeechCommand[0]} or /{BotCommands.YtdlLeechCommand[1]}: Leech yt-dlp supported link.",
    ]

    DRIVE = [
        f"/{BotCommands.CloneCommand} [drive_url]: Copy file/folder to Cloud.",
        f"/{BotCommands.CountCommand} [drive_url]: Count file/folder of Google Drive.",
        f"/{BotCommands.ListCommand} [query]: Search in Cloud and Telegram.",
        f"/{BotCommands.DeleteCommand} [drive_url]: Delete file/folder from Google Drive.",
    ]

    USER = [
        f"/{BotCommands.RssCommand}: RSS Menu (list, sub, unsub, etc).",
        f"/{BotCommands.HelpCommand}: Get help (this message).",
        f"/{BotCommands.UserSetCommand} [query]: Users settings.",
        f"/{BotCommands.StatsCommand}: Show stats of the machine where the bot is hosted in.",
        f"/{BotCommands.StatusCommand}: Shows a status of all the downloads.",
        f"/{BotCommands.SearchCommand} [query]: Search for torrents with API.",
        f"/{BotCommands.PingCommand}: Check how long it takes to Ping the Bot.",
        f"/{BotCommands.MiscCommand}: Misc tools (OCR, Translate, TTS, etc).",
        f"/{BotCommands.BypassCommand}: Bypass some support website.",
        f"/{BotCommands.ScrapperCommand}: Scrapper index link.",
        f"/{BotCommands.JoinChatCommand}: Joined to chat for download restrict content.",
        f"/{BotCommands.InfoCommand}: Get info about anime, movie, and user.",
        f"/{BotCommands.LVidCommand}: Video tools with DDL mode and upload to telegram.",
        f"/{BotCommands.MVidCommand}: Video tools with DDL mode and upload to cloud.",
        f"/{BotCommands.HashCommand}: Get hash help file/media.",
        f"/{BotCommands.BackupCommand}: Backup message from any chat to another chat.",
        f"/{BotCommands.MediaInfoCommand}: Get media info from DDL.",
        f"/{BotCommands.DdlsCommand}: Gnereate DDL from telegram file.",
        f"/{BotCommands.FastDlCommand}: Get fast download from link and magnet.",
        f"/{BotCommands.WayBackCommand}: Archive a webpage with wayback machine.",
    ]

    OWNER = [
        f"/{BotCommands.SpeedCommand}: Check internet speed of the host (Sudo).",
        f"/{BotCommands.CancelAllCommand} [query]: Cancel all [status] tasks (Sudo).",
        f"/{BotCommands.AuthorizeCommand}: Authorize a chat or a user to use the bot (Sudo).",
        f"/{BotCommands.UnAuthorizeCommand}: Unauthorize a chat or a user to use the bot (Sudo).",
        f"/{BotCommands.UsersCommand}: Show users settings (Sudo).",
        f"/{BotCommands.AddSudoCommand}: Add sudo user (Owner).",
        f"/{BotCommands.RmSudoCommand}: Remove sudo users (Owner).",
        f"/{BotCommands.RestartCommand}: Restart and update the bot (Oudo).",
        f"/{BotCommands.LogCommand}: Get a log file of the bot. Handy for getting crash reports (Owner).",
        f"/{BotCommands.ShellCommand}: Run shell commands (Owner).",
        f"/{BotCommands.AExecCommand}: RExec async functions (Owner).",
        f"/{BotCommands.ExecCommand}: Exec sync functions (Owner).",
        f"/{BotCommands.SleepCommand}: Sleep the bot (Owner).",
        f"/{BotCommands.PurgeCommand}: Purge the message (Owner).",
        f"/{BotCommands.BroadcaseCommand}: Send broadcase message (Owner).",
        f"/{BotCommands.BotSetCommand}: Bot settings (Sudo).",
        f"/{BotCommands.UserSetPremiCommand}: Set user as premium (Sudo).",
        f"/{BotCommands.ClearLocalsCommand}: Clear {BotCommands.AExecCommand} or {BotCommands.ExecCommand} locals (Owner).",
    ]

    PASSWORD_ERROR_MESSAGE = """
<b>This link requires a password!</b>
- Insert <b>::</b> after the link and write the password after the sign.

<b>Example:</b> link::my password
"""

    MLNOTE = """
Available Arguments:
⁍ New Name: <code>-n</code>
⁍ Zip to Archive: <code>-z</code>
⁍ Extract Archive: <code>-e</code>
⁍ Join: <code>-j</code>
⁍ Multi Link: <code>-i</code>
⁍ Seed (Torrent): <code>-d</code>
⁍ Select (Torrent) <code>-s</code>
⁍ Same Directory: <code>-m</code>
⁍ Bulk Download: <code>-b</code>
⁍ Sample Video: <code>-sv</code>
⁍ Screenshot: <code>-ss</code>
⁍ Split Size: <code>-sp</code>
⁍ Direct Thumbnail: <code>-t</code>
⁍ GoFile Upload: <code>-gf</code>
⁍ Upload (RClone or GD): <code>-up</code>
⁍ RClone Flags: <code>-rcf</code>
⁍ Auth Username: <code>-au</code>
⁍ Auth Password: <code>-ap</code>
⁍ Video Tools: <code>-vt</code>

Note: <i><b>QB</b> commands ONLY for torrents!</i>
"""

    MTG = """
Treat links like any direct link
Some links need user access so sure you must add USER_SESSION_STRING for it.
Three types of links:
Public: <code>https://t.me/channel_name/message_id</code>
Private: <code>tg://openmessage?user_id=xxxxxx&message_id=xxxxx</code>
Super: <code>https://t.me/c/channel_id/message_id</code>
Range: <code>https://t.me/channel_name/first_message_id-last_message_id</code>

Range Example: <code>tg://openmessage?user_id=xxxxxx&message_id=555-560</code> or <code>https://t.me/channel_name/100-150</code>
Note: Range link will work only by replying cmd to it
"""

    MLDL = """
<code>/cmd link -n new name</code>

<b>By replying to link/file</b>:
<code>/cmd -n new name -z -e -up upload destination</code>

<b>Direct link authorization</b>: -au -ap
<code>/cmd link -au username -ap password</code>

<b>Direct link custom headers</b>: -h
<code>/cmd link -h Key: value Key1: value1</code>

<b>Thumbnail for current task</b>: -t
<code>/cmd link -t tg-message-link</code> (doc or photo)

<b>Split size for current task</b>: -sp
<code>/cmd link -sp</code> (<code>500mb</code> or <code>2gb</code> or <code>4000000000</code>)
Note: Only mb and gb are supported or write in bytes without unit!
"""

    MLZUZ = """
<code>/cmd link -e password</code> (extract password protected)
<code>/cmd link -z password</code> (zip password protected)
<code>/cmd link -z password -e</code> (extract and zip password protected)
<code>/cmd link -e password -z password</code> (extract password protected and zip password protected)

Note: When both extract and zip added with cmd it will extract first and then zip, so always extract first
"""

    MLJOINSAM = """
Join option will only work before extract and zip, so mostly it will be used with -m argument (samedir)
By Reply:
<code>/cmd -i 3 -j -m folder </code>
<code>/cmd -b -j -m folder name</code>
if u have link have splitted files:
<code>/cmd link -j</code>
Note: Join not for YTDL cmds

<b>Create sample video</b>: -sv
<code>/cmd -sv</code> (it will take the default values which 60sec sample duration and part duration is 4sec).
You can control those values.
Example: <code>/cmd -sv 70:5</code> (sample-duration:part-duration) or <code>/cmd -sv :5</code> or <code>/cmd -sv 70</code>.

<b>Create screenshots</b>: -ss
Up to 10 screenshots for one video
<code>/cmd -ss</code> or <code>/cmd -ss 6</code>
"""

    MLBULK = """
Bulk can be used by text message and by replying to text file contains links seperated by new line.
You can use it only by reply to message(text/file).
All options should be along with link!
Example:
<code>/cdm link1 -n new name -up remote1:path1 -rcf |key:value|key:value</code>
<code>/cdm link2 -z -n new name -up remote2:path2</code>
<code>/cdm link3 -e -n new name -up remote2:path2</code>

Reply to this example by this cmd <code>/cmd -b</code> (bulk)
You can set start and end of the links from the bulk like seed, with -b start:end or only end by -b :end or only start by -b start. The default start is from zero(first link) to inf.
"""

    MISC = f"""
1. OCR: Generate text from image.
2. TTS: Text to speech, generate sound from text or image.
4. Webss: Generate screenshot from url.
5. Vidss: Generate screenshot from ddl.
6. Translate: Translate from text or image.
7. Pahe: Find movie by title from Pahe website.
8. Convert: Convert non animation sticker from image or from sticker to image.
9. Thumbnail: Genearte some thumbnail poster.

<b>Note</b>\nAvailable code for TTS and Translate <b><a href='https://telegra.ph/Support-Language-08-17'>Here</a></b>.
<b>Example:</b> <code>/{BotCommands.MiscCommand} id</code>, result will in id (Indonesia) language.
<i>*Some laguage may not work for TTS.</i>
"""

    CLONE = """
<b>Support Site:
GDToT
GDrive
Sharer
AppDrive
Gdflix
FileBee
Filepress</b>

Send support sites or rclone path along with command or by replying to the link/rc_path by command

<b>Multi links only by replying to first link or rclone_path:</b>
<code>/cmd -i 10 </code>(number of links/paths)

<b>Gdrive:</b>
<code>/cmd link -up dest_up</code>

<b>RClone:</b>
<code>/cmd link -up dest_up -rcf flagkey:flagvalue|flagkey|flagkey:flagvalue</code>

<b>link & dest_up:</b> rcl or rclone_path (RClone) and gdl, drive_id, or gdrive_path (GDrive API)

Note: If -up not specified then will take DEFAULT_UPLOAD from BOT/USER setting.
"""

    RCLONE = """
<b>Rclone Download</b>:
<code>/cmd main:dump/ubuntu.iso</code> or <code>rcl</code> (To select config, remote and path)
Add <code>mrcc:</code> before the path without space to add path manually
<code>/cmd mrcc:main:/dump/ubuntu.iso</code>

<b>Upload</b>: -up
<code>/cmd link -up rcl</code> (to select rclone config, remote & path or tg id/username for leech)
Sirect upload path: -up remote:dir/subdir
If DEFAULT_UPLOAD is `rc` then you can pass up: `gd` to upload using gdrive tools to GDRIVE_ID.
If DEFAULT_UPLOAD is `gd` then you can pass up: `rc` to upload to RCLONE_PATH.
Add <code>mrcc:</code> before the path without space to add path manually
<code>/cmd link -up mrcc:main:dump</code>

<b>Rclone Flags</b>: -rcf
<code>/cmd link -up path|rcl -rcf --buffer-size:8M|--drive-starred-only|key|key:value</code>
This will override all other flags except --exclude
Check here all <a href='https://rclone.org/flags/'>RcloneFlags</a>.
"""

    SELECT = """
<code>/cmd link -s</code> or by replying to file/link
"""

    BTSEED = """
<code>/cmd link -d ratio:seed_time</code> or by replying to file/link
To specify ratio and seed time add -d ratio:time. Ex: -d 0.7:10 (ratio and time) or -d 0.7 (only ratio) or -d :10 (only time) where time in minutes.
"""

    GOFILE = """
<code>/cmd link</code> or reply to a message
<i>*GoFile upload only for cmd mirror not leech</i>
"""

    MULTI = """
<b>Multi links only by replying to first link/file</b>:
<code>/cmd -i 10</code> (number of links/files)

<b>Multi links within same upload directory only by replying to first link/file</b>: -m
<code>/cmd -i 10</code> (number of links/files) <code>-m folder name</code> (multi message)
<code>/cmd -b -m folder name</code> (bulk-message/file)
"""

    YLNOTE = """
Available Arguments:
⁍ New Name: <code>-n</code>
⁍ Zip to Archive: <code>-z</code>
⁍ Multi Link: <code>-i</code>
⁍ Quality Select: <code>-s</code>
⁍ Same Directory: <code>-m</code>
⁍ Bulk Download: <code>-b</code>
⁍ Sample Video: <code>-sv</code>
⁍ Screenshot: <code>-ss</code>
⁍ Split Size: <code>-sp</code>
⁍ YTDL Options: <code>-o</code>
⁍ GoFile Upload: <code>-gf</code>
⁍ Upload (RClone or GD): <code>-up</code>
⁍ RClone Flags: <code>-rcf</code>
⁍ Video Tools: <code>-vt</code>
"""

    YLDL = """
<b>Send link along with command line</b>:
<code>/cmd link -s -n new name -opt x:y|x1:y1</code>

<b>By replying to link</b>:
<code>/cmd -n  new name -z password -opt x:y|x1:y1</code>

<b>Thumbnail for current task</b>: -t
<code>/cmd link -t tg-message-link</code> (doc or photo)

<b>New Name</b>: -n
<code>/cmd link -n new name</code>
Note: Don't add file extension

<b>Zip</b>: -z password
<code>/cmd link -z</code> (zip)
<code>/cmd link -z password</code> (zip password protected)

<b>Create sample video</b>: -sv
<code>/cmd -sv</code> (it will take the default values which 60sec sample duration and part duration is 4sec).
You can control those values.
Example: <code>/cmd -sv 70:5</code> (sample-duration:part-duration) or <code>/cmd -sv :5</code> or <code>/cmd -sv 70</code>.

<b>Create screenshots</b>: -ss
Up to 10 screenshots for one video
<code>/cmd -ss</code> or <code>/cmd -ss 6</code>

<b>Split size for current task</b>: -sp
<code>/cmd link -sp</code> (<code>500mb</code> or <code>2gb</code> or <code>4000000000</code>)
Note: Only mb and gb are supported or write in bytes without unit!
"""

    YLBULK = """
Bulk can be used by text message and by replying to text file contains links seperated by new line.
You can use it only by reply to message(text/file).
All options should be along with link!
Example:
link1 -n new name -up remote1:path1 -rcf |key:value|key:value
link2 -z -n new name -up remote2:path2
link3 -e -n new name -opt ytdlpoptions

<code>/cmd ytlink pswd: pass</code> (zip/unzip) <code>opt: ytdlpoptions up: remote2:path2</code>
Reply to this example by this cmd <code>/cmd b</code> (bulk)
You can set start and end of the links from the bulk with -b start:end or only end by -b :end or only start by -b start. The default start is from zero(first link) to inf.
"""

    YTOPT = """
Incase default quality added from yt-dlp options using format option and you need to select quality for specific link or links with multi links feature.
<code>/cmd link -s</code>

<code>/cmd link -opt playliststart:^10|fragment_retries:^inf|matchtitle:S13|writesubtitles:true|live_from_start:true|postprocessor_args:{"ffmpeg": ["-threads", "4"]}|wait_for_video:(5, 100)</code>
Note: Add `^` before integer or float, some values must be numeric and some string.
Like playlist_items:10 works with string, so no need to add `^` before the number but playlistend works only with integer so you must add `^` before the number like example above.
You can add tuple and dict also. Use double quotes inside dict.

Check all yt-dlp api options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FILE</a> or use this <a href='https://t.me/mltb_official_channel/177'>script</a> to convert cli arguments to api options.
"""

    VIDTOOLS = """
Extra Videos Tool:
1. Merge video + video
2. Merge video + audio
3. Merge video + subtitle
4. Hardsub (sudo) - supports custom .ttf font uploads
5. SubSync
6. Compress video - supports custom CRF quality selection
7. Trim video
8. Watermark video
9. Remove video stream
10. Extract video stream
11. Convert (1080p, 720p, 540p, 480p, 360p)
12. Speed Adjust (0.5x, 0.75x, 1.25x, 1.5x, 2.0x)
13. Video to GIF
14. Crop / Aspect Ratio (16:9, 9:16, 4:3, 1:1)
15. Video Filters (Rotate, Flip, Denoise)
16. Multi-Resolution (Generate multiple resolution files concurrently)
17. IntroSub (Add intro subtitle/credits at start of video)
18. Strip Metadata (Remove tags and global headers)
19. Swap Audio (Swap/replace audio stream with external audio file)
20. Translate Subs (Translate subtitle files via Google Translate API)

Note:
1. Don't use arg -n (rename) for merge, -n can be used in bulk
2. Merge mode required arg -m (same folder) for multi file/link
3. Trim, watermark, remove, extract and convert will take first video setting for all videos
4. Only first video will be executed if multi mode for vidtools has been disable
"""

    RSSHELP = """
Use this format to add feed url:
Title1 link (required)
Title2 link -c cmd -inf xx -exf xx
Title3 link -c cmd -d ratio:time -z password

-c command + any arg
-inf For included words filter.
-exf For excluded words filter.

Example: Title https://www.rss-url.com -inf 1080 or 720 or 144p|mkv or mp4|hevc -exf flv or web|xxx -c -up: mrcc:remote:path/subdir -rcf: --buffer-size:8M|key|key:value
This filter will parse links that it's titles contains `(1080 or 720 or 144p) and (mkv or mp4) and hevc` and doesn't conyain (flv or web) and xxx` words. You can add whatever you want.

Another example: -inf  1080  or 720p|.web. or .webrip.|hvec or x264. This will parse titles that contains ( 1080  or 720p) and (.web. or .webrip.) and (hvec or x264). Added space before and after 1080 to avoid wrong matching. If this `10805695` number in title it will match 1080 if added 1080 without spaces after it.

Filter Notes:
1. | means and.
2. Add `or` between similar keys, you can add it between qualities or between extensions, so don't add filter like this -inf 1080|mp4 or 720|web because this will parse 1080 and (mp4 or 720) and web ... not (1080 and mp4) or (720 and web)."
3. You can add `or` and `|` as much as you want."
4. Take look on title if it has static special character after or before the qualities or extensions or whatever and use them in filter to avoid wrong match.

<i>Timeout: 60s.</i>
        """

    @property
    def all_commands(self):
        return (
            self.ARIA
            + self.QBIT
            + self.JD
            + self.EXTRAML
            + self.YTDL
            + self.DRIVE
            + self.USER
            + self.OWNER
        )


class CMDS:
    ARIA = "\n".join(HelpString.ARIA + HelpString.EXTRAML)
    QBIT = "\n".join(HelpString.QBIT + HelpString.EXTRAML)
    JD = "\n".join(HelpString.JD)
    YTDL = "\n".join(HelpString.YTDL)
    DRIVE = "\n".join(HelpString.DRIVE)
    USER = "\n".join(HelpString.USER)
    OWNER = "\n".join(HelpString.OWNER)


HELP = {
    "Aria": [f"<b>ARIA COMMANDS</b>\n{CMDS.ARIA}", config_dict["IMAGE_ARIA"], "home"],
    "qBit": [
        f"<b>QBITTORRENT COMMANDS</b>\n{CMDS.QBIT}",
        config_dict["IMAGE_QBIT"],
        "home",
    ],
    "JD": [
        f"<b>JDOWNLOADER COMMANDS</b>\n{CMDS.JD}",
        config_dict["IMAGE_QBIT"],
        "home",
    ],
    "YTDL": [f"<b>YTDL COMMANDS</b>\n{CMDS.YTDL}", config_dict["IMAGE_YT"], "home"],
    "Drive": [f"<b>GDRIVE COMMANDS</b>\n{CMDS.DRIVE}", config_dict["IMAGE_GD"], "home"],
    "User": [f"<b>USER COMMANDS</b>\n{CMDS.USER}", config_dict["IMAGE_USER"], "home"],
    "Owner": [
        f"<b>OWNER COMMANDS</b>\n{CMDS.OWNER}",
        config_dict["IMAGE_OWNER"],
        "home",
    ],
    "VidTools": [
        f"<b>VIDEO TOOLS (-vt)</b>{HelpString.VIDTOOLS}",
        config_dict["IMAGE_VIDTOOLS"],
        "home",
    ],
    "Mirror/Leech": [
        f"<b>MIRROR/LEECH</b>{HelpString.MLNOTE}",
        config_dict["IMAGE_HELP"],
        "ml",
    ],
    "YouTube/YLeech": [
        f"<b>YOUTUBE/YLEECH</b>{HelpString.YLNOTE}",
        config_dict["IMAGE_HELP"],
        "ytdl",
    ],
    "Basic ML": [
        f"<b>BASIC COMMAND</b>{HelpString.MLDL}",
        config_dict["IMAGE_HELP"],
        "ml",
    ],
    "Zip/Unzip": [
        f"<b>ZIP/UNZIP (-z -e)</b>{HelpString.MLZUZ}",
        config_dict["IMAGE_HELP"],
        "ml",
    ],
    "Join": [
        f"<b>JOIN/SAMPLE (-j -sv)</b>{HelpString.MLJOINSAM}",
        config_dict["IMAGE_HELP"],
        "ml",
    ],
    "Selection": [
        f"<b>TORRENT/JD SELECTION (-s)</b>{HelpString.SELECT}",
        config_dict["IMAGE_HELP"],
        "ml",
    ],
    "Seed": [
        f"<b>TORRENT SEED (-d)</b>{HelpString.BTSEED}",
        config_dict["IMAGE_HELP"],
        "ml",
    ],
    "MRClone": [
        f"<b>RCLONE OPTIONS</b>{HelpString.RCLONE}",
        config_dict["IMAGE_HELP"],
        "ml",
    ],
    "GoFile ML": [
        f"<b>GOFILE UPLOAD (-gf)</b>{HelpString.GOFILE}",
        config_dict["IMAGE_HELP"],
        "ml",
    ],
    "Multi ML": [
        f"<b>MULTI LINK (-i)</b>{HelpString.MULTI}",
        config_dict["IMAGE_HELP"],
        "ml",
    ],
    "TG Link": [
        f"<b>TG LINK DOWNLOAD</b>{HelpString.MTG}",
        config_dict["IMAGE_HELP"],
        "ml",
    ],
    "Bulk ML": [
        f"<b>BULK DOWNLOAD (-b)</b>{HelpString.MLBULK}",
        config_dict["IMAGE_HELP"],
        "ml",
    ],
    "Basic YL": [
        f"<b>BASIC COMMAND</b>{HelpString.YLDL}",
        config_dict["IMAGE_HELP"],
        "ytdl",
    ],
    "Options": [
        f"<b>YOUTUBE OPSTIONS (-opt)</b>{HelpString.YTOPT}",
        config_dict["IMAGE_HELP"],
        "ytdl",
    ],
    "YRClone": [
        f"<b>RCLONE OPTIONS</b>{HelpString.RCLONE}",
        config_dict["IMAGE_HELP"],
        "ytdl",
    ],
    "GoFile YL": [
        f"<b>GOFILE UPLOAD (-gf)</b>{HelpString.GOFILE}",
        config_dict["IMAGE_HELP"],
        "ytdl",
    ],
    "Multi YL": [
        f"<b>MULTI LINK (-i)</b>{HelpString.MULTI}",
        config_dict["IMAGE_HELP"],
        "ytdl",
    ],
    "Bulk YL": [
        f"<b>BULK DOWNLOAD (-b)</b>{HelpString.YLBULK}",
        config_dict["IMAGE_HELP"],
        "ytdl",
    ],
}


def get_help_button(from_user: int, data: str = None):
    buttons = ButtonMaker()

    def _build_button(btns: list[set], back=True):
        for key in btns:
            if key != data:
                buttons.button_data(
                    key,
                    f"help {from_user.id} {key}",
                    "header" if key in ["Mirror/Leech", "YouTube/YLeech"] else None,
                )
        if back:
            buttons.button_data("<<", f"help {from_user.id} back", "footer")

    home_menu = [
        "Aria",
        "qBit",
        "JD",
        "YTDL",
        "Drive",
        "User",
        "Owner",
        "VidTools",
        "Mirror/Leech",
        "YouTube/YLeech",
    ]
    ml_menu = [
        "Basic ML",
        "Zip/Unzip",
        "Join",
        "Selection",
        "Seed",
        "MRClone",
        "GoFile ML",
        "Multi ML",
        "TG Link",
        "Bulk ML",
    ]
    ytdl_menu = ["Basic YL", "Options", "YRClone", "GoFile YL", "Multi YL", "Bulk YL"]

    if not data or data == "back":
        text, image = (
            f"{from_user.mention}, Choose Options Below.",
            config_dict["IMAGE_HELP"],
        )
        _build_button(home_menu, back=False)
    else:
        text, image, menu = HELP[data]
        match menu:
            case "home":
                _build_button(home_menu)
            case "ml":
                _build_button(ml_menu)
            case "ytdl":
                _build_button(ytdl_menu)

    buttons.button_data("Close", f"help {from_user.id} close", "footer")
    return text, image, buttons.build_menu(3)
